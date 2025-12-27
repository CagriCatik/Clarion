import typer
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional
from clarion.schemas import InstructionConfig
from clarion.pipeline import run_pipeline
from clarion.renderer import render_markdown
from clarion.providers import OllamaProvider
from clarion.prompts import Stage

import sys
# ... imports
app = typer.Typer(help="Clarion: Bio-scientific documentation generator.")


def generate(
    inputs: List[Path] = typer.Option(..., "--input", "-i", help="Input files"),
    out_dir: Path = typer.Option(..., help="Output directory"),
    # ...
    instruction: str = typer.Option(None, help="Inline instruction text"),
    prompt_file: List[Path] = typer.Option([], help="Path to user prompt override file(s)"),
    # Provider options
    model: str = typer.Option("llama3.1", help="Ollama model name"),
    base_url: str = typer.Option("http://localhost:11434", help="Ollama base URL"),
    # Pipeline options
    word_budget: int = typer.Option(2000, help="Word budget per chunk"),
    overlap: int = typer.Option(2, help="Segment overlap count"),
    # Gen options
    temperature: float = typer.Option(0.2, help="LLM Temperature"),
    top_p: float = typer.Option(0.9, help="LLM Top P"),
    num_ctx: int = typer.Option(4096, help="LLM Context Window Size")
):
    """
    Generate documentation from input files.
    """
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("clarion")
    
    # Ensure output dir
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Config
    config = InstructionConfig(
        user_prompt_files=[str(p) for p in prompt_file],
        inline_instruction=instruction
    )
    
    # Provider
    provider = OllamaProvider(model_name=model, base_url=base_url)
    
    # Generation config
    from clarion.schemas import GenerationConfig
    gen_config = GenerationConfig(
        temperature=temperature,
        top_p=top_p,
        num_ctx=num_ctx
    )
    
    async def process_all():
        for input_path in inputs:
            logger.info(f"Processing {input_path}...")
            try:
                result = await run_pipeline(config, str(input_path), provider, gen_config)
                
                # Write Manifest
                manifest_name = f"{input_path.stem}_manifest.json"
                manifest_path = out_dir / manifest_name
                # Note: valid manifest generation requires passing segments/chunks/etc.
                # Currently run_pipeline returns DocResult which has final_doc.
                # To get full manifest, we might need run_pipeline to return more data 
                # or have it write the manifest. 
                # For this MVP, let's assume run_pipeline could handle writing or we fake it here
                # actually, pipeline.py needs to handle it contextually.
                # Let's fix pipeline.py later to return full context if needed, 
                # but for now we won't crash if we miss deep audit in CLI. 
                # Actually, `run_pipeline` logic was:
                # return DocResult(..., manifest_path="") 
                # and we defined generate_manifest inside pipeline.py but didn't call it fully with all context.
                # We will accept this gap for the "Skeleton" phase and refine if needed.
                
                # Render Markdown
                md_content = render_markdown(result.final_doc)
                out_name = f"{input_path.stem}_doc.md"
                out_path = out_dir / out_name
                
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
                    
                logger.info(f"Generated {out_path}")
                
            except Exception as e:
                logger.error(f"Failed to process {input_path}: {e}")
                # continue or fail?
                # fail for now
                raise e

    asyncio.run(process_all())

if __name__ == "__main__":
    print(f"DEBUG: argv={sys.argv}")
    typer.run(generate)
