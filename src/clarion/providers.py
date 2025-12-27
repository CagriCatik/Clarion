import json
import httpx
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Any, List, Optional
from pydantic import BaseModel, ValidationError

# Use string forward reference to avoid circular import if necessary, 
# but import if possible. 
from clarion.schemas import GenerationConfig
from clarion.prompt_loader import render_prompt

T = TypeVar("T", bound=BaseModel)

class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, schema: Type[T], config: Optional[GenerationConfig] = None) -> T:
        pass

    async def list_models(self) -> List[str]:
        return []

class OllamaProvider(LLMProvider):
    def __init__(self, model_name: str = "llama3.1", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    async def generate_json(self, prompt: str, schema: Type[T], config: Optional[GenerationConfig] = None) -> T:
        """
        Generates a JSON response matching the schema.
        """
        schema_json = json.dumps(schema.model_json_schema())
        
        pydantic_prompt = render_prompt(
            "json_enforcement.j2",
            prompt=prompt,
            schema_json=schema_json
        )
        
        # Merge defaults
        options = {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_ctx": 4096
        }
        if config:
            options["temperature"] = config.temperature
            options["top_p"] = config.top_p
            options["num_ctx"] = config.num_ctx
            options["presence_penalty"] = config.presence_penalty
            options["frequency_penalty"] = config.frequency_penalty
            options["repeat_penalty"] = config.repeat_penalty
            options["top_k"] = config.top_k
            
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": pydantic_prompt}],
            "stream": False,
            "format": "json",
            "options": options
        }
        
        try:
            response = await self._call_api(payload)
            return self._parse_and_validate(response, schema)
        except (ValidationError, json.JSONDecodeError) as e:
            # Retry logic
            print(f"JSON validation failed: {e}. Retrying with repair prompt.")
            
            repair_prompt = render_prompt("repair.j2", error=str(e))
            
            payload["messages"].append({"role": "user", "content": repair_prompt})
            
            # Second attempt
            response_text = await self._call_api(payload)
            try:
                return self._parse_and_validate(response_text, schema)
            except Exception as final_e:
                # Fallback: If we just want content (FlexDoc), and the model gave us text, use it.
                # This is a specific fallback for FlexDoc-like schemas that have a 'content' field.
                if hasattr(schema, "model_fields") and "content" in schema.model_fields and len(schema.model_fields) == 1:
                    print(f"JSON strict validation failed after retry. Using raw text fallback for robust content generation.")
                    # Heuristic: treat the entire raw response as the content
                    # Clean up any markdown blocks if present
                    safe_content = response_text
                    if safe_content.startswith("```json"): safe_content = safe_content[7:]
                    elif safe_content.startswith("```"): safe_content = safe_content[3:]
                    if safe_content.endswith("```"): safe_content = safe_content[:-3]
                    
                    # Create valid instance manually
                    fallback_json = {"content": safe_content.strip()}
                    return schema.model_validate(fallback_json)
                
                print(f"Retry failed: {final_e}. Checking for fallback candidates...")
                raise final_e
            
    async def list_models(self) -> List[str]:
        """
        Lists available models from Ollama.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
            except Exception as e:
                print(f"Failed to list models: {e}")
                return []

    async def _call_api(self, payload: dict) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            if resp.status_code == 404:
                # Fallback to generate if chat not found (shouldn't happen for standard ollama)
                resp.raise_for_status()
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
            
    def _parse_and_validate(self, content: str, schema: Type[T]) -> T:
        # Clean content if needed 
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        obj = json.loads(cleaned)
        return schema.model_validate(obj)
