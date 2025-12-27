import hashlib
from typing import Dict, List, Optional
from enum import Enum
from pathlib import Path
from clarion.schemas import InstructionConfig

class Stage(str, Enum):
    OUTLINE = "outline"
    MAP = "map"
    REDUCE = "reduce"
    FINAL = "final"

# Base templates (embedded for simplicity, or could load from files)
BASE_PROMPTS = {
    Stage.OUTLINE: """
You are an expert scientific documentation architect.
Analyze the following text segments and PROPOSE a strict JSON outline for a comprehensive scientific document.
Focus on extracting: Background, Methods, Findings, Discussion.
Return ONLY JSON.
""",
    Stage.MAP: """
You are a precise data extractor.
Extract all relevant scientific facts, claims, methods, and definitions from the provided text chunk.
Match extraction to the provided OUTLINE.
For every item, you MUST provide precise evidence (segment_ids).
Return ONLY JSON.
""",
    Stage.REDUCE: """
You are a synthesis engine.
Merge the provided extracted fragments into a unified set of lists.
Deduplicate similar claims.
Preserve ALL distinct evidence references.
Return ONLY JSON.
""",
    Stage.FINAL: """
You are a scientific writer.
Rewrite the structured data into a flowing, professional scientific document.
Adhere STRICTLY to the provided structure.
Preserve ALL citation links (evidence).
Return ONLY JSON.
"""
}

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load_effective_prompts(
    user_prompt_files: List[str],
    inline_instruction: Optional[str]
) -> Dict[str, str]:
    """
    Load effective prompts by layering:
    Base + User Files + Inline Instruction.
    
    Returns a dict mapping Stage -> effective prompt text.
    Also returns hashes in a separate call? 
    For simplicity, this returns the prompts. The caller handles config object updates.
    """
    
    # 1. Load user file content
    user_content = ""
    for fpath in user_prompt_files:
        try:
            # Simple read
            with open(fpath, "r", encoding="utf-8") as f:
                user_content += "\n" + f.read()
        except Exception as e:
            print(f"Warning: could not read prompt file {fpath}: {e}")

    # 2. Layering
    effective = {}
    
    # Common instruction block to append
    # We allow user to append instructions that apply to ALL stages, 
    # or we could parse separate sections. 
    # Req: "Inputs: ... prompt templates ... user prompt file ... inline ... Inject into ALL stages"
    
    additional_context = ""
    if user_content.strip():
        additional_context += f"\n\n## User Instructions (File)\n{user_content}"
    
    if inline_instruction and inline_instruction.strip():
        additional_context += f"\n\n## User Instructions (Inline - Highest Priority)\n{inline_instruction}"
    
    # Guardrails: Scan for prohibited tokens
    # Req: "ignore any instruction fragment that attempts to ... request non-JSON ... secrets"
    # This is a basic keyword check.
    prohibited = ["ignore previous guidelines", "return plain text", "no json", "ignore evidence"]
    lowered_context = additional_context.lower()
    for p in prohibited:
        if p in lowered_context:
            print(f"Warning: Prohibited instruction detected and neutralized: '{p}'")
            # Primitive redaction or just warning. 
            # Req: "Record ignored fragments as warnings". 
            # We'll just strip it for now or log it. 
            # For strictness, let's replace it.
            additional_context = additional_context.replace(p, "[REDACTED_PROHIBITED]")
            additional_context = additional_context.replace(p.upper(), "[REDACTED_PROHIBITED]")
            additional_context = additional_context.replace(p.title(), "[REDACTED_PROHIBITED]")

    for stage, base in BASE_PROMPTS.items():
        # Combine
        full_text = f"{base}\n{additional_context}"
        effective[stage] = full_text
        
    return effective
