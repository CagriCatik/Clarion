from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import shutil
import tempfile
import os
import json
from pathlib import Path

from clarion.schemas import InstructionConfig, DocResult
from clarion.pipeline import run_pipeline
from clarion.providers import OllamaProvider
from clarion.renderer import render_markdown

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI(title="Clarion API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProcessRequest(BaseModel):
    # For file uploads we usually form-data, so pydantic model for body is tricky
    # We will use simple form params in the endpoint
    pass

@app.post("/v1/docgen")
async def generate_doc(
    files: List[UploadFile] = File(...),
    instruction: Optional[str] = Form(None),
    prompt_files: List[UploadFile] = File(default=[]),
    model: str = Form("llama3.1"),
    word_budget: int = Form(2000),
    overlap: int = Form(2),
    temperature: float = Form(0.2),
    top_p: float = Form(0.9),
    num_ctx: int = Form(4096),
    presence_penalty: float = Form(0.0),
    frequency_penalty: float = Form(0.0),
    repeat_penalty: float = Form(1.1),
    top_k: int = Form(40),
    num_predict: int = Form(2048)
):
    """
    Process uploaded markdown files with server-sent events for progress.
    """
    
    # 1. Create unique temp dir for this request
    # We must do this synchronously before returning to keep files open while we copy them
    request_temp_dir = tempfile.mkdtemp()
    request_temp_path = Path(request_temp_dir)
    
    try:
        # 2. Save all prompt files
        saved_prompt_files = []
        for pf in prompt_files:
            p_path = request_temp_path / f"prompt_{pf.filename}"
            with open(p_path, "wb") as f:
                shutil.copyfileobj(pf.file, f)
            saved_prompt_files.append(str(p_path))
            
        # 3. Save all input files
        saved_input_files = []
        for file in files:
            i_path = request_temp_path / file.filename
            with open(i_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            saved_input_files.append(str(i_path))
            
    except Exception as e:
        # If save fails, cleanup and raise
        shutil.rmtree(request_temp_dir)
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {e}")

    # 4. Define generator that uses these saved files
    async def event_generator():
        try:
            config = InstructionConfig(
                user_prompt_files=saved_prompt_files,
                inline_instruction=instruction
            )
            
            from clarion.schemas import GenerationConfig
            gen_config = GenerationConfig(
                temperature=temperature,
                top_p=top_p,
                num_ctx=num_ctx,
                num_predict=num_predict,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
                repeat_penalty=repeat_penalty,
                top_k=top_k
            )
            
            provider = OllamaProvider(model_name=model)
            
            results = []
            
            for i, input_path_str in enumerate(saved_input_files):
                filename = Path(input_path_str).name
                yield f"event: status\ndata: Processing file {i+1}/{len(saved_input_files)}: {filename}...\n\n"
                await asyncio.sleep(0.1) 
                
                # Callback for pipeline
                async def progress_callback(msg: str):
                    clean_msg = msg.replace("\n", " ")
                    yield f"event: status\ndata: [{filename}] {clean_msg}\n\n"
                
                # Run pipeline
                try:
                    doc_result = await run_pipeline(config, input_path_str, provider, gen_config, progress_callback)
                    
                    # Render
                    md_output = render_markdown(doc_result.final_doc)
                    
                    # Persist to disk
                    output_dir = Path("outputs")
                    output_dir.mkdir(exist_ok=True)
                    
                    base_name = Path(filename).stem
                    out_md_path = output_dir / f"{base_name}_doc.md"
                    out_json_path = output_dir / f"{base_name}_doc.json"
                    
                    with open(out_md_path, "w", encoding="utf-8") as f:
                        f.write(md_output)
                    with open(out_json_path, "w", encoding="utf-8") as f:
                        f.write(doc_result.final_doc.model_dump_json(indent=2))
                    
                    res_data = {
                        "filename": filename,
                        "markdown": md_output,
                        "json": doc_result.final_doc.model_dump(),
                        "saved_to": str(out_md_path.absolute())
                    }
                    results.append(res_data)
                    
                except Exception as e:
                    import traceback
                    print(traceback.format_exc())
                    
                    err_data = {
                        "filename": filename,
                        "error": str(e)
                    }
                    results.append(err_data)
                    yield f"event: error\ndata: Error processing {filename}: {str(e)}\n\n"

            # Final result
            yield f"event: result\ndata: {json.dumps({'results': results})}\n\n"
            yield "event: complete\ndata: done\n\n"
            
        finally:
            # CLEANUP TEMP DIR
            try:
                shutil.rmtree(request_temp_dir)
            except Exception as e:
                print(f"Failed to cleanup temp dir {request_temp_dir}: {e}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/v1/models")
async def list_models():
    provider = OllamaProvider()
    models = await provider.list_models()
    return {"models": models}

@app.get("/v1/health")
def health():
    return {"status": "ok"}

@app.post("/v1/open_outputs")
def open_outputs():
    try:
        output_dir = Path("outputs").resolve()
        output_dir.mkdir(exist_ok=True)
        os.startfile(str(output_dir))
        return {"status": "ok", "path": str(output_dir)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
