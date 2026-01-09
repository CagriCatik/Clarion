import asyncio
import math
import re
from typing import List, Optional, Callable, Awaitable
from clarion.schemas import (
    InstructionConfig, FlexDoc, DocResult, GenerationConfig, ReviewReport, RepairResult, DeciderResponse
)

from clarion.providers import LLMProvider, OllamaProvider
from clarion.prompt_loader import render_prompt

# Simple token estimator (char / 4)
def estimate_tokens(text: str) -> int:
    return len(text) // 4

class DirectPipeline:
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        # In-memory cache for this session (moved to instance to reset per run)
        self._cache: dict[str, FlexDoc] = {}
        
    async def _notify(self, msg: str, status_callback: Optional[Callable]):
        if status_callback:
            if asyncio.iscoroutinefunction(status_callback):
                await status_callback(msg)
            else:
                status_callback(msg)

    def _get_cache_key(self, text: str, instruction: str) -> str:
        """Simple hash for caching."""
        import hashlib
        raw = f"{text}{instruction}"
        return hashlib.md5(raw.encode()).hexdigest()

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
            # === STRATEGY B: PARALLEL WINDOWED REDUCE ===
            await self._notify(f"Strategy: Large File Split ({est_tokens} > {safe_input_limit}). Executing Parallel Windows...", status_callback)
            
            from clarion.splitter import MarkdownSplitter
            splitter = MarkdownSplitter(chunk_size=safe_input_limit * 4, overlap=500)
            windows = splitter.split_text(input_text_full)
            
            await self._notify(f"Split into {len(windows)} semantic blocks. Processing concurrently...", status_callback)
            
            # --- PARALLEL EXECUTION ---
            tasks = []
            for i, window in enumerate(windows):
                task = self._process_block(
                    window, 
                    user_instruction,
                    generation_config,
                    status_callback,
                    f"Window {i+1}"
                )
                tasks.append(task)
            
            # Execute all blocks (Ollama queueing handled by provider lock/semaphore if implemented, else relies on server queue)
            docs = await asyncio.gather(*tasks)
                
            # Merge
            await self._notify("Merging window results...", status_callback)
            final_doc = self._merge_docs(docs)
            
        await self._notify("Complete.", status_callback)
        
        return DocResult(
            input_file=input_path,
            final_doc=final_doc,
            manifest_path=""
        )



    async def _process_block(self, text: str, instruction: str, config: GenerationConfig, status_callback: Optional[Callable] = None, label: str = "Block") -> FlexDoc:
        # --- CACHING CHECK ---
        cache_key = self._get_cache_key(text, instruction)
        if cache_key in self._cache:
            await self._notify(f"[{label}] Cache Hit! Skipping generation.", status_callback)
            return self._cache[cache_key]

        # --- STEP 1: GENERATOR ---
        gen_model = config.generator_model if config else None
        await self._notify(f"[{label}] Role: GENERATOR (Drafting content | Input: {len(text)} chars | Model: {gen_model or 'Default'})...", status_callback)
        gen_prompt = render_prompt(
            "02_task_generator.j2",
            instruction=instruction,
            context=text
        )
        draft_doc = await self.provider.generate_json(gen_prompt, FlexDoc, config, model_override=gen_model)
        await self._notify(f"[{label}] Role: GENERATOR (Draft size: {len(draft_doc.content)} chars).", status_callback)
        
        # SANITIZATION
        draft_doc.content = self._sanitize_content(draft_doc.content)

        # Skip review if too short
        if (config and config.fast_mode) or not draft_doc.content or len(draft_doc.content) < 50:
            self._cache[cache_key] = draft_doc # Cache valid result
            return draft_doc

        # --- STEP 1.5: MERMAID AUGMENTATION ---
        # Robust, deterministic generation using creating clarion.mermaid
        if not config or not config.fast_mode: # Only in robust mode
            try:
                await self._notify(f"[{label}] Analyzing for Mermaid Diagram potential...", status_callback)
                # We analyze the DRAFT CONTENT to ensure the diagram matches what was written.
                decider_prompt = render_prompt("03_mermaid_decider.j2", context=draft_doc.content) 
                
                decider_res = await self.provider.generate_json(decider_prompt, DeciderResponse, config, model_override=gen_model)
                
                if decider_res.use_mermaid and decider_res.spec:
                     await self._notify(f"[{label}] Mermaid needed: {decider_res.diagram_intent}. Rendering...", status_callback)
                     from clarion.mermaid.renderer import MermaidRenderer
                     
                     mermaid_code = MermaidRenderer.render(decider_res.spec)
                     
                     # Append strictly formatting
                     draft_doc.content += f"\n\n## Diagram: {decider_res.diagram_intent}\n\n```mermaid\n{mermaid_code}\n```\n"
                else:
                     await self._notify(f"[{label}] No Mermaid diagram required.", status_callback)
                     
            except Exception as e:
                print(f"Mermaid generation failed: {e}")
                # Non-fatal error
                await self._notify(f"[{label}] Mermaid generation skipped (error: {str(e)}).", status_callback)


        # --- STEP 2: REVIEWER ---
        rev_model = config.reviewer_model if config else None
        await self._notify(f"[{label}] Role: REVIEWER (Auditing compliance | Model: {rev_model or 'Default'})...", status_callback)
        review_prompt = render_prompt(
            "04_task_reviewer.j2",
            draft_content=draft_doc.content
        )
        try:
            review_report = await self.provider.generate_json(review_prompt, ReviewReport, config, model_override=rev_model)
            
            # Attach report to document for frontend "Interactive Mode"
            draft_doc.review_report = review_report
            
            has_errors = len(review_report.mermaid_errors) > 0 or len(review_report.text_issues) > 0
            
            # --- INTERACTIVE MODE CHECK ---
            if config and config.interactive_review:
                await self._notify(f"[{label}] Role: REVIEWER (Interactive Mode). Returning report without repair.", status_callback)
                self._cache[cache_key] = draft_doc
                return draft_doc

            # --- DECISION LOGIC ---
            # If errors exist, we MUST repair, even if confidence is reported as high (LLM contradiction).
            if not has_errors:
                 if review_report.confidence_score > 0.9:
                    await self._notify(f"[{label}] Role: REVIEWER (High Confidence: {review_report.confidence_score}). Skipping repair.", status_callback)
                 else:
                    await self._notify(f"[{label}] Role: REVIEWER (PASSED: No violations).", status_callback)
                 
                 self._cache[cache_key] = draft_doc
                 return draft_doc

                
            await self._notify(f"[{label}] Role: REVIEWER (FAILED: {len(review_report.mermaid_errors)} logic, {len(review_report.text_issues)} text errors).", status_callback)
            
            # --- STEP 3: REPAIRER ---
            await self._notify(f"[{label}] Role: REPAIRER (Applying fixes)...", status_callback)
            repair_prompt = render_prompt(
                "05_task_repairer.j2",
                draft_content=draft_doc.content,
                errors_json=review_report.model_dump_json()
            )
            
            repair_result = await self.provider.generate_json(repair_prompt, RepairResult, config)
            
            final_doc = FlexDoc(
                content=self._sanitize_content(repair_result.repaired_document),
                thought_process=draft_doc.thought_process,
                review_report=review_report # Attach report to final also
            )
            self._cache[cache_key] = final_doc # Cache repaired result
            return final_doc
            
        except Exception as e:
            print(f"Review/Repair cycle failed: {e}")
            await self._notify(f"[{label}] Epistemic Loop interrupted ({str(e)}). Returning draft.", status_callback)
            return draft_doc

    def _sanitize_content(self, content: str) -> str:
        """
        Fixes common LLM markdown mistakes before processing.
        """
        if not content:
            return ""
            
        # 1. Fix incorrect fencing: ```graph TD -> ```mermaid\ngraph TD
        pattern = r"```\s*(graph\s+[A-Za-z]+|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|flowchart\s+[A-Za-z]+)"
        content = re.sub(pattern, r"```mermaid\n\1", content, flags=re.IGNORECASE)

        # 2. Fix invalid Mermaid arrow syntax: -->|Label|> to -->|Label|
        # Matches -->|Text|> and -.->|Text|>
        arrow_pattern_1 = r"(-?->\|[^|]+\|)>"
        content = re.sub(arrow_pattern_1, r"\1", content)

        # 3. Fix invalid Mermaid label syntax: --> "Label" Node to -->|Label| Node
        # Matches --> "Label" Node
        arrow_pattern_2 = r"(-?->)\s*\"([^\"]+)\"\s*([A-Za-z0-9_]+)"
        content = re.sub(arrow_pattern_2, r"\1|\2| \3", content)

        # 4. Remove Setext header underlines or decorative separators (long strings of = or -)
        # Matches lines that are just ===... or ---... (min length 3)
        content = re.sub(r"^\s*[-=]{3,}\s*$", "", content, flags=re.MULTILINE)
        
        return content

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
