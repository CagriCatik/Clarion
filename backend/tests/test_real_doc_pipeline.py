
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from clarion.pipeline import DirectPipeline, InstructionConfig, GenerationConfig, estimate_tokens
from clarion.schemas import FlexDoc, ReviewReport, RepairResult, DeciderResponse

# Input File Path
REAL_DOC_PATH = Path(r"C:\Users\mccat\Documents\Clarion\inputs\01_protection-eavesdrop.md")

class MockProviderWithLogic:
    def __init__(self):
        self.call_count = 0
        
    async def generate_json(self, prompt, schema, config=None, **kwargs):
        self.call_count += 1
        # Basic mock responses
        if schema == FlexDoc:
            return FlexDoc(content="# Mock Generated Doc\n\nBased on real input.", thought_process="Mocking...")
        if schema == DeciderResponse:
            return DeciderResponse(use_mermaid=False)
        if schema == ReviewReport:
            return ReviewReport(mermaid_errors=[], text_issues=[], confidence_score=0.95)
        return None

@pytest.mark.asyncio
async def test_pipeline_with_real_input_file():
    """
    Integration test using the specific real document: 01_protection-eavesdrop.md
    Verifies that the file loads, token estimation works, and the pipeline accepts it.
    """
    if not REAL_DOC_PATH.exists():
        pytest.skip(f"Real input file not found at {REAL_DOC_PATH}")

    # 1. Read File
    with open(REAL_DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    print(f"\n[Test Info] Real Doc Length: {len(content)} chars")
    
    # 2. Estimate Tokens
    est_tokens = estimate_tokens(content)
    print(f"[Test Info] Estimated Tokens: {est_tokens}")
    
    # 3. Setup Pipeline
    provider = MockProviderWithLogic()
    pipeline = DirectPipeline(provider)
    
    # Config setup
    instr_config = InstructionConfig(inline_instruction="Generate security documentation.")
    gen_config = GenerationConfig(
        num_ctx=4096, # Set a limit to test strategy selection
        fast_mode=False
    )
    
    status_updates = []
    async def on_status(msg):
        status_updates.append(msg)
        print(f"[Pipeline Status] {msg}")

    # 4. Run Pipeline
    result = await pipeline.run(
        input_path=str(REAL_DOC_PATH),
        input_text_full=content,
        instruction_config=instr_config,
        generation_config=gen_config,
        status_callback=on_status
    )

    # 5. Assertions
    assert result is not None
    assert result.input_file == str(REAL_DOC_PATH)
    assert "Mock Generated Doc" in result.final_doc.content
    
    # Verify Strategy Selection via logs
    # 01_protection-eavesdrop.md is ~3.6KB. 
    # 3600 chars / 4 = ~900 tokens.
    # Safe limit = 4096 - 2000 = 2096 tokens.
    # Should be ONE-SHOT.
    
    strategy_log = next((msg for msg in status_updates if "Strategy:" in msg), None)
    assert strategy_log is not None
    
    if est_tokens <= (4096 - 2000):
        assert "One-Shot" in strategy_log
    else:
        assert "Parallel Windows" in strategy_log

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
