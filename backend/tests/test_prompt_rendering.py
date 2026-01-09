from clarion.prompt_loader import render_prompt
import pytest

def test_system_guidelines_rendering():
    """Verify system guidelines include persona and mermaid rules."""
    sg = render_prompt("01_system_core.j2")
    assert "deterministic epistemic document system" in sg.lower(), "System ID missing"
    assert "ROLE INVARIANTS" in sg, "Invariants missing"

def test_review_prompt_rendering():
    """Verify review prompt includes editor persona and rules."""
    rv = render_prompt("04_task_reviewer.j2", draft_content="TEST")
    assert "REVIEWER" in rv.upper()
    assert "Mermaid" in rv
    
def test_repair_prompt_rendering():
    """Verify repair prompt includes strict constraints."""
    rp = render_prompt("05_task_repairer.j2", error="TEST", draft_content="Draft", errors_json="{}")
    assert "OUTPUT FORMAT (JSON ONLY)" in rp or "valid JSON" in rp
    assert "REPAIRER" in rp
