from typing import List, Optional, Literal
from pydantic import BaseModel, Field

# --- Diagram Specification ---

class MermaidNode(BaseModel):
    id: str = Field(..., description="Alphanumeric ID (e.g., Node1)")
    label: str = Field(..., description="Text label for the node")

class MermaidEdge(BaseModel):
    source: str = Field(..., description="Source Node ID")
    target: str = Field(..., description="Target Node ID")
    label: Optional[str] = Field(None, description="Edge label (optional)")
    type: Literal["solid", "dotted"] = Field("solid", description="solid (-->) or dotted (-.->)")

class DiagramSpec(BaseModel):
    """
    Canonical representation of a flowchart.
    """
    direction: Literal["TD", "LR"] = "TD"
    nodes: List[MermaidNode] = Field(default_factory=list)
    edges: List[MermaidEdge] = Field(default_factory=list)

# --- Linting & Results ---

class LintError(BaseModel):
    line: int
    issue: str
    suggested_fix: str

class LintReport(BaseModel):
    is_valid: bool
    errors: List[LintError] = Field(default_factory=list)

class MermaidResult(BaseModel):
    status: Literal["ok", "no_mermaid", "error"]
    mermaid_code: Optional[str] = None
    fallback_text: Optional[str] = None
    lint_report: Optional[LintReport] = None
