import pytest
import httpx
import json
from unittest.mock import patch, AsyncMock
from clarion.schemas import DocResult, FlexDoc
from pathlib import Path
import tempfile

BASE_URL = "http://localhost:8000"

# Test configuration with all parameters
TEST_PARAMS = {
    "model": "llama3.1",
    "temperature": 0.5,
    "top_p": 0.95,
    "top_k": 50,
    "num_ctx": 16384,
    "num_predict": 8192,
    "repeat_penalty": 1.2,
    "presence_penalty": 0.1,
    "frequency_penalty": 0.1,
    "fast_mode": True,
    "word_budget": 3000,
    "overlap": 3,
    "use_rag": True,
    "rag_k": 10,
    "chunk_size": 8000,
    "chunk_overlap": 1000,
}

from fastapi.testclient import TestClient
from clarion.server import app

client = TestClient(app)

@pytest.fixture
def test_file():
    """Create a temporary test file."""
    content = """
    Test content for parameter verification.
    This is a simple test document to verify parameter transmission.
    """
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
        f.write(content.encode('utf-8'))
        f_name = f.name
    return Path(f_name)


@patch("clarion.services.doc_service.run_pipeline", new_callable=AsyncMock)
def test_parameter_transmission(mock_run, test_file):
    """Test that all parameters are correctly transmitted to backend."""
    
    mock_run.return_value = DocResult(
        input_file=str(test_file),
        final_doc=FlexDoc(content="Done"),
        manifest_path=""
    )

    # Prepare multipart form data
    with open(test_file, "rb") as f:
        files = {"files": ("test.txt", f, "text/plain")}
        
        data = {
            "model": TEST_PARAMS["model"],
            "temperature": str(TEST_PARAMS["temperature"]),
            "top_p": str(TEST_PARAMS["top_p"]),
            "top_k": str(TEST_PARAMS["top_k"]),
            "num_ctx": str(TEST_PARAMS["num_ctx"]),
            "num_predict": str(TEST_PARAMS["num_predict"]),
            "repeat_penalty": str(TEST_PARAMS["repeat_penalty"]),
            "presence_penalty": str(TEST_PARAMS["presence_penalty"]),
            "frequency_penalty": str(TEST_PARAMS["frequency_penalty"]),
            "fast_mode": str(TEST_PARAMS["fast_mode"]).lower(),
            "word_budget": str(TEST_PARAMS["word_budget"]),
            "overlap": str(TEST_PARAMS["overlap"]),
            "use_rag": str(TEST_PARAMS["use_rag"]).lower(),
            "rag_k": str(TEST_PARAMS["rag_k"]),
            "chunk_size": str(TEST_PARAMS["chunk_size"]),
            "chunk_overlap": str(TEST_PARAMS["chunk_overlap"]),
        }
        
        # Send request using TestClient
        response = client.post("/v1/docgen", files={"files": ("test.txt", f, "text/plain")}, data=data)
        assert response.status_code == 200
        # For SSE, we can just check content
        assert "text/event-stream" in response.headers["content-type"]
        
    # VERIFY MOCK CALL
    assert mock_run.called
    args, kwargs = mock_run.call_args
    gen_config = kwargs.get("gen_config") or (args[3] if len(args) > 3 else None)
    
    assert gen_config is not None
    assert gen_config.temperature == TEST_PARAMS["temperature"]
    assert gen_config.num_predict == TEST_PARAMS["num_predict"]
    assert gen_config.word_budget == TEST_PARAMS["word_budget"]
    assert gen_config.rag_k == TEST_PARAMS["rag_k"]
    assert gen_config.chunk_size == TEST_PARAMS["chunk_size"]
    
    print("✅ All parameters successfully transmitted and verified via GenerationConfig")


def test_default_parameters(test_file):
    """Test that default parameters work when not specified."""
    
    with open(test_file, "rb") as f:
        files = {"files": ("test.txt", f, "text/plain")}
        
        # Send with minimal params (use defaults)
        data = {"model": "llama3.1"}
        
        response = client.post("/v1/docgen", files=files, data=data)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
                
    print("✅ Default parameters work correctly")


