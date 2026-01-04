"""
Unit tests for prompt templates.
Tests that each template renders correctly and contains expected content.
"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.prompt_loader import render_prompt


class TestCorePersonas:
    """Test Core Persona prompts."""
    
    def test_persona_writer_renders(self):
        prompt = render_prompt("components/persona_writer.j2")
        assert "Clarion" in prompt
        assert "NO DUPLICATION" in prompt or "No Duplication" in prompt
        assert "Evidence-Based" in prompt
        # Verify domain-agnostic (no industry-specific terms)
        assert "cybersecurity" not in prompt.lower()
        assert "automotive" not in prompt.lower()
        
    def test_persona_editor_renders(self):
        prompt = render_prompt("components/persona_editor.j2")
        assert "Clarion QA" in prompt or "Technical Editor" in prompt
        assert "Duplicate Detection" in prompt
        assert "NEVER add new information" in prompt or "never invent" in prompt.lower()


class TestFormatRules:
    """Test Format Rule templates."""
    
    def test_rules_mermaid_has_examples(self):
        prompt = render_prompt("components/rules_mermaid.j2")
        # Check for BAD/GOOD examples
        assert "❌" in prompt or "BAD" in prompt
        assert "✅" in prompt or "GOOD" in prompt
        # Verify domain-agnostic examples
        assert "NodeA" in prompt or "NodeB" in prompt
        # Should NOT have domain-specific examples
        assert "ECU" not in prompt
        assert "Transport Layer" not in prompt
        
    def test_rules_json_has_critical_rules(self):
        prompt = render_prompt("components/rules_json.j2")
        assert "JSON Only" in prompt or "ENTIRE response" in prompt
        assert "No Markdown Wrapping" in prompt or "NOT wrap in code blocks" in prompt
        assert "No Explanatory Text" in prompt
        assert "content" in prompt  # Must reference content field


class TestTaskInstructions:
    """Test Task Instruction templates."""
    
    def test_generation_includes_persona(self):
        prompt = render_prompt("generation.j2", context="Test context", instruction="Write docs", system_guidelines="Guidelines")
        assert "Clarion" in prompt
        assert "Test context" in prompt
        assert "Write docs" in prompt
        
    def test_review_has_fix_priorities(self):
        prompt = render_prompt("review.j2", draft_content="# Draft\n\nContent", relevant_rules="")
        assert "Remove Duplication" in prompt or "duplication" in prompt.lower()
        assert "Fix Mermaid" in prompt or "mermaid" in prompt.lower()
        assert "# Draft" in prompt
        
    def test_consolidate_addresses_chunks(self):
        prompt = render_prompt("consolidate.j2", merged_content="# Title\n\n# Title\n\nDuplicate")
        assert "multiple independent chunks" in prompt.lower() or "chunks" in prompt
        assert "Merge Duplicate Headers" in prompt or "duplicate" in prompt.lower()
        assert "# Title" in prompt


class TestSystemUtilities:
    """Test System Utility templates."""
    
    def test_system_guidelines_includes_persona(self):
        prompt = render_prompt("system_guidelines.j2")
        assert "Clarion" in prompt
        
    def test_json_enforcement_wrapper(self):
        prompt = render_prompt("json_enforcement.j2", prompt="Task", schema_json='{"type": "object"}')
        assert "Task" in prompt
        assert "JSON" in prompt
        assert '{"type": "object"}' in prompt
        
    def test_repair_shows_error(self):
        prompt = render_prompt("repair.j2", error="Invalid JSON", schema_json='{"type": "object"}')
        assert "Invalid JSON" in prompt
        assert "previous output was invalid" in prompt.lower()


def test_no_cybersecurity_bias():
    """Ensure NO domain-specific bias across all prompts."""
    prompts_to_check = [
        ("components/persona_writer.j2", {}),
        ("components/persona_editor.j2", {}),
        ("components/rules_mermaid.j2", {}),
        ("components/rules_json.j2", {}),
        ("generation.j2", {"context": "test", "instruction": "test", "system_guidelines": "test"}),
        ("review.j2", {"draft_content": "test", "relevant_rules": ""}),
        ("consolidate.j2", {"merged_content": "test"}),
    ]
    
    for template, params in prompts_to_check:
        prompt = render_prompt(template, **params)
        # Check for common domain-specific terms
        assert "cybersecurity" not in prompt.lower(), f"{template} contains 'cybersecurity'"
        assert "automotive" not in prompt.lower(), f"{template} contains 'automotive'"
        # ECU is OK in mermaid rules ONLY if used as generic example, but Transport Layer is not
        if template != "components/rules_mermaid.j2":
            assert "ECU" not in prompt, f"{template} contains 'ECU'"
