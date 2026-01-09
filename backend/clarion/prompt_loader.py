import os
from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape

class PromptLoader:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptLoader, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        # Locate prompts directory relative to this file
        current_dir = Path(__file__).parent
        prompts_dir = current_dir / "prompts"
        
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render(self, template_name: str, **kwargs: Any) -> str:
        """
        Renders a Jinja2 template with the given context.
        """
        template = self.env.get_template(template_name)
        return template.render(**kwargs)

# Global singleton accessor
loader = PromptLoader()

def render_prompt(template_name: str, **kwargs: Any) -> str:
    return loader.render(template_name, **kwargs)
