
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from clarion.pipeline import DirectPipeline, InstructionConfig, GenerationConfig
from clarion.schemas import FlexDoc, ReviewReport, RepairResult, DeciderResponse, GenerationConfig as GenConfig

# Mock Provider
class HybridMockProvider:
    def __init__(self):
        self.call_log = []

    async def generate_json(self, prompt, schema, config=None, **kwargs):
        self.call_log.append(schema.__name__)
        
        if schema == FlexDoc:
            return FlexDoc(
                content="""
# Bad Diagram Doc

Here is a diagram with a forbidden syntax (ending with |>):

```mermaid
graph TD
    A["Start"] -->|Label|> B["End"]
```
""", 
                thought_process="Drafting with bad syntax..."
            )
            
        if schema == DeciderResponse:
            return DeciderResponse(use_mermaid=False) # Skip extra generation

        if schema == ReviewReport:
            # SIMULATE LLM BLINDNESS
            # The LLM Reviewer says "100% Perfect!", missing the syntax error.
            return ReviewReport(
                mermaid_errors=[], 
                text_issues=[], 
                confidence_score=1.0 
            )

        if schema == RepairResult:
            # The Repairer should fix it because the LINTER caught it
            return RepairResult(
                repaired_document="""
# Fixed Doc

```mermaid
graph TD
    A["Start"] -->|Label| B["End"]
```
""", 
                repair_notes=["Fixed invalid arrow Syntax"]
            )
            
        return None

@pytest.mark.asyncio
async def test_linter_overrides_llm_blindness():
    """
    Critical Test:
    1. Generator produces invalid Mermaid syntax (forbidden `|>`).
    2. LLM Reviewer misses it completely (Returns 1.0 confidence, no errors).
    3. CLAIM: The Deterministic Linter must catch it, append the error, and FORCE the Repairer to run.
    """
    provider = HybridMockProvider()
    pipeline = DirectPipeline(provider)
    
    # Run
    result = await pipeline.run(
        input_path="dummy.md", 
        input_text_full="Short.", 
        instruction_config=InstructionConfig(), 
        generation_config=GenerationConfig(),
        status_callback=AsyncMock()
    )
    
    # 1. Verify Repairer was called
    # Sequence: FlexDoc (Gen) -> DeciderResponse? -> ReviewReport (Rev) -> RepairResult (Rep)
    # Note: Decider might be skipped or called depending on config/implementation details. 
    # In my pipeline implementation, Decider is called if config.fast_mode is false.
    # We used default config, so fast_mode is false.
    
    # Check if 'RepairResult' is in the call log
    print(f"Call Log: {provider.call_log}")
    assert "RepairResult" in provider.call_log, "Repairer should have been triggered by Linter!"

    # 2. Verify the document was actually repaired
    assert "-->|Label| B" in result.final_doc.content
    assert "|>" not in result.final_doc.content

    # 3. Verify the Review Report actually contains the Linter error
    report = result.final_doc.review_report
    assert report is not None
    assert len(report.mermaid_errors) > 0
    assert "[AUTO-LINTER]" in report.mermaid_errors[0].issue
    assert report.confidence_score == 0.0 # Should have been smashed to 0.0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
