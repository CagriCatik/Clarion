import pytest
import asyncio
from typing import Type, TypeVar, Optional, Callable
from pydantic import BaseModel
from clarion.providers import LLMProvider
from clarion.schemas import GenerationConfig, FlexDoc

T = TypeVar("T", bound=BaseModel)

class MockLLMProvider(LLMProvider):
    def __init__(self, model_name: str = "mock-model"):
        self.responses = []
        self.calls = []
        self.model_name = model_name

    def add_response(self, obj: BaseModel):
        self.responses.append(obj)

    async def generate_json(self, prompt: str, schema: Type[T], config: Optional[GenerationConfig] = None, status_callback: Optional[Callable] = None) -> T:
        self.calls.append({"prompt": prompt, "schema": schema, "config": config})
        if self.responses:
            return self.responses.pop(0)
        # Default fallback
        if schema == FlexDoc:
            return FlexDoc(thought_process="Mock thought", content="Mock content")
        return schema()

    async def list_models(self):
        return ["mock-model-1", "mock-model-2"]

@pytest.fixture
def mock_provider():
    return MockLLMProvider()

@pytest.fixture
def sample_markdown():
    return """# Sample Document
This is a sample markdown file for testing Clarion.
## Section 1
Content of section 1.
"""

@pytest.fixture
def large_markdown():
    # Generate ~10k tokens (40k chars)
    return ("# Large Document\n" + "This is a repetitive line to increase file size for windowed testing.\n" * 500)
