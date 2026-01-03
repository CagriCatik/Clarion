import asyncio
import math
from typing import List, Optional, Callable, Awaitable
from clarion.schemas import (
    InstructionConfig, FlexDoc, DocResult, GenerationConfig
)

from clarion.providers import LLMProvider, OllamaProvider
from clarion.prompt_loader import render_prompt

# Simple token estimator (char / 4)
def estimate_tokens(text: str) -> int:
    return len(text) // 4

class DirectPipeline:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        
    async def _notify(self, msg: str, status_callback: Optional[Callable]):
        if status_callback:
            if asyncio.iscoroutinefunction(status_callback):
                await status_callback(msg)
            else:
                status_callback(msg)

    async def run(
        self, 
        input_path: str, 
        input_text_full: str, 
        instruction_config: InstructionConfig,
        generation_config: Optional[GenerationConfig] = None,
        status_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> DocResult:
        
        # 1. Analyze Input
        total_chars = len(input_text_full)
        est_tokens = estimate_tokens(input_text_full)
        
        # Determine Context Limit
        ctx_limit = generation_config.num_ctx if generation_config else 4096
        safe_input_limit = max(1000, ctx_limit - 2000) 
        
        await self._notify(f"Analysis: Input is {total_chars} chars (~{est_tokens} tokens). Context limit: {ctx_limit}.", status_callback)
        
        # 2. Prepare Prompt
        # Purely user instruction. If empty, default to summarization.
        user_instruction = instruction_config.inline_instruction or "Summarize the following text in detail."
        
        # 3. Execution Strategy
        if est_tokens <= safe_input_limit:
            # === STRATEGY A: ONE-SHOT ===
            await self._notify(f"Strategy: One-Shot Processing (fits in {ctx_limit} context).", status_callback)
            
            final_doc = await self._process_block(
                input_text_full, 
                user_instruction,
                generation_config,
                status_callback
            )
            
        else:
            # === STRATEGY B: WINDOWED REDUCE ===
            await self._notify(f"Strategy: Large File Split ({est_tokens} > {safe_input_limit}). Using Semantic Splitter...", status_callback)
            
            from clarion.splitter import MarkdownSplitter
            # Use safe_input_limit * 4 for approx chars, with some overlap
            splitter = MarkdownSplitter(chunk_size=safe_input_limit * 4, overlap=500)
            windows = splitter.split_text(input_text_full)
            
            await self._notify(f"Split into {len(windows)} semantic blocks.", status_callback)
            
            # Process each window
            docs: List[FlexDoc] = []
            for i, window in enumerate(windows):
                await self._notify(f"Processing window {i+1}/{len(windows)}...", status_callback)
                d = await self._process_block(
                    window, 
                    user_instruction,
                    generation_config,
                    status_callback
                )
                docs.append(d)
                
            # Merge
            await self._notify("Merging window results...", status_callback)
            merged_doc = self._merge_docs(docs)
            
            # Optional: Final Synthesis if it fits?
            # For now, just return merged because "Reduce" with freeform instructions is ambiguous
            # (e.g. if instruction was "List action items", merging is just concat. 
            # If it was "Write a story", concat works too. 
            # Re-summarizing might lose detail.)
            final_doc = merged_doc

        await self._notify("Complete.", status_callback)
        
        return DocResult(
            input_file=input_path,
            final_doc=final_doc,
            manifest_path=""
        )

    async def _process_block(self, text: str, instruction: str, config: GenerationConfig, status_callback: Optional[Callable] = None) -> FlexDoc:
        # Load system guidelines
        system_guidelines = render_prompt("system_guidelines.j2")

        # Render main prompt
        prompt = render_prompt(
            "generation.j2",
            instruction=instruction,
            system_guidelines=system_guidelines,
            context=text
        )
        
        # 1. Draft
        await self._notify("Drafting content with Ollama...", status_callback)
        draft_doc = await self.provider.generate_json(prompt, FlexDoc, config)
        
        # 2. Reflection / Review Loop (Skip if fast_mode is enabled)
        if config and config.fast_mode:
            await self._notify("Fast Mode: Skipping refinement pass.", status_callback)
            return draft_doc

        # We only run this if we have content to review
        if draft_doc.content and len(draft_doc.content) > 10:
            review_prompt = render_prompt(
                "review.j2",
                draft_content=draft_doc.content
            )
            # Pass 2: The model acts as editor
            await self._notify("Reviewing and refining output...", status_callback)
            final_doc = await self.provider.generate_json(review_prompt, FlexDoc, config)
            return final_doc
            
        return draft_doc

    def _merge_docs(self, docs: List[FlexDoc]) -> FlexDoc:
        if not docs:
            return FlexDoc(content="")
            
        # fast concat
        full_content = "\n\n".join([d.content for d in docs])
        return FlexDoc(content=full_content)

async def run_pipeline(
    config: InstructionConfig, 
    input_path: str,
    provider: Optional[LLMProvider] = None,
    generation_config: Optional[GenerationConfig] = None,
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> DocResult:
    
    # Read full text
    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    prov = provider or OllamaProvider()
    pipeline = DirectPipeline(prov)
    return await pipeline.run(input_path, text, config, generation_config, status_callback)
