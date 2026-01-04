import pytest
import json
from unittest.mock import AsyncMock, patch
from clarion.providers import OllamaProvider
from clarion.schemas import FlexDoc

@pytest.mark.asyncio
async def test_repair_mechanism_triggers_on_bad_json():
    provider = OllamaProvider(model_name="test-model")
    
    # Mock _call_api to return bad JSON first, then good JSON
    with patch.object(provider, '_call_api', new_callable=AsyncMock) as mock_call:
        mock_call.side_effect = [
            "This is not JSON", 
            '{"thought_process": "fixed", "content": "Repaired content"}'
        ]
        
        status_msgs = []
        async def mock_callback(msg): status_msgs.append(msg)
        
        result = await provider.generate_json("test prompt", FlexDoc, status_callback=mock_callback)
        
        assert result.content == "Repaired content"
        assert any("Clarion Repair" in m for m in status_msgs)
        assert mock_call.call_count == 2

@pytest.mark.asyncio
async def test_fallback_content_extraction():
    provider = OllamaProvider(model_name="test-model")
    
    # Mock _call_api to return something that NEVER validates as JSON even after repair
    with patch.object(provider, '_call_api', new_callable=AsyncMock) as mock_call:
        # After 2 attempts of JSON failure, it tries "smart extraction" or raw fallback
        mock_call.return_value = "```markdown\n# Raw Content\nThis is raw text fallback.\n```"
        
        result = await provider.generate_json("test prompt", FlexDoc)
        
        # FlexDoc fallback should extract content from raw text
        assert "# Raw Content" in result.content
        assert "This is raw text fallback" in result.content

@pytest.mark.asyncio
async def test_normalization_remaps_keys():
    provider = OllamaProvider(model_name="test-model")
    
    # Model returns 'text' instead of 'content'
    raw_json = '{"thoughts": "my thoughts", "text": "mapped content"}'
    
    with patch.object(provider, '_call_api', new_callable=AsyncMock) as mock_call:
        mock_call.return_value = raw_json
        
        result = await provider.generate_json("test prompt", FlexDoc)
        
        assert result.thought_process == "my thoughts"
        assert result.content == "mapped content"
