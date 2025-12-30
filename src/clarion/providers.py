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
            options["num_predict"] = config.num_predict
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
                if hasattr(schema, "model_fields") and "content" in schema.model_fields:
                    print(f"JSON strict validation failed after retry. Using raw text fallback for robust content generation.")
                    # Heuristic: treat the entire raw response as the content
                    # Clean up any markdown blocks if present
                    safe_content = response_text
                    if safe_content.startswith("```json"): safe_content = safe_content[7:]
                    elif safe_content.startswith("```"): safe_content = safe_content[3:]
                    if safe_content.endswith("```"): safe_content = safe_content[:-3]
                    
                    # Create valid instance manually
                    # Try to construct it with just content.
                    try:
                        return schema(content=safe_content.strip())
                    except Exception as fallback_e:
                        print(f"Fallback construction failed: {fallback_e}")
                        pass # Raise original error
                
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
        timeout = httpx.Timeout(120.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            max_retries = 5
            base_delay = 2.0
            
            for attempt in range(max_retries):
                try:
                    resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                    
                    if resp.status_code == 429 or resp.status_code == 503:
                        msg = resp.json().get("error", "Too Many Requests") if resp.status_code == 429 else "Service Unavailable"
                        delay = base_delay * (2 ** attempt)
                        print(f"Server busy ({resp.status_code}: {msg}). Retrying in {delay}s...")
                        import asyncio
                        await asyncio.sleep(delay)
                        continue
                        
                    if resp.status_code == 404:
                        # Fallback to generate if chat not found (shouldn't happen for standard ollama)
                        resp.raise_for_status()
                        
                    resp.raise_for_status()
                    data = resp.json()
                    return data["message"]["content"]
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [429, 503]:
                        # Pass through to retry logic if raise_for_status triggered it
                        delay = base_delay * (2 ** attempt)
                        print(f"HTTP {e.response.status_code}. Retrying in {delay}s...")
                        import asyncio
                        await asyncio.sleep(delay)
                        continue
                    raise e
                except (httpx.ConnectError, httpx.ReadTimeout) as e:
                     # Also retry on connection errors/timeouts? Maybe safer.
                     print(f"Network error: {e}. Retrying...")
                     delay = base_delay * (2 ** attempt)
                     import asyncio
                     await asyncio.sleep(delay)
                     continue
            
            raise Exception("Max retries exceeded for LLM API call.")
            
    def _parse_and_validate(self, content: str, schema: Type[T]) -> T:
        # Clean content if needed 
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        try:
            # strict=False allows control characters like newlines in strings
            obj = json.loads(cleaned, strict=False)
        except json.JSONDecodeError as e:
            # Recover from "Extra data" (e.g. JSON + explanation)
            if e.msg.startswith("Extra data"):
                try:
                    # Find the LAST '}' to truncate trailing garbage
                    last_brace = cleaned.rfind('}')
                    if last_brace != -1:
                        truncated = cleaned[:last_brace+1]
                        obj = json.loads(truncated, strict=False)
                    else:
                        raise e
                except Exception:
                    raise e
            else:
                # Recover from "Invalid control character" or other issues by brute force finding the largest JSON block
                import re
                try:
                    # Naive regex to find the largest outer brace pair
                    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                    if match:
                        obj = json.loads(match.group(0), strict=False)
                    else:
                        raise e
                except Exception:
                    raise e
                    
        return schema.model_validate(obj)
