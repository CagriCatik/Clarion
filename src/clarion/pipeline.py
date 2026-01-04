import asyncio
import math
import time
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
        status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
        use_rag: bool = False,
        embedding_model: Optional[str] = None,
        selected_kb_ids: Optional[List[str]] = None
    ) -> DocResult:
        
        # 1. Analyze Input
        start_time = time.perf_counter()
        total_chars = len(input_text_full)
        est_tokens = estimate_tokens(input_text_full)
        
        # Determine Context Limit
        ctx_limit = generation_config.num_ctx if generation_config else 4096
        output_budget = generation_config.num_predict if generation_config else 2048
        
        # Reserve space for output + system prompt overhead (~1000)
        # We ensure we at least leave room for the requested output budget.
        # If the user asks for 8k output on 8k context, this will be negative/small, forcing a split.
        reserved_overhead = output_budget + 1000 
        safe_input_limit = max(1000, ctx_limit - reserved_overhead)
        
        await self._notify(f"Analysis: Input is {total_chars} chars (~{est_tokens} tokens). Context: {ctx_limit}, Output Requested: {output_budget}. Safe Input Limit: {safe_input_limit}.", status_callback)
        
        # 2. Prepare Prompt
        # Purely user instruction. If empty, default to summarization.
        user_instruction = instruction_config.inline_instruction or "Summarize the following text in detail."
        
        # 3. Execution Strategy
        if est_tokens <= safe_input_limit:
            # === STRATEGY A: ONE-SHOT ===
            process_start = time.perf_counter()
            await self._notify(f"Strategy: One-Shot Processing (fits in {ctx_limit} context).", status_callback)
            
            final_doc = await self._process_block(
                input_text_full, 
                user_instruction,
                generation_config,
                status_callback,
                use_rag=use_rag,
                embedding_model=embedding_model,
                selected_kb_ids=selected_kb_ids
            )
            
        else:
            # === STRATEGY B: PARALLEL WINDOWED REDUCE ===
            process_start = time.perf_counter()
            await self._notify(f"Strategy: Large File Split ({est_tokens} > {safe_input_limit}). Using Parallel Semantic Splitter...", status_callback)
            
            from clarion.splitter import MarkdownSplitter
            c_size = (generation_config.chunk_size if generation_config else safe_input_limit * 4)
            c_overlap = (generation_config.chunk_overlap if generation_config else 500)
            splitter = MarkdownSplitter(chunk_size=c_size, overlap=c_overlap)
            windows = splitter.split_text(input_text_full)
            
            await self._notify(f"Split into {len(windows)} semantic blocks. Processing concurrently...", status_callback)
            
            # Create tasks for parallel processing
            tasks = []
            for idx, window in enumerate(windows):
                # Context-aware instruction is simplified for parallel execution
                # We lose strictly previous context, but gain speed.
                chunk_instruction = f"{user_instruction}\n\n(Part {idx+1}/{len(windows)} of document)"
                
                tasks.append(self._process_block(
                    window, 
                    chunk_instruction,
                    generation_config,
                    status_callback, # Note: concurrent callbacks might interleave
                    use_rag=use_rag,
                    embedding_model=embedding_model,
                    selected_kb_ids=selected_kb_ids
                ))
            
            # Execute all blocks in parallel
            docs = await asyncio.gather(*tasks)
                
            # Merge
            await self._notify("Merging parallel results...", status_callback)
            merged_doc = self._merge_docs(docs)
            
            # CRITICAL: Run consolidation pass to dry out duplication/disjointedness
            await self._notify("Consolidating merged chunks...", status_callback)
            final_doc = await self._consolidate_chunks(
                merged_doc,
                generation_config,
                status_callback
            )

        end_time = time.perf_counter()
        total_duration = end_time - start_time
        process_duration = end_time - process_start
        
        await self._notify(f"Complete. Total pipeline time: {total_duration:.2f}s (Processing: {process_duration:.2f}s).", status_callback)
        
        # Append metadata footer village
        footer = f"\n\n---\n**Generation Metadata**\n- **Model**: {self.provider.model_name}\n- **Time**: {process_duration:.2f}s"
        if use_rag and hasattr(self, "_kb_stats") and self._kb_stats:
             footer += "\n- **Vector Context Used**:"
             for src, count in self._kb_stats.items():
                 footer += f"\n  - {src} ({count} chunks)"
        
        if final_doc and final_doc.content:
            final_doc.content += footer

        return DocResult(
            input_file=input_path,
            final_doc=final_doc,
            manifest_path=""
        )

    async def _process_block(
        self, 
        text: str, 
        instruction: str, 
        config: GenerationConfig, 
        status_callback: Optional[Callable] = None,
        use_rag: bool = False,
        embedding_model: Optional[str] = None,
        selected_kb_ids: Optional[List[str]] = None
    ) -> FlexDoc:
        # Load system guidelines
        system_guidelines = render_prompt("system_guidelines.j2")
        
        relevant_rules = ""
        if use_rag:
            from clarion.knowledge import get_vector_store
            vs = get_vector_store(embedding_model=embedding_model)
            
            # Index guidelines if not already done (internal hashing handles this)
            vs.index_guidelines(system_guidelines)
            
            await self._notify("RAG: Retrieving relevant guidelines...", status_callback)
            rk = config.rag_k if config else 5
            relevant_rules = vs.get_relevant_guidelines(text, n_results=rk)
            
            # Combine relevant rules with core instructions village
            system_context = f"{system_guidelines}\n\nRELEVANT GUIDELINES FOR THIS BLOCK:\n{relevant_rules}"
            
            # Incorporate selected KB documents village
            if selected_kb_ids:
                doc_list_str = ", ".join(selected_kb_ids)
                await self._notify(f"RAG: Querying {len(selected_kb_ids)} selected KB docs: {doc_list_str}...", status_callback)
                
                kb_content, params = vs.get_relevant_kb_content(text, n_results=5, filter_sources=selected_kb_ids)
                
                # Store stats for final footer
                if not hasattr(self, "_kb_stats"):
                    self._kb_stats = {}
                for src, count in params.items():
                    self._kb_stats[src] = self._kb_stats.get(src, 0) + count
                
                if kb_content:
                    # Estimate chunks by double newlines
                    chunk_count = kb_content.count('\n\n') + 1
                    await self._notify(f"RAG: Found {chunk_count} relevant chunks from Knowledge Base.", status_callback)
                    system_context += f"\n\nPROJECT CONTEXT (RELEVANT KB CONTENT):\n{kb_content}"
                    print(f"DEBUG: RAG added {len(kb_content)} chars of KB content.")
                else:
                    print("DEBUG: RAG retrieval returned NO content.")
                    await self._notify(f"RAG: No relevant content found in selected KB documents for this block.", status_callback)
        else:
            system_context = system_guidelines

        # Log custom instruction usage
        if instruction:
            display_instr = (instruction[:50] + '...') if len(instruction) > 50 else instruction
            await self._notify(f"Applying custom instruction: '{display_instr}'", status_callback)

        # Render main prompt
        prompt = render_prompt(
            "generation.j2",
            instruction=instruction,
            system_guidelines=system_context,
            context=text,
            word_budget=config.word_budget if config else 2000,
            num_predict=config.num_predict if config else 2048
        )
        
        
        # 1. Draft
        await self._notify("Drafting content with Ollama...", status_callback)
        draft_doc = await self.provider.generate_json(prompt, FlexDoc, config, status_callback=status_callback)
        
        # 2. Reflection / Review Loop (Skip if fast_mode is enabled)
        if config and config.fast_mode:
            await self._notify("Fast Mode: Skipping refinement pass.", status_callback)
            return draft_doc

        # We only run this if we have content to review
        if draft_doc.content and len(draft_doc.content) > 10:
            review_prompt = render_prompt(
                "review.j2",
                draft_content=draft_doc.content,
                relevant_rules=relevant_rules,
                word_budget=config.word_budget if config else 2000
            )
            # Pass 2: The model acts as editor
            await self._notify("Reviewing and refining output...", status_callback)
            final_doc = await self.provider.generate_json(review_prompt, FlexDoc, config, status_callback=status_callback)
            return final_doc
            
        return draft_doc

    def _merge_docs(self, docs: List[FlexDoc]) -> FlexDoc:
        if not docs:
            return FlexDoc(content="")
            
        # fast concat
        full_content = "\n\n".join([d.content for d in docs])
        return FlexDoc(content=full_content)
    
    async def _consolidate_chunks(
        self,
        merged_doc: FlexDoc,
        config: GenerationConfig,
        status_callback: Optional[Callable] = None
    ) -> FlexDoc:
        """
        Takes merged chunk content and consolidates it into ONE coherent document.
        Removes duplicate headers, merges overlapping sections, eliminates redundancy.
        """
        consolidate_prompt = render_prompt(
            "consolidate.j2",
            merged_content=merged_doc.content,
            word_budget=config.word_budget if config else 2000,
            num_predict=config.num_predict if config else 2048
        )
        
        # Run consolidation pass (no review needed, this IS the final pass)
        consolidated = await self.provider.generate_json(
            consolidate_prompt,
            FlexDoc,
            config,
            status_callback=status_callback
        )
        
        return consolidated

async def run_pipeline(
    config: InstructionConfig, 
    input_path: str,
    provider: Optional[LLMProvider] = None,
    generation_config: Optional[GenerationConfig] = None,
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    use_rag: bool = False,
    embedding_model: Optional[str] = None,
    selected_kb_ids: Optional[List[str]] = None
) -> DocResult:
    
    # Read full text
    def read_file(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    text = await asyncio.to_thread(read_file, input_path)
        
    prov = provider or OllamaProvider()
    pipeline = DirectPipeline(prov)
    return await pipeline.run(
        input_path, 
        text, 
        config, 
        generation_config, 
        status_callback, 
        use_rag=use_rag, 
        embedding_model=embedding_model,
        selected_kb_ids=selected_kb_ids
    )
