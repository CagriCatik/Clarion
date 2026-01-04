"""
Integration tests for the full prompt chain.
Tests Generate → Review → Consolidate workflow with actual LLM calls.
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clarion.providers import OllamaProvider
from clarion.schemas import FlexDoc, GenerationConfig
from clarion.prompt_loader import render_prompt


class TestGenerationChain:
    """Test the Generate → Review → Consolidate chain."""
    
    @pytest.fixture
    def provider(self):
        """Create LLM provider for tests."""
        return OllamaProvider(model_name="llama3.1:8b")
    
    @pytest.fixture
    def config(self):
        """Standard generation config for tests."""
        return GenerationConfig(
            temperature=0.2,
            num_ctx=8192,
            num_predict=2048,
            fast_mode=True
        )
    
    @pytest.mark.asyncio
    async def test_generation_produces_valid_json(self, provider, config):
        """Test that generation prompt produces valid FlexDoc."""
        prompt = render_prompt(
            "generation.j2",
            context="A simple HTTP server that listens on port 8080 and returns 'Hello World' for GET requests.",
            instruction="Write technical documentation explaining the server architecture.",
            system_guidelines=render_prompt("system_guidelines.j2")
        )
        
        result = await provider.generate_json(prompt, FlexDoc, config)
        
        # Verify structure
        assert isinstance(result, FlexDoc)
        assert result.content is not None
        assert len(result.content) > 100  # Should be substantial
        
        # Verify no JSON schema leak
        assert '"type": "object"' not in result.content
        assert '"properties"' not in result.content
        
    @pytest.mark.asyncio
    async def test_generation_includes_thought_process(self, provider, config):
        """Test that thought_process field is used."""
        prompt = render_prompt(
            "generation.j2",
            context="Database connection pooling mechanism with retry logic.",
            instruction="Document the retry strategy.",
            system_guidelines=render_prompt("system_guidelines.j2")
        )
        
        result = await provider.generate_json(prompt, FlexDoc, config)
        
        # Thought process should contain planning keywords
        if result.thought_process:
            tp_lower = result.thought_process.lower()
            assert any(word in tp_lower for word in ["structure", "explain", "diagram", "section", "overview"])
    
    @pytest.mark.asyncio
    async def test_review_fixes_mermaid_syntax(self, provider, config):
        """Test that review prompt fixes Mermaid syntax errors."""
        # Draft with intentional Mermaid errors
        draft_with_errors = """
# Documentation

```mermaid
graph TD
    Start Node["Beginning"]  
    Data Processor-->End Node[Done]
    Start-->|Label| End
```
"""
        
        prompt = render_prompt(
            "review.j2",
            draft_content=draft_with_errors,
            relevant_rules=""
        )
        
        result = await provider.generate_json(prompt, FlexDoc, config)
        
        # Should fix spaces in node IDs
        assert "Start Node" not in result.content
        assert "Data Processor" not in result.content
        assert "End Node" not in result.content
        
        # Should remove pipe syntax
        assert "-->|" not in result.content
        
    @pytest.mark.asyncio
    async def test_review_removes_duplication(self, provider, config):
        """Test that review removes duplicate sections."""
        draft_with_duplication = """
# Overview
The system processes data.

# Introduction
The system processes data.

# Details
The system processes data.
"""
        
        prompt = render_prompt(
            "review.j2",
            draft_content=draft_with_duplication,
            relevant_rules=""
        )
        
        result = await provider.generate_json(prompt, FlexDoc, config)
        
        # Count occurrences of "system processes data"
        occurrences = result.content.lower().count("system processes data")
        
        # Should consolidate to 1-2 mentions max (introduction + maybe one detail)
        assert occurrences <= 2, f"Found {occurrences} duplicates, expected ≤2"
        
    @pytest.mark.asyncio
    async def test_consolidate_merges_duplicate_headers(self, provider, config):
        """Test that consolidate merges duplicate top-level headers."""
        merged_chunks = """
