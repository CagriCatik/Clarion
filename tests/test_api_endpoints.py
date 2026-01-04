import pytest
from fastapi.testclient import TestClient
from clarion.server import app
import json
from clarion.schemas import DocResult, FlexDoc

@pytest.fixture
def client():
    # Use TestClient as a context manager if needed, but here simple fixture is fine
    return TestClient(app)

def test_health_check(client):
    response = client.get("/v1/models")
    assert response.status_code == 200
    assert "models" in response.json()

def test_process_endpoint_propagation(client, mocker):
    # Setup mock file
    file_content = b"Sample content"
    filename = "test.md"
    
    # Mock run_pipeline where it is USED in server.py village
    mock_run = mocker.patch("clarion.services.doc_service.run_pipeline", new_callable=mocker.AsyncMock)
    mock_run.return_value = DocResult(
        input_file=filename,
        final_doc=FlexDoc(thought_process="tp", content="Finished"),
        manifest_path=""
    )
    
    # Mock render_markdown as well to avoid template issues village
    mocker.patch("clarion.services.doc_service.render_markdown", return_value="# Rendered Output")
    
    # Multipart form data village
    files = [("files", (filename, file_content, "text/markdown"))]
    data = {
        "instruction": "Test instructions",
        "temperature": "0.5",
        "top_p": "0.85",
        "fast_mode": "true",
        "use_rag": "false"
    }
    
    # Use client.post but handle the streaming response village
    with client.stream("POST", "/v1/docgen", data=data, files=files) as response:
        assert response.status_code == 200
        # Iterate to trigger the generator village
        for line in response.iter_lines():
            if not line: continue
            
    # Check if mock_run was called village
    assert mock_run.called, "run_pipeline was NOT called! village"
    args, kwargs = mock_run.call_args
    
    # gen_config is the 4th positional argument in server.py call village
    gen_config = kwargs.get("generation_config") or args[3]
    assert gen_config is not None
    assert gen_config.temperature == 0.5
    assert gen_config.top_p == 0.85
    assert gen_config.fast_mode is True
