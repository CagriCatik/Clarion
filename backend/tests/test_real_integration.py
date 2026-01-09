import pytest
import asyncio
import os
from clarion.pipeline import DirectPipeline, InstructionConfig, GenerationConfig
from clarion.providers import OllamaProvider
from clarion.schemas import DocResult

# USE REAL LOCAL OLLAMA INSTANCE on port 11434
# This requires the user to have 'ollama serve' running locally or via Docker
LOCAL_OLLAMA_URL = "http://localhost:11434"

@pytest.mark.asyncio
async def test_real_epistemic_pipeline():
    """
    INTEGRATION TEST: Runs the full pipeline against the real Ollama model.
    """
    # 1. Setup Provider
    try:
        provider = OllamaProvider(base_url=LOCAL_OLLAMA_URL, model="olmo-3:7b")
        # Check connectivity
        models = await provider.list_models()
        print(f"\nConnected to Ollama. Available models: {[m['name'] for m in models]}")
    except Exception as e:
        pytest.skip(f"Skipping integration test: Could not connect to Ollama at {LOCAL_OLLAMA_URL}. Error: {e}")

    # 2. Setup Pipeline
    pipeline = DirectPipeline(provider)
    
    # 3. Load Real Input File
    input_file = "inputs/secure_ota.md"
    if not os.path.exists(input_file):
        # Fallback if running from a different root
        input_file = "../inputs/secure_ota.md"
        
    if not os.path.exists(input_file):
        # Create a dummy real file if missing
        with open("inputs/test_real.md", "w") as f:
            f.write("# Real Input\nThis is a test file for the integration test.\nIt should be long enough to trigger the review process.\n" * 10)
        input_file = "inputs/test_real.md"

    print(f"\nProcessing real file: {input_file}")
    
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    # 4. Config
    instr = InstructionConfig(inline_instruction="Generate a detailed technical specification with a Mermaid sequence diagram.")
    gen_config = GenerationConfig(num_ctx=4096, fast_mode=False) # Ensure review is ON
    
    # 5. Execute
    result = await pipeline.run(
        input_path=input_file,
        input_text_full=text,
        instruction_config=instr,
        generation_config=gen_config,
        status_callback=lambda msg: print(f"  -> {msg}")
    )
    
    # 6. Assertions
    assert isinstance(result, DocResult)
    assert len(result.final_doc.content) > 100, "Output should be substantial"
    
    # Check for Epistemic Artifacts
    if "```mermaid" in result.final_doc.content:
        print("\n[SUCCESS] Generated content includes Mermaid diagram.")
    else:
        print("\n[WARNING] No Mermaid diagram generated (Model choice or input dependent).")
        
    print(f"\nFinal Document Preview:\n{result.final_doc.content[:500]}...")
