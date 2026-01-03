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
    def __init__(self, model_name: str = "llama3.1", base_url: Optional[str] = None):
        import os
        self.model_name = model_name
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

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
                    print(f"JSON strict validation failed after retry. Attempting smart content extraction.")
                    
                    # Try to parse it anyway just to get the content field if it exists
                    try:
                        import re
                        cleaned_json = response_text.strip()
                        if "```" in cleaned_json:
                            # Try to find THE LATELY JSON block if multiple exist
                            matches = re.findall(r'```(?:json)?\s*(.*?)\s*```', cleaned_json, re.DOTALL)
                            if matches: cleaned_json = matches[-1].strip()
                        
                        start = cleaned_json.find('{')
                        end = cleaned_json.rfind('}')
                        if start != -1 and end != -1:
                            data = json.loads(cleaned_json[start:end+1], strict=False)
                            if isinstance(data, dict):
                                data = self._normalize_obj(data, schema)
                                if "content" in data:
                                    print("Successfully extracted 'content' field from malformed/invalid JSON response.")
                                    return schema(
                                        thought_process=data.get("thought_process"),
                                        content=str(data["content"])
                                    )
                    except:
                        pass

                    print(f"Extraction failed. Using raw text fallback.")
                    safe_content = response_text
                    if safe_content.startswith("```json"): safe_content = safe_content[7:]
                    elif safe_content.startswith("```"): safe_content = safe_content[3:]
                    if safe_content.endswith("```"): safe_content = safe_content[:-3]
                    
                    safe_content = safe_content.strip()
                    if not safe_content:
                        raise final_e
                        
                    return schema(content=safe_content)
                
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
        # Increase timeout to 20m for large model loading
        timeout = httpx.Timeout(1200.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            max_retries = 5
            base_delay = 2.0
            last_error = None
            
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
                    last_error = e
                    if e.response.status_code == 500:
                        try:
                            err_data = e.response.json()
                            if "error" in err_data:
                                raise Exception(f"Ollama Server Error: {err_data['error']}")
                        except (json.JSONDecodeError, ValueError):
                            pass
                            
                    if e.response.status_code in [429, 503]:
                        # Pass through to retry logic if raise_for_status triggered it
                        delay = base_delay * (2 ** attempt)
                        print(f"HTTP {e.response.status_code}. Retrying in {delay}s...")
                        import asyncio
                        await asyncio.sleep(delay)
                        continue
                    raise e
                except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
                     last_error = e
                     # Also retry on connection errors/timeouts? Maybe safer.
                     print(f"Network error: {e}. Retrying...")
                     delay = base_delay * (2 ** attempt)
                     import asyncio
                     await asyncio.sleep(delay)
                     continue
            
            raise Exception(f"Max retries exceeded for LLM API call. Last error: {last_error}")
            
    def _parse_and_validate(self, content: str, schema: Type[T]) -> T:
        """
        Robustly extract and validate JSON from model output.
        Handles markdown blocks, extra text, and common syntax errors.
        """
        # 1. Strip whitespace
        cleaned = content.strip()
        
        # 2. Remove markdown code blocks if present
        def clean_markdown(text: str) -> str:
            if "```" in text:
                import re
                # Try to find the first JSON-like block
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
                if match:
                    return match.group(1).strip()
            return text
            
        cleaned = clean_markdown(cleaned)
        
        # 3. Find first { and last } to isolate potential JSON
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            potential_json = cleaned[start:end+1]
        else:
            potential_json = cleaned
            
        # 4. Attempt to parse
        try:
            obj = json.loads(potential_json, strict=False)
        except json.JSONDecodeError:
            # 5. Recovery: If it looks like it ended prematurely, try adding missing braces
            # This is common with large model outputs that hit token limits
            try:
                # Count open/close braces
                depth = potential_json.count('{') - potential_json.count('}')
                if depth > 0:
                    recovered = potential_json + ("}" * depth)
                    obj = json.loads(recovered, strict=False)
                else:
                    raise
            except Exception:
                # 6. Fallback: Try even more aggressive regex if still failing
                import re
                match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if match:
                    try:
                        obj = json.loads(match.group(0), strict=False)
                    except:
                        raise json.JSONDecodeError("Could not recover JSON from content", potential_json, 0)
                else:
                    raise json.JSONDecodeError("No JSON structure found", cleaned, 0)
                    
        # Apply normalization before Pydantic validation
        obj = self._normalize_obj(obj, schema)
        return schema.model_validate(obj)

    def _normalize_obj(self, obj: Any, schema: Type[T]) -> Any:
        """
        Normalize keys in objects to match expected schema fields.
        e.g. 'text' -> 'content'
        """
        if not isinstance(obj, dict):
            return obj
            
        # Common mapping for FlexDoc-like models
        if "text" in obj and "content" not in obj:
            obj["content"] = obj["text"]
        if "thoughts" in obj and "thought_process" not in obj:
            obj["thought_process"] = obj["thoughts"]
            
        # Ensure 'content' is never nested JSON if it was accidentally stringified twice
        if "content" in obj and isinstance(obj["content"], str):
             c = obj["content"].strip()
             if c.startswith('{') and c.endswith('}') and '"content"' in c:
                 try:
                     inner = json.loads(c)
                     if isinstance(inner, dict) and "content" in inner:
                         obj["content"] = inner["content"]
                 except:
                     pass
        return obj
