import json
import httpx
import re
import time
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Any, List, Optional
from pydantic import BaseModel, ValidationError

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
    def __init__(self, model_name: str = "olmo-3:7b", base_url: Optional[str] = None):
        import os
        self.model_name = model_name
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    async def generate_json(self, prompt: str, schema: Type[T], config: Optional[GenerationConfig] = None, model_override: Optional[str] = None) -> T:
        """
        Generates a JSON response matching the schema.
        """
        system_prompt = render_prompt("01_system_core.j2")
        user_prompt = prompt # Raw prompt from pipeline (which now contains the specific Role Task)
        
        # Merge defaults
        options = {
            "temperature": 0.2,
            "top_p": 0.9,
            "num_ctx": 16384,
            "num_predict": 8192
        }
        if config:
            options["temperature"] = config.temperature
            options["top_p"] = config.top_p
            if config.num_ctx: options["num_ctx"] = config.num_ctx
            if config.num_predict: options["num_predict"] = config.num_predict
            
        payload = {
            "model": model_override or self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": options
        }
        
        print(f"DEBUG: Ollama Request Payload (model={self.model_name}, ctx={options.get('num_ctx')}): {json.dumps(payload, default=str)[:2000]}...")
        # Call Ollama
        start_time = time.time()
        try:
            timeout = httpx.Timeout(1200.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
            
            duration = time.time() - start_time
            print(f"Ollama generation completed in {duration:.2f}s")
                
            response_text = data["message"].get("content", "")
            internal_thought = data["message"].get("thinking", "")
            
            if not response_text and internal_thought:
                # Fallback: if we only got thinking, use it as content or throw error
                # For now, let's try to parse what we have
                response_text = internal_thought
            
            if not response_text:
                raise Exception("Ollama returned an empty response.")
                
            return self._parse_any(response_text, schema, internal_thought)

        except Exception as e:
            print(f"Generation error: {e}. Attempting recovery...")
            if hasattr(schema, "model_fields") and "content" in schema.model_fields:
                return schema(content=f"Error during generation: {str(e)}")
            raise

    def _parse_any(self, text: str, schema: Type[T], internal_thought: str = "") -> T:
        # Pre-process: strip <thought> blocks if they leaked into the content
        clean_text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL).strip()
            
        # 1. Try JSON parsing
        try:
            data = json.loads(clean_text)
            if internal_thought and not data.get("thought_process"):
                data["thought_process"] = internal_thought
            return schema(**data)
        except (json.JSONDecodeError, ValidationError):
            pass
            
        # 2. Try Frontmatter parsing
        return self._parse_frontmatter_markdown(clean_text, schema, internal_thought)

    def _parse_frontmatter_markdown(self, text: str, schema: Type[T], internal_thought: str = "") -> T:
        thought_process = internal_thought or None
        content = text.strip()
        
        # Strip any remaining meta-commentary before the first header if no frontmatter found
        if not content.startswith("---") and "# " in content:
            header_start = content.find("# ")
            if header_start > 0:
                # possible meta-commentary before title
                possible_meta = content[:header_start].strip()
                if not thought_process:
                    thought_process = possible_meta
                content = content[header_start:].strip()

        try:
            parts = re.split(r'^---\s*$', content, maxsplit=2, flags=re.MULTILINE)
            if len(parts) >= 3:
                yaml_block = parts[1].strip()
                content = parts[2].strip()
                tp_match = re.search(r'thought_process:\s*(?P<quote>["\']?)(.*?)(?P=quote)\s*($|\n)', yaml_block, re.DOTALL)
                if tp_match:
                    thought_process = tp_match.group(2).strip()
            elif len(parts) == 2:
                if not parts[0].strip():
                    content = parts[1].strip()
        except Exception:
            pass
                
        if not content.strip() and text.strip():
            content = text.strip()
                
        try:
            return schema(
                content=str(content).strip(),
                thought_process=str(thought_process) if thought_process else None
            )
        except Exception:
            if hasattr(schema, "model_fields") and "content" in schema.model_fields:
                 return schema(content=str(content).strip())
            raise

    async def list_models(self) -> List[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
            except Exception as e:
                print(f"Failed to list models: {e}")
                return []
