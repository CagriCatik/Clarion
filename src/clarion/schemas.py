from typing import List, Optional
from pydantic import BaseModel, Field

class GenerationConfig(BaseModel):
    """
    LLM generation parameters.
    """
    temperature: float = 0.2
    top_p: float = 0.9
    num_ctx: int = 4096
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    repeat_penalty: float = 1.1
    top_k: int = 40
    
class InstructionConfig(BaseModel):
    """
    Configuration for prompt ingestion from user files and inline text.
    """
    base_prompt_hashes: dict[str, str] = Field(default_factory=dict)
    user_prompt_files: List[str] = Field(default_factory=list)
    inline_instruction: Optional[str] = None
    effective_prompt_hashes: dict[str, str] = Field(default_factory=dict)

# --- Simplified Document Models (No Citations/Evidence) ---

class GlossaryTerm(BaseModel):
    term: str
    definition: str

class Claim(BaseModel):
    claim: str
    confidence: str = Field(..., pattern="^(high|medium|low)$")

class ActionItem(BaseModel):
    action: str
    owner: Optional[str] = None
    due_date: Optional[str] = None

class FlexDoc(BaseModel):
    """
    Flexible document container.
    """
    thought_process: Optional[str] = Field(
        None, 
        description="Internal reasoning/planning block. Use this to analyze the request before generating content."
    )
    content: str = Field(..., description="The main markdown content.")

class DocResult(BaseModel):
    """
    Final output structure.
    """
    input_file: str
    final_doc: FlexDoc
    manifest_path: str
