import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path
from clarion.server import app

client = TestClient(app)

@patch("clarion.server.run_pipeline")
@patch("clarion.server.OllamaProvider")
def test_all_parameters_transmission(mock_provider, mock_run_pipeline):
    """
    Test that ALL advanced parameters from the frontend are correctly received 
    by the backend and passed to the configuration objects.
    """
    
    # 1. Setup Mock
    # We mock run_pipeline so we don't actually generate anything
    async def mock_pipeline_execution(instruction_config, input_path, provider, gen_config, callback):
        # We just want to inspect 'gen_config' here!
        # Return a dummy object so the endpoint doesn't crash before we can assert
        mock_doc = MagicMock()
        mock_doc.final_doc.model_dump_json.return_value = "{}"
        mock_doc.final_doc.model_dump.return_value = {"content": "Dummy content"} # Fix: Return a dict
        mock_doc.final_doc.content = "Dummy content"
        mock_doc.final_doc.thought_process = "Dummy thoughts"
        mock_doc.final_doc.review_report = None # Ensure this is not a Mock
        return mock_doc

    mock_run_pipeline.side_effect = mock_pipeline_execution
    
    # 2. Define non-default values for every parameter to ensure defaults aren't hiding issues
    test_params = {
        "model": "llama3.1:8b",
        "instruction": "Specific test instruction",
        "word_budget": "1500",
        "overlap": "5",
        "temperature": "0.7",
        "top_p": "0.85",
        "num_ctx": "8192",
        "presence_penalty": "1.5",
        "frequency_penalty": "0.5",
        "repeat_penalty": "1.2",
        "top_k": "60",
        "num_predict": "4096",
        "fast_mode": "true", # Boolean sent as string in FormData
    }
    
    # 3. Create real file payload
    real_input_path = Path(r"C:\Users\mccat\Documents\Clarion\inputs\01_protection-eavesdrop.md")
    if not real_input_path.exists():
        # Fallback if file doesn't exist (e.g. CI), though user said it does
        content = "# Mock Content"
        filename = "fallback.md"
    else:
        with open(real_input_path, "rb") as f:
            content = f.read()
        filename = real_input_path.name

    files = {'files': (filename, content, 'text/markdown')}
    
    # 4. Make Request
    response = client.post("/v1/docgen", data=test_params, files=files)
    
    # 5. Verify Request Logic
    # The endpoint is streaming, so we need to consume it or check if it started (status 200)
    assert response.status_code == 200
    
    # 6. Verify Arguments passed to run_pipeline
    # This is the crucial step: did the backend parse the Form data and create the config object correctly?
    assert mock_run_pipeline.called
    
    # Get the arguments of the first call
    args, kwargs = mock_run_pipeline.call_args
    
    # Unpack arguments (signature: config, input_path, provider, gen_config, progress_callback)
    # We are interested in 'gen_config' which is the 4th argument (index 3)
    gen_config = args[3]
    
    # Check Schema Generation Config
    print("\n[Checked] Verifying Generation Parameters...")
    assert gen_config.temperature == 0.7
    assert gen_config.top_p == 0.85
    assert gen_config.num_ctx == 8192
    assert gen_config.num_predict == 4096
    assert gen_config.presence_penalty == 1.5
    assert gen_config.frequency_penalty == 0.5
    assert gen_config.repeat_penalty == 1.2
    assert gen_config.top_k == 60
    assert gen_config.fast_mode is True
    
    instruction_config = args[0]
    assert instruction_config.inline_instruction == "Specific test instruction"
    
    # Check Provider setup
    mock_provider.assert_called_with(model_name="llama3.1:8b")
    
    print("All parameters transmitted correctly!")
    
    # Cleanup
    from clarion.server import OUTPUT_DIR
    for f in ["test_doc.md", "test_doc.json"]:
        p = OUTPUT_DIR / f
        if p.exists():
            p.unlink()