# System Documentation

## Overview
First chunk overview.

# System Documentation

## Overview
Second chunk overview.

# System Documentation

## Overview
Third chunk overview.
"""
        
        prompt = render_prompt(
            "consolidate.j2",
            merged_content=merged_chunks
        )
        
        result = await provider.generate_json(prompt, FlexDoc, config)
        
        # Should have only ONE top-level header
        header_count = result.content.count("# System Documentation")
        assert header_count == 1, f"Found {header_count} top-level headers, expected 1"
        
        # Should have consolidated overview
        overview_count = result.content.count("## Overview")
        assert overview_count <= 1, f"Found {overview_count} Overview sections, expected ≤1"


class TestFullPipelineIntegration:
    """Test the complete pipeline: Generate → Review → Consolidate."""
    
    @pytest.fixture
    def provider(self):
        return OllamaProvider(model_name="llama3.1:8b")
    
    @pytest.fixture
    def config(self):
        return GenerationConfig(
            temperature=0.2,
            num_ctx=8192,
            num_predict=1024,  # Keep short for fast tests
            fast_mode=True
        )
    
    @pytest.mark.asyncio
    async def test_complete_workflow_no_duplication(self, provider, config):
        """
        Test the full workflow produces ONE coherent document.
        Generate → Review → Consolidate should result in no duplicate sections.
        """
        # Step 1: Generate
        gen_prompt = render_prompt(
            "generation.j2",
            context="A REST API with authentication middleware that validates JWT tokens.",
            instruction="Document the authentication flow.",
            system_guidelines=render_prompt("system_guidelines.j2")
        )
        
        draft = await provider.generate_json(gen_prompt, FlexDoc, config)
        
        # Step 2: Review
        review_prompt = render_prompt(
            "review.j2",
            draft_content=draft.content,
            relevant_rules=""
        )
        
        reviewed = await provider.generate_json(review_prompt, FlexDoc, config)
        
        # Step 3: Consolidate (simulating chunk merge by duplicating)
        merged = f"{reviewed.content}\n\n{reviewed.content}"  # Artificial duplication
        
        consolidate_prompt = render_prompt(
            "consolidate.j2",
            merged_content=merged
        )
        
        final = await provider.generate_json(consolidate_prompt, FlexDoc, config)
        
        # Verification: Final should be shorter than artificial duplication
        assert len(final.content) < len(merged), "Consolidation should reduce length by removing duplication"
        
        # Count unique top-level headers
        lines = final.content.split('\n')
        h1_headers = [line for line in lines if line.startswith('# ') and not line.startswith('## ')]
        
        # Should have ideally 1 top-level header
        assert len(h1_headers) <= 2, f"Found {len(h1_headers)} top-level headers, expected ≤2"
    
    @pytest.mark.asyncio
    async def test_mermaid_survives_full_chain(self, provider, config):
        """Test that Mermaid diagrams remain valid through full chain."""
        # Generate with intentional bad Mermaid
        gen_prompt = render_prompt(
            "generation.j2",
            context="""State machine with three states: Idle, Processing, Complete.
Transitions: Idle->Processing on 'start', Processing->Complete on 'finish'.""",
            instruction="Document with a state diagram.",
            system_guidelines=render_prompt("system_guidelines.j2")
        )
        
        draft = await provider.generate_json(gen_prompt, FlexDoc, config)
        
        # Review should fix any syntax
        review_prompt = render_prompt(
            "review.j2",
            draft_content=draft.content,
            relevant_rules=""
        )
        
        reviewed = await provider.generate_json(review_prompt, FlexDoc, config)
        
        # Final document should have valid Mermaid
        assert "```mermaid" in reviewed.content
        
        # Check for common errors that should NOT be present
        assert " Node" not in reviewed.content  # No spaces in IDs
        assert "-->|" not in reviewed.content   # No pipe syntax


# Performance marker for slow tests
pytestmark = pytest.mark.slow
