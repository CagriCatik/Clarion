import json
import httpx
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Any, List, Optional, Callable
from pydantic import BaseModel, ValidationError

# Use string forward reference to avoid circular import if necessary, 
# but import if possible. 
from clarion.schemas import GenerationConfig
from clarion.prompt_loader import render_prompt

T = TypeVar("T", bound=BaseModel)

_httpx_clients: dict = {}

def get_shared_client() -> httpx.AsyncClient:
    global _httpx_clients
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Fallback for non-async contexts if any
        return httpx.AsyncClient()
        
    if loop not in _httpx_clients or _httpx_clients[loop].is_closed:
        # Increase timeout to 60m for large model loading and long generation
        timeout = httpx.Timeout(3600.0, connect=30.0)
        _httpx_clients[loop] = httpx.AsyncClient(timeout=timeout)
    return _httpx_clients[loop]

class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, schema: Type[T], config: Optional[GenerationConfig] = None, status_callback: Optional[Callable] = None) -> T:
        pass

    async def list_models(self) -> List[str]:
        return []

class OllamaProvider(LLMProvider):
    def __init__(self, model_name: str = "llama3.1", base_url: Optional[str] = None):
        import os
        self.model_name = model_name
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def generate_json(self, prompt: str, schema: Type[T], config: Optional[GenerationConfig] = None, status_callback: Optional[Callable] = None) -> T:
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
            msg = f"Clarion Repair: JSON validation failed. Retrying with repair logic... village"
            print(msg)
            if status_callback: 
                import asyncio
                if asyncio.iscoroutinefunction(status_callback): await status_callback(msg)
                else: status_callback(msg)
            
            repair_prompt = render_prompt("repair.j2", error=str(e), schema_json=schema_json)
            
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
                        # If truly empty, and we need content, this is a failure the model didn't provide anything.
                        print("Error: Model returned an empty response.")
                        raise final_e
                        
                    return schema(content=safe_content)
                
                print(f"Retry failed: {final_e}. Checking for fallback candidates...")
                
                # FINAL ATTEMPT: Try WITHOUT 'format: json' if the model is being stubborn.
                # Sometimes Ollama's strict mode causes the model to return nothing if it can't 
                # satisfy the constraint immediately.
                if payload.get("format") == "json":
                    print("Last resort: Attempting generation WITHOUT strict JSON format enforcement...")
                    payload.pop("format")
                    # Make the prompt even more explicit for non-formatted mode
                    payload["messages"].append({
                        "role": "user", 
                        "content": "CRITICAL: You must return ONLY valid JSON. No markdown, no text. Just the JSON object."
                    })
                    try:
                        resp_text = await self._call_api(payload)
                        return self._parse_and_validate(resp_text, schema)
                    except:
                        pass

                raise final_e
            
    async def list_models(self) -> List[str]:
        """
        Lists available models from Ollama.
        """
        client = get_shared_client()
        try:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            print(f"Failed to list models: {e}")
            return []

    async def _call_api(self, payload: dict) -> str:
        client = get_shared_client()
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
                
                content = data.get("message", {}).get("content", "")
                
                # Diagnostic check for empty responses
                if not content:
                    done = data.get("done", False)
                    done_reason = data.get("done_reason", "unknown")
                    print(f"--- WARNING: LLM returned empty content ---")
                    print(f"Done: {done}, Reason: {done_reason}")
                    print(f"Full response: {json.dumps(data, indent=2)}")
                    print(f"-------------------------------------------")
                
                return content
                
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
        
        CRITICAL: Some models output markdown THEN JSON. We must extract ONLY the JSON.
        """
        # 1. Strip whitespace
        cleaned = content.strip()
        
        # 2. Remove markdown code blocks if present
        def clean_markdown(text: str) -> str:
            if not text:
                return text
            if "```" in text:
                import re
                # Try to find the last JSON-like block (often models repeat or fix themselves)
                matches = re.findall(r'```(?:json)?\\s*(.*?)\\s*```', text, re.DOTALL)
                if matches:
                    return matches[-1].strip()
            return text
            
        cleaned = clean_markdown(cleaned)
        
        if not cleaned:
             raise json.JSONDecodeError("Received empty response from LLM", content, 0)
        
        # 3. CRITICAL: If the model output markdown BEFORE the JSON, extract ONLY the JSON
        # Look for the LAST occurrence of { ... } in the entire content
        # This handles cases like: "# Header\n\nSome text\n\n{...json...}"
        
        # Find ALL potential JSON blocks (between { and })
        json_candidates = []
        brace_depth = 0
        json_start = -1
        
        for i, char in enumerate(cleaned):
            if char == '{':
                if brace_depth == 0:
                    json_start = i
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
                if brace_depth == 0 and json_start != -1:
                    json_candidates.append(cleaned[json_start:i+1])
                    json_start = -1
        
        # Try parsing candidates from LAST to FIRST (last is most likely correct)
        potential_json = None
        for candidate in reversed(json_candidates):
            try:
                obj = json.loads(candidate, strict=False)
                if isinstance(obj, dict):
                    potential_json = candidate
                    break
            except:
                continue
        
        # Fallback to old logic if brace extraction failed
        if not potential_json:
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
            # 5. Recovery: If it looks like it ended prematurely, try adding missing quotes/braces
            # This is common with large model outputs that hit token limits
            try:
                # 5a. Close unterminated quotes
                recovered = potential_json
                if recovered.count('"') % 2 != 0:
                    recovered += '"'
                
                # 5b. Count open/close braces
                depth = recovered.count('{') - recovered.count('}')
                if depth > 0:
                    recovered = recovered + ("}" * depth)
                    obj = json.loads(recovered, strict=False)
                elif recovered != potential_json:
                    obj = json.loads(recovered, strict=False)
                else:
                    raise
            except Exception:
                # 6. Fallback: Try even more aggressive regex if still failing
                import re
                match = re.search(r'\\{.*\\}', cleaned, re.DOTALL)
                if match:
                    try:
                        obj = json.loads(match.group(0), strict=False)
                    except:
                        raise json.JSONDecodeError("Could not recover JSON from content", potential_json, 0)
                else:
                    # Log raw content for debugging before raising
                    print(f"--- DEBUG: RAW LLM RESPONSE (Length: {len(content)}) ---\\n{content}\\n--- END DEBUG ---")
                    raise json.JSONDecodeError("No JSON structure found", cleaned, 0)
                    
        # Apply normalization before Pydantic validation
        obj = self._normalize_obj(obj, schema)
        try:
            return schema.model_validate(obj)
        except ValidationError as e:
            # If validation fails, log what we were trying to validate
            print(f"--- FAILED TO VALIDATE OBJECT ---")
            print(f"Object: {json.dumps(obj, indent=2)}")
            print(f"Error: {e}")
            print(f"----------------------------------")
            raise e

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
