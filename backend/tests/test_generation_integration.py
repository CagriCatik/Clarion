import pytest
from fastapi.testclient import TestClient
from clarion.server import app
import os
import json
import httpx
from unittest.mock import patch

# Create TestClient
client = TestClient(app)

def is_ollama_running(base_url="http://localhost:11434"):
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False

@patch("clarion.server.run_pipeline")
def test_docgen_integration(mock_run_pipeline):
    """
    Integration test that mocks the pipeline execution to verify
    data transmission and SSE streaming structure without needing a live LLM.
    """
    from clarion.schemas import DocResult, FlexDoc
    from unittest.mock import MagicMock
    
    # Mock the return value of run_pipeline
    async def side_effect(config, input_path, provider, generation_config, status_callback):
        # Simulate some progress
        if status_callback:
            await status_callback("Mocking progress 1...")
            await status_callback("Mocking progress 2...")
            
        # Return a dummy DocResult
        return DocResult(
            input_file="test_input.md",
            final_doc=FlexDoc(
                content="# Generated Test Doc\n\nMocked content.",
                thought_process="Mock thoughts"
            ),
            manifest_path=""
        )
        
    mock_run_pipeline.side_effect = side_effect

    # 1. Prepare dummy input file
    file_content = """
# Test Document

This is a small test document to verify the generation pipeline.
It contains some basic text and a list:
- Item 1
- Item 2
    """
    
    files = {
        'files': ('test_input.md', file_content, 'text/markdown')
    }
    
    # 2. Prepare Form Data
    data = {
        "model": "mock-model",
        "instruction": "Summarize this document.",
        "word_budget": 500,
        "temperature": 0.1,
        "fast_mode": True
    }
    
    # 3. Call the endpoint
    # We use stream=True to handle the StreamingResponse
    print("\n[Test] Sending request to /v1/docgen...")
    with client.stream("POST", "/v1/docgen", files=files, data=data) as response:
        assert response.status_code == 200
        
        status_events = []
        result_event = None
        error_event = None
        
        # 4. Consume the SSE stream
        for line in response.iter_lines():
            if not line:
                continue
            
            # Parse data: lines with JSON
            if line.startswith("data: "):
                content = line[6:].strip()
                
                try:
                    json_data = json.loads(content)
                    
                    # Check for result (now sent individually)
                    if 'result' in json_data:
                        print(f"[Test] Received result payload")
                        result_event = json_data['result']
                    
                    # Check for status updates
                    if 'status' in json_data:
                        status_events.append(json_data['status'])
                        
                    # Check for completion
                    if json_data.get('complete'):
                        print("[Test] Stream complete.")
                        
                except json.JSONDecodeError:
                    # Not JSON, skip
                    pass

        # 5. Assertions
        
        # Verify we got some status updates
        assert len(status_events) > 0, "Should have received status updates"
        
        # Verify we got a result
        assert result_event is not None, "Should have received a final result event"
        
        doc = result_event
        assert doc.get("filename") or doc.get("saved_to"), "Result should have filename or saved_to"
        assert "markdown" in doc
        
        generated_md = doc.get("markdown", "")
        if len(generated_md) <= 10:
            print(f"\n[FAILURE DEBUG] status_events: {status_events}")
            print(f"[FAILURE DEBUG] result_event: {result_event}")
            print(f"[FAILURE DEBUG] doc content: '{generated_md}'")
            
        assert len(generated_md) > 10, f"Generated markdown should not be empty. Received: '{generated_md}'"
        
        print("\n[Test] Generated Markdown Preview:")
        print(generated_md[:200] + "...")
        
        # Verify it saved to disk
        if "saved_to" in doc:
            assert os.path.exists(doc["saved_to"])
        
        # Cleanup generated file
        try:
            os.remove(doc["saved_to"])
            json_path = doc["saved_to"].replace(".md", ".json")
            if os.path.exists(json_path):
                os.remove(json_path)
        except Exception as e:
            print(f"Warning: Failed to cleanup test output files: {e}")

if __name__ == "__main__":
    # Allow running this file directly
    import sys
    sys.exit(pytest.main(["-v", __file__]))
