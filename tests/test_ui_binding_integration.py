import pytest
from fastapi.testclient import TestClient
from clarion.server import app
from unittest.mock import patch, AsyncMock
from clarion.schemas import DocResult, FlexDoc

@pytest.fixture
def client():
    return TestClient(app)

@patch("clarion.services.doc_service.run_pipeline", new_callable=AsyncMock)
def test_ui_binding_gap_replication(mock_run, client):
    # This test replicates the EXACT payload sent by App.tsx handleGenerate()
    # derived from static analysis of the frontend code.
    
    file_content = b"Content"
    filename = "test.md"
    
    mock_run.return_value = DocResult(
        input_file=filename,
        final_doc=FlexDoc(content="Done"),
        manifest_path=""
    )
    
    # Payload mimicking FIXED App.tsx
    data = {
        "model": "llama3",
        "word_budget": "2000",
        "overlap": "2",
        "temperature": "0.7",
        "top_p": "0.9",
        "top_k": "40",
        "repeat_penalty": "1.1",
        "presence_penalty": "0.0",
        "frequency_penalty": "0.0",
        "num_ctx": "8192",
        "num_predict": "2048",
        "fast_mode": "false",
        "use_rag": "true",
        # New bindings
        "rag_k": "10",
        "chunk_size": "2500",
        "chunk_overlap": "300"
    }
    
    files = [("files", (filename, file_content, "text/markdown"))]
    
    # Execute Request
    with client.stream("POST", "/v1/docgen", data=data, files=files) as response:
        assert response.status_code == 200
        for _ in response.iter_lines(): pass
        
    # Validation
    assert mock_run.called
    args, kwargs = mock_run.call_args
    gen_config = kwargs.get("generation_config") or args[3]
    
    # Assert that params are now correctly passed
    print(f"captured chunk_size: {gen_config.chunk_size}")
    assert gen_config.chunk_size == 2500
    assert gen_config.chunk_overlap == 300
    assert gen_config.rag_k == 10
