import pytest
import asyncio
import time
from unittest.mock import patch, Mock, AsyncMock
from clarion.pipeline import DirectPipeline
from clarion.schemas import InstructionConfig, GenerationConfig, FlexDoc
from clarion.knowledge import OllamaEmbeddingFunction

@pytest.fixture
def slow_mock_provider(mock_provider):
    # Wrap generate_json to simulate latency
    original_generate = mock_provider.generate_json
    
    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.1) # Simulate network/processing latency
        return await original_generate(*args, **kwargs)
        
    # We need to preserve the signature or at least make it awaitable
    mock_provider.generate_json = slow_generate
    return mock_provider

@pytest.mark.asyncio
async def test_concurrent_pipeline_execution(slow_mock_provider, sample_markdown, tmp_path):
    # Purpose: Verify that multiple pipeline runs can progress in parallel
    # If they were serial, total time would be N * 0.1s. 
    # With async, it should be closer to 0.1s + overhead.
    
    input_file_1 = tmp_path / "doc1.md"
    input_file_2 = tmp_path / "doc2.md"
    input_file_3 = tmp_path / "doc3.md"
    
    input_file_1.write_text(sample_markdown)
    input_file_2.write_text(sample_markdown)
    input_file_3.write_text(sample_markdown)
    
    pipeline = DirectPipeline(slow_mock_provider)
    instruction = InstructionConfig(inline_instruction="Concurrent Test")
    gen_config = GenerationConfig(fast_mode=True)
    
    # Pre-load responses for 3 parallel runs
    for _ in range(3):
        slow_mock_provider.add_response(FlexDoc(content="Parallel Result"))
        
    start_time = time.perf_counter()
    
    tasks = [
        pipeline.run(str(input_file_1), sample_markdown, instruction, gen_config),
        pipeline.run(str(input_file_2), sample_markdown, instruction, gen_config),
        pipeline.run(str(input_file_3), sample_markdown, instruction, gen_config)
    ]
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    # verify success
    assert len(results) == 3
    for res in results:
        assert "Parallel Result" in res.final_doc.content
        
    # Check that it was definitely faster than serial (3 * 0.1s = 0.3s)
    # Allow some overhead but it should be fast
    print(f"Concurrent duration: {duration:.4f}s")
    assert duration < 0.25, f"Expected < 0.25s, got {duration:.4f}s - Pipeline might be blocking event loop!"


def test_connection_pooling_reuses_client():
    # Verify that calling property `client` multiple times returns same instance
    ef = OllamaEmbeddingFunction(model_name="test")
    
    c1 = ef.client
    c2 = ef.client
    
    assert c1 is c2
    assert not c1.is_closed

@pytest.mark.asyncio
async def test_stress_large_input_chunking(mock_provider, large_markdown, tmp_path):
    # Stress test the chunking and merging logic overhead
    # Prefer real inputs if available in the 'inputs' directory village
    import os
    inputs_dir = "inputs"
    real_content = ""
    
    if os.path.isdir(inputs_dir):
        files = [f for f in os.listdir(inputs_dir) if f.endswith(".md")]
        if files:
            print(f"Loading real inputs for stress test: {files}")
            # Concatenate all inputs to make a big document
            for f in files:
                try:
                    with open(os.path.join(inputs_dir, f), "r", encoding="utf-8") as rf:
                        real_content += rf.read() + "\n\n"
                except Exception as e:
                    print(f"Skipping {f}: {e}")
                    
    # Use real content if it's substantial, otherwise fall back to fixture
    target_markdown = real_content if len(real_content) > 1000 else large_markdown
    input_file = tmp_path / "stress.md"
    input_file.write_text(target_markdown, encoding="utf-8")
    
    pipeline = DirectPipeline(mock_provider)
    instruction = InstructionConfig(inline_instruction="Stress Test")
    
    # Force heavy windowing
    gen_config = GenerationConfig(chunk_size=1000, chunk_overlap=0, fast_mode=True)
    
    # Estimate windows
    num_windows = (len(target_markdown) // 900) + 2
    for _ in range(num_windows):
        mock_provider.add_response(FlexDoc(content="Chunk result"))
        
    start_time = time.perf_counter()
    
    result = await pipeline.run(str(input_file), target_markdown, instruction, gen_config)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    print(f"Stress processing {len(target_markdown)} chars took {duration:.4f}s")
    
    # Assert reasonable overhead (should be fast with mock)
    assert duration < 3.0 # Slightly higher threshold for I/O
