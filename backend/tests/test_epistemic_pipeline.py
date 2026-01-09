import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from clarion.pipeline import DirectPipeline, InstructionConfig, GenerationConfig
from clarion.schemas import FlexDoc, ReviewReport, RepairResult, DocResult

# Mock the LLM Provider
class MockProvider:
    async def generate_json(self, prompt, schema, config=None, **kwargs):
        if schema == FlexDoc:
            return FlexDoc(content="# Mock Draft\nContent is now long enough to trigger the review process properly.", thought_process="Thinking...")
        if schema == ReviewReport:
            # Return low confidence to trigger repair
            return ReviewReport(
                mermaid_errors=[], 
                text_issues=[{"location": "Title", "issue": "Passive voice", "suggested_fix": "Active voice"}],
                confidence_score=0.8
            )
        if schema == RepairResult:
            return RepairResult(repaired_document="# Repaired Draft\nFixed Content.", repair_notes=["Fixed passive voice"])
        return None

@pytest.mark.asyncio
async def test_epistemic_pipeline_flow():
    """
    Test the full Generator -> Reviewer -> Repairer loop.
    """
    provider = MockProvider()
    pipeline = DirectPipeline(provider)
    
    config = InstructionConfig(inline_instruction="Test Instruction")
    gen_config = GenerationConfig()
    
    # Run
    # Input must be long enough to avoid "Short input" skip logic if using mocked content
    result = await pipeline.run(
        input_path="dummy.md",
        input_text_full="Short input text for one-shot strategy.",
        instruction_config=config,
        generation_config=gen_config,
        status_callback=AsyncMock()
    )
    
    assert isinstance(result, DocResult)
    # Since confidence was 0.8 and errors existed, it should have been repaired
    assert "Repaired" in result.final_doc.content

@pytest.mark.asyncio
async def test_confidence_optimization():
    """
    Test that High Confidence (>0.9) skips the repair step.
    """
    provider = MockProvider()
    
    # Override to return high confidence
    async def high_conf_review(*args, **kwargs):
        return ReviewReport(
            mermaid_errors=[], 
            text_issues=[{"location": "Nit", "issue": "Minor", "suggested_fix": "Ignore"}],
            confidence_score=0.95 
        )
    
    # Content must be > 50 chars to trigger review
    long_content = "# Draft Content\n" + ("This is a long enough content to pass the length check" * 2)

    # Mock Decider response
    from clarion.schemas import DeciderResponse
    
    provider.generate_json = AsyncMock(side_effect=[
        FlexDoc(content=long_content, thought_process=""), # Generator
        DeciderResponse(use_mermaid=False), # Decider
        ReviewReport(mermaid_errors=[], text_issues=[], confidence_score=0.95), # Reviewer
        # Repairer NOT called
    ])
    
    pipeline = DirectPipeline(provider)
    config = InstructionConfig()
    
    result = await pipeline.run(
        input_path="dummy.md", 
        input_text_full="Short input.", 
        instruction_config=config,
        status_callback=AsyncMock()
    )
    
    assert provider.generate_json.call_count == 3
    assert result.final_doc.content == long_content

@pytest.mark.asyncio
async def test_caching_mechanism():
    """
    Test that identical inputs hitting the pipeline return the CACHED result immediately.
    """
    provider = MockProvider()
    # Mock generator to be called only once
    provider.generate_json = AsyncMock(return_value=FlexDoc(content="Unique Content"))
    
    pipeline = DirectPipeline(provider)
    
    # First Run
    await pipeline.run("f1", "Input A", InstructionConfig(), status_callback=AsyncMock())
    
    # Second Run (Identical)
    await pipeline.run("f1", "Input A", InstructionConfig(), status_callback=AsyncMock())
    
    # Generator should only be called once due to cache hit
    assert provider.generate_json.call_count == 1
    
@pytest.mark.asyncio
async def test_parallel_windowing():
    """
    Test that large inputs trigger parallel asyncio.gather.
    """
    provider = MockProvider()
    provider.generate_json = AsyncMock(return_value=FlexDoc(content="Window Output"))
    
    pipeline = DirectPipeline(provider)
    
    # Create input larger than safe_input_limit (assume ~2000 chars limit)
    large_input = "A" * 10000 
    
    # Mock split_text to return 2 windows
    with patch("clarion.splitter.MarkdownSplitter.split_text", return_value=["Win1", "Win2"]):
        await pipeline.run("large.md", large_input, InstructionConfig(inline_instruction="Run"), status_callback=AsyncMock())
        
        # Should process 2 windows
        # Each window calls Generator -> (Reviewer -> Repairer optional)
        # Minimum calls to generator = 2
        assert provider.generate_json.call_count >= 2
