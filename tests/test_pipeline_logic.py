import pytest
import os
from unittest.mock import MagicMock
from clarion.pipeline import DirectPipeline
from clarion.schemas import InstructionConfig, GenerationConfig, FlexDoc

@pytest.mark.asyncio
async def test_pipeline_one_shot_strategy(mock_provider, sample_markdown, tmp_path):
    # Setup
    input_file = tmp_path / "test.md"
    input_file.write_text(sample_markdown)
    
    pipeline = DirectPipeline(mock_provider)
    instruction = InstructionConfig(inline_instruction="Test instruction")
    gen_config = GenerationConfig(num_ctx=4096)
    
    # 1 response for draft, 1 for review
    mock_provider.add_response(FlexDoc(content="Draft content"))
    mock_provider.add_response(FlexDoc(content="Refined content"))
    
    # Run
    result = await pipeline.run(str(input_file), sample_markdown, instruction, gen_config)
    
    # Verify
    assert "Refined content" in result.final_doc.content
    assert len(mock_provider.calls) == 2 # Draft + Review
    assert "Instruction" in mock_provider.calls[0]["prompt"]

@pytest.mark.asyncio
async def test_pipeline_windowed_strategy(mock_provider, large_markdown, tmp_path):
    # Setup
    input_file = tmp_path / "large.md"
    input_file.write_text(large_markdown)
    
    pipeline = DirectPipeline(mock_provider)
    instruction = InstructionConfig(inline_instruction="Test large")
    # Force windowing by setting low context or large file
    gen_config = GenerationConfig(num_ctx=2048, chunk_size=1000, chunk_overlap=100)
    
    # Add enough responses for multiple windows
    # large_markdown is ~35k chars, chunk_size=1000 -> ~35 windows?
    # Actually safe_input_limit * 4 is used for chunk_size if not provided.
    # In test, we provide chunk_size=1000.
    num_windows = (len(large_markdown) // 900) + 1 # rough estimate
    for _ in range(num_windows * 2): # Draft + Review for each
        mock_provider.add_response(FlexDoc(content="Part content "))
        
    # Run
    result = await pipeline.run(str(input_file), large_markdown, instruction, gen_config)
    
    # Verify
    assert "Part content" in result.final_doc.content
    # Each window does 1 Draft + 1 Review (if not fast_mode) village
    assert len(mock_provider.calls) > 2 

@pytest.mark.asyncio
async def test_pipeline_fast_mode_skips_refinement(mock_provider, sample_markdown, tmp_path):
    # Setup
    input_file = tmp_path / "test_fast.md"
    input_file.write_text(sample_markdown)
    
    pipeline = DirectPipeline(mock_provider)
    instruction = InstructionConfig(inline_instruction="Fast test")
    gen_config = GenerationConfig(fast_mode=True)
    
    mock_provider.add_response(FlexDoc(content="Draft only"))
    
    # Run
    result = await pipeline.run(str(input_file), sample_markdown, instruction, gen_config)
    
    # Verify
    assert "Draft only" in result.final_doc.content
    assert len(mock_provider.calls) == 1 # No review call
