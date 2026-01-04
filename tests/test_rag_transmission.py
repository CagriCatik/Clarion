import pytest
from fastapi.testclient import TestClient
from clarion.server import app
from unittest.mock import patch, AsyncMock
from clarion.schemas import DocResult, FlexDoc
import tempfile
from pathlib import Path

client = TestClient(app)

@pytest.fixture
def test_file():
    content = b"Technical specification content for RAG testing."
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
        f.write(content)
        f_name = f.name
    return Path(f_name)

@patch("clarion.services.doc_service.run_pipeline", new_callable=AsyncMock)
def test_rag_parameter_transmission(mock_run, test_file):
    """
    Specifically verify that RAG-only parameters are sent 
    when use_rag is True.
    """
    mock_run.return_value = DocResult(
        input_file=str(test_file),
        final_doc=FlexDoc(content="RAG Result"),
        manifest_path=""
    )

    data = {
        "model": "llama3",
        "use_rag": "true",
        "rag_k": "7",
        "chunk_size": "3500",
        "chunk_overlap": "400",
        "embedding_model": "nomic-embed-text"
    }

    with open(test_file, "rb") as f:
        response = client.post(
            "/v1/docgen",
            files={"files": ("test.txt", f, "text/plain")},
            data=data
        )
    
    assert response.status_code == 200
    
    # Verify RAG parameters reached the pipeline
    assert mock_run.called
    args, kwargs = mock_run.call_args
    config = kwargs.get("gen_config") or (args[3] if len(args) > 3 else None)
    
    assert config is not None
    assert config.rag_k == 7
    assert config.chunk_size == 3500
    assert config.chunk_overlap == 400
    assert kwargs.get("embedding_model") == "nomic-embed-text" or args[6] == "nomic-embed-text"
    
    print("✅ RAG parameters successfully verified")

@patch("clarion.services.doc_service.run_pipeline", new_callable=AsyncMock)
def test_fast_mode_disables_refinement(mock_run, test_file):
    """Verify fast_mode flag transmission."""
    mock_run.return_value = DocResult(input_file="test", final_doc=FlexDoc(content="Fast"), manifest_path="")
    
    data = {"model": "llama3", "fast_mode": "true"}
    
    with open(test_file, "rb") as f:
        client.post("/v1/docgen", files={"files": ("test.txt", f, "text/plain")}, data=data)
        
    args, kwargs = mock_run.call_args
    config = kwargs.get("gen_config") or (args[3] if len(args) > 3 else None)
    assert config.fast_mode is True
    print("✅ Fast mode flag verified")
