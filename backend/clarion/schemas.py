from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class GenerationConfig(BaseModel):
    """
    LLM generation parameters.
    """
    temperature: float = 0.2
    top_p: float = 0.9
    num_ctx: int = 16384
    num_predict: int = 8192
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    repeat_penalty: float = 1.1
    top_k: int = 40
    fast_mode: bool = False

    # --- Multi-Model & Interactive Config ---
    generator_model: Optional[str] = Field(None, description="Model to use for Drafting (e.g. phi3)")
    reviewer_model: Optional[str] = Field(None, description="Model to use for Reviewing (e.g. llama3.1)")
    interactive_review: bool = Field(False, description="If True, return ReviewReport without auto-repairing.")
    
class InstructionConfig(BaseModel):
    """
    Configuration for prompt ingestion from user files and inline text.
    """
    base_prompt_hashes: dict[str, str] = Field(default_factory=dict)
    user_prompt_files: List[str] = Field(default_factory=list)
    inline_instruction: Optional[str] = None
    effective_prompt_hashes: dict[str, str] = Field(default_factory=dict)

# --- Simplified Document Models ---

class FlexDoc(BaseModel):
    """
    Flexible document container for Generator output.
    """
    thought_process: Optional[str] = Field(None, description="Internal reasoning.")
    content: str = Field(..., description="The main markdown content.")
    review_report: Optional['ReviewReport'] = Field(None, description="Attached review findings if available.")

from clarion.mermaid.schemas import DiagramSpec

class DeciderResponse(BaseModel):
    use_mermaid: bool
    diagram_intent: Optional[str] = None
    spec: Optional[DiagramSpec] = None

# --- Reviewer Schemas ---

class MermaidError(BaseModel):
    diagram_id: str
    block_index: int
    line: int
    issue: str
    suggested_fix: str

class TextIssue(BaseModel):
    location: str
    issue: str
    suggested_fix: str

class ReviewReport(BaseModel):
    mermaid_errors: List[MermaidError] = Field(default_factory=list)
    text_issues: List[TextIssue] = Field(default_factory=list)
    confidence_score: float = Field(1.0, description="Confidence in the DRAFT's quality (0.0 to 1.0). If > 0.9, repair may be skipped.")

# --- Repairer Schemas ---

class RepairResult(BaseModel):
    repaired_document: str
    repair_notes: List[str] = Field(default_factory=list)

class DocResult(BaseModel):
    """
    Final output structure.
    """
    input_file: str
    final_doc: FlexDoc
    manifest_path: str
