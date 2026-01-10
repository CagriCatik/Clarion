
import sys
import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

# --- PATH SETUP ---
# Ensure 'backend' is in sys.path so 'clarion' package can be imported
current_file = Path(__file__)
project_root = current_file.parent.parent.parent # backend/tests -> backend -> Clarion
backend_path = project_root / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import the app
from clarion.server import app, OUTPUT_DIR
from clarion import server as server_module # To patch objects

client = TestClient(app)

# --- TESTS ---

def test_health_check():
    """Verify basic API health."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_list_models(monkeypatch):
    """Test fetching model list from Ollama provider."""
    # Mock OllamaProvider.list_models
    mock_list = AsyncMock(return_value=["model-a", "model-b"])
    
    # We need to patch the Class method, but providers is imported inside list_models usually?
    # No, it's imported at top level in server.py usually, or instanced.
    # checking server.py: 
    # @app.get("/v1/models") uses: provider = OllamaProvider(); await provider.list_models()
    
    from clarion.providers import OllamaProvider
    monkeypatch.setattr(OllamaProvider, "list_models", mock_list)
    
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert response.json() == {"models": ["model-a", "model-b"]}

def test_metrics():
    """Test system metrics endpoint."""
    response = client.get("/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "ram" in data
    assert "gpu" in data # can be null

def test_docgen_full_transmission(monkeypatch):
    """
    Comprehensive test of the /v1/docgen endpoint.
    Verifies:
    1. Transmission of all parameters (including new multi-model ones).
    2. Correct parsing of FormData.
    3. Response streaming format (SSE).
    4. Inclusion of ReviewReport in the result.
    """
    
    # Mocks
    mock_run_pipeline = AsyncMock()
    
    # Create a dummy DocResult with a ReviewReport to verify transmission back to UI
    from clarion.schemas import DocResult, FlexDoc, ReviewReport, TextIssue, MermaidError
    
    # Dynamic Side Effect
    async def mock_run_implementation(config, input_path, provider, gen_config, status_callback):
        # Infer filename from path
        fname = Path(input_path).name
        return DocResult(
            input_file=input_path,
            final_doc=FlexDoc(
                content=f"# Generated Documentation for {fname}\n\nThis is a mock generation based on the real input context.",
                review_report=ReviewReport(
                    confidence_score=0.85,
                    text_issues=[
                        TextIssue(location="L10", issue="Typo", suggested_fix="Fix it")
                    ],
                    mermaid_errors=[]
                )
            ),
            manifest_path="manifest.json"
        )
            
    mock_run_pipeline.side_effect = mock_run_implementation
    
    # Patch run_pipeline in server module
    monkeypatch.setattr(server_module, "run_pipeline", mock_run_pipeline)
    
    # Patch OllamaProvider to avoid real network calls during init
    from clarion.providers import OllamaProvider
    monkeypatch.setattr(OllamaProvider, "__init__", lambda self, model_name="x", base_url=None: None)

    # Payload
    # Payload
    real_input_path = Path(r"C:\Users\mccat\Documents\Clarion\inputs\01_protection-eavesdrop.md")
    if real_input_path.exists():
        with open(real_input_path, "rb") as f:
            file_bytes = f.read()
        filename = real_input_path.name
    else:
        file_bytes = b'# Test Input'
        filename = 'test_input.md'

    files = [
        ('files', (filename, file_bytes, 'text/markdown'))
    ]
    
    data = {
        "model": "main-model",
        "instruction": "Do it well",
        "word_budget": "2000",
        "overlap": "2",
        "temperature": "0.7",
        "top_p": "0.9",
        "num_ctx": "4096",
        "num_predict": "1000",
        "presence_penalty": "0.5",
        "frequency_penalty": "0.6",
        "repeat_penalty": "1.2",
        "top_k": "50",
        "fast_mode": "false",
        
        # New Params
        "generator_model": "draft-agent",
        "reviewer_model": "audit-agent",
        "interactive_review": "true"
    }
    
    # Execute Request
    response = client.post("/v1/docgen", files=files, data=data)
    assert response.status_code == 200
    
    # Capture Stream Content
    # The endpoint returns a StreamingResponse. TestClient follows it.
    # We parse the SSE lines.
    stream_content = response.content.decode("utf-8")
    lines = stream_content.split("\n\n")
    
    # 1. Verify Pipeline Call Arguments
    call_args = mock_run_pipeline.call_args
    assert call_args is not None
    
    # run_pipeline(config, input_path_str, provider, gen_config, callback)
    # Check GenConfig
    args, _ = call_args
    gen_config = args[3] # 4th argument
    
    assert gen_config.temperature == 0.7
    assert gen_config.generator_model == "draft-agent"
    assert gen_config.reviewer_model == "audit-agent"
    assert gen_config.interactive_review is True
    
    # 2. Verify Output Transmission
    # Look for the JSON result lines
    result_found = False
    report_verified = False
    
    for line in lines:
        if line.startswith("data: "):
            json_str = line[6:]
            if not json_str.strip(): continue
            try:
                payload = json.loads(json_str)
                if "result" in payload:
                    result_found = True
                    res = payload["result"]
                    # Check if review_report is present in the transmitted JSON
                    if "review_report" in res and res["review_report"] is not None:
                        rpt = res["review_report"]
                        if rpt["confidence_score"] == 0.85 and len(rpt["text_issues"]) == 1:
                            report_verified = True
            except json.JSONDecodeError:
                pass

    assert result_found, "No result JSON found in stream"
    assert report_verified, "ReviewReport was not correctly transmitted in the JSON result"

def test_outputs_crud():
    """Test listing, getting, and deleting outputs."""
    # Create a dummy output file
    test_filename = "test_transmission_doc.md"
    test_path = OUTPUT_DIR / test_filename
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(test_path, "w") as f:
        f.write("# Generated Doc")
        
    try:
        # List
        res = client.get("/v1/outputs")
        assert res.status_code == 200
        assert test_filename in res.json()["outputs"]
        
        # Get
        res = client.get(f"/v1/outputs/{test_filename}")
        assert res.status_code == 200
        assert res.json()["markdown"] == "# Generated Doc"
        
        # Delete
        res = client.delete(f"/v1/outputs/{test_filename}")
        assert res.status_code == 200
        assert not test_path.exists()
        
    finally:
        # Cleanup if test failed
        if test_path.exists():
            test_path.unlink()