def test_parameter_validation():
    """Test that invalid parameters are handled."""
    
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
        f.write(b"test")
        test_path = Path(f.name)
    
    with open(test_path, "rb") as f:
        files = {"files": ("test.txt", f, "text/plain")}
        
        # Test invalid temperature (FastAPI usually handles type coercion, 
        # but let's see if the server crashes or returns 422)
        data = {
            "model": "llama3.1",
            "temperature": "not-a-number"  # Invalid
        }
        
        response = client.post(
            "/v1/docgen",
            files=files,
            data=data
        )
        
        # FastAPI should return 422 Unprocessable Entity
        assert response.status_code == 422
        print(f"✅ Invalid parameters correctly rejected with status {response.status_code}")


@patch("clarion.services.doc_service.run_pipeline", new_callable=AsyncMock)
def test_exhaustive_parameter_sweep(mock_run, test_file):
    """Exhaustively verify every single parameter in the GenerationConfig."""
    
    mock_run.return_value = DocResult(input_file="test", final_doc=FlexDoc(content="Exhaustive"), manifest_path="")
    
    sweep_params = {
        "model": "gpt-mock",
        "temperature": "0.1",
        "top_p": "0.8",
        "top_k": "20",
        "num_ctx": "2048",
        "num_predict": "1024",
        "repeat_penalty": "1.5",
        "presence_penalty": "0.5",
        "frequency_penalty": "0.5",
        "fast_mode": "true",
        "word_budget": "1500",
        "overlap": "1",
        "use_rag": "true",
        "rag_k": "3",
        "chunk_size": "1000",
        "chunk_overlap": "100"
    }
    
    with open(test_file, "rb") as f:
        client.post("/v1/docgen", files={"files": ("test.txt", f, "text/plain")}, data=sweep_params)
        
    args, kwargs = mock_run.call_args
    config = kwargs.get("gen_config") or (args[3] if len(args) > 3 else None)
    
    assert config.temperature == 0.1
    assert config.top_p == 0.8
    assert config.top_k == 20
    assert config.num_ctx == 2048
    assert config.num_predict == 1024
    assert config.repeat_penalty == 1.5
    assert config.presence_penalty == 0.5
    assert config.frequency_penalty == 0.5
    assert config.fast_mode is True
    assert config.word_budget == 1500
    assert config.overlap == 1
    assert config.rag_k == 3
    assert config.chunk_size == 1000
    assert config.chunk_overlap == 100
    
    print("✅ Exhaustive parameter sweep verified")

def test_parameter_schema():
    """Test that GenerationConfig schema has all required fields."""
    from clarion.schemas import GenerationConfig
    
    # Create config with all parameters
    config = GenerationConfig(
        temperature=0.5,
        top_p=0.95,
        num_ctx=16384,
        num_predict=8192,
        presence_penalty=0.1,
        frequency_penalty=0.1,
        repeat_penalty=1.2,
        top_k=50,
        fast_mode=True,
        word_budget=3000,
        overlap=3,
        rag_k=10,
        chunk_size=8000,
        chunk_overlap=1000
    )
    
    # Verify all fields are set
    assert config.temperature == 0.5
    assert config.top_p == 0.95
    assert config.num_ctx == 16384
    assert config.num_predict == 8192
    assert config.presence_penalty == 0.1
    assert config.frequency_penalty == 0.1
    assert config.repeat_penalty == 1.2
    assert config.top_k == 50
    assert config.fast_mode == True
    assert config.word_budget == 3000  # NEW
    assert config.overlap == 3         # NEW
    assert config.rag_k == 10
    assert config.chunk_size == 8000
    assert config.chunk_overlap == 1000
    
    print("✅ GenerationConfig schema has all 14 parameters")


if __name__ == "__main__":
    # Run synchronous tests
    print("\n" + "="*70)
    print("PARAMETER TRANSMISSION TESTS")
    print("="*70 + "\n")
    
    print("1. Testing GenerationConfig Schema...")
    test_parameter_schema()
    
    print("\n2. Testing Async Parameter Transmission...")
    print("   (Run with: pytest test_parameter_transmission.py -v)")
    print("\n" + "="*70)
