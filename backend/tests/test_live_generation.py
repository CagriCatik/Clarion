
import pytest
import shutil
import os
from pathlib import Path
from clarion.pipeline import run_pipeline
from clarion.schemas import InstructionConfig, GenerationConfig
from clarion.providers import OllamaProvider
from clarion.server import OUTPUT_DIR

# Hardcoded input file as requested
REAL_INPUT = Path(r"C:\Users\mccat\Documents\Clarion\inputs\01_protection-eavesdrop.md")

@pytest.mark.asyncio
async def test_live_generation_eavesdrop():
    """
    LIVE INTEGRATION TEST
    ---------------------
    Uses:
    1. Real File: inputs/01_protection-eavesdrop.md
    2. Real Pipeline: No mocks.
    3. Real LLM: Connects to local Ollama (if available).
    
    Objective: Verify the system can digest a real production document and generate output throughout the whole stack.
    """
    
    # 1. Pre-checks
    if not REAL_INPUT.exists():
        pytest.skip(f"Input file missing: {REAL_INPUT}")
        
    # Check Ollama connectivity
    provider = OllamaProvider(model_name="llama3.1:8b")
    
    try:
        models = await provider.list_models()
        if not models:
            pytest.skip("Ollama reachable but no models found.")
    except Exception:
        pytest.skip("Ollama not running or unreachable. Skipping live generation.")

    print(f"\n[Live Test] Processing {REAL_INPUT.name} ({REAL_INPUT.stat().st_size} bytes)")
    
    # 2. Configuration
    # We use "Fast Mode" to avoid long waiting times during tests, 
    # but it still exercises the Generator + Pipeline Logic + Real LLM.
    instr_config = InstructionConfig(
        inline_instruction="Generate a concise security summary."
    )
    gen_config = GenerationConfig(
        fast_mode=True,       # Skip Review/Repair for speed
        num_ctx=4096,
        model="llama3.1:8b"     # Ensure we use a model likely to exist or fallback
    )
    
    async def progress(msg):
        print(f"  [Pipeline] {msg}")

    # 3. Execution (Real)
    try:
        result = await run_pipeline(
            config=instr_config,
            input_path=str(REAL_INPUT),
            provider=provider,
            generation_config=gen_config,
            status_callback=progress
        )
        
        # 4. assertions
        assert result is not None
        assert result.input_file == str(REAL_INPUT)
        
        content = result.final_doc.content
        assert content is not None
        assert len(content) > 50, "Generated content was suspiciously short"
        
        print(f"\n[Success] Generated {len(content)} chars.")
        print(f"Preview:\n{content[:200]}...")
        
        # 5. Verify Output Saving Loop (Simulated)
        # The pipeline returns the result, Server usually saves it. 
        # We manually save it here to verify it's writeable.
        OUTPUT_DIR.mkdir(exist_ok=True)
        out_path = OUTPUT_DIR / f"{REAL_INPUT.stem}_TEST_ARTIFACT.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        assert out_path.exists()
        
        # Cleanup
        out_path.unlink()
        
    except Exception as e:
        pytest.fail(f"Live generation failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
