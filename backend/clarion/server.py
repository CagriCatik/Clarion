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

import psutil
try:
    import pynvml
    pynvml.nvmlInit()
    nvml_initialized = True
except Exception:
    nvml_initialized = False

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
import time

# Output directory - use parent of backend (project root) / outputs
# When running from project root via `uvicorn clarion.server:app`, this resolves correctly
OUTPUT_DIR = Path("outputs")

app = FastAPI(title="Clarion API", version="1.0.0")

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
    model: str = Form("olmo-3:7b"),
    word_budget: int = Form(2000),
    overlap: int = Form(2),
    temperature: float = Form(0.2),
    top_p: float = Form(0.9),
    num_ctx: int = Form(4096),
    presence_penalty: float = Form(0.0),
    frequency_penalty: float = Form(0.0),
    repeat_penalty: float = Form(1.1),
    top_k: int = Form(40),
    num_predict: int = Form(2048),
    fast_mode: bool = Form(False),
    # Multi-Model Params
    generator_model: Optional[str] = Form(None),
    reviewer_model: Optional[str] = Form(None),
    interactive_review: bool = Form(False)
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
        start_time = time.time()
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
                top_k=top_k,
                fast_mode=fast_mode,
                generator_model=generator_model,
                reviewer_model=reviewer_model,
                interactive_review=interactive_review
            )
            
            provider = OllamaProvider(model_name=model)
            
            results = []
            
            # Status message queue for streaming
            status_queue = asyncio.Queue()
            
            for i, input_path_str in enumerate(saved_input_files):
                filename = Path(input_path_str).name
                yield f"data: {{\"status\": \"Processing file {i+1}/{len(saved_input_files)}: {filename}...\"}}\n\n"
                await asyncio.sleep(0.05)
                
                # Create a proper callback that queues messages
                async def progress_callback(msg: str, fn=filename):
                    clean_msg = msg.replace("\\n", " ").replace('"', "'")
                    await status_queue.put(f"[{fn}] {clean_msg}")
                
                # Run pipeline in background task
                async def run_with_status():
                    return await run_pipeline(config, input_path_str, provider, gen_config, progress_callback)
                
                # Run pipeline
                try:
                    # Start pipeline
                    task = asyncio.create_task(run_with_status())
                    
                    # Drain status queue while pipeline runs
                    while not task.done():
                        try:
                            msg = await asyncio.wait_for(status_queue.get(), timeout=0.1)
                            yield f"data: {{\"status\": \"{msg}\"}}\n\n"
                        except asyncio.TimeoutError:
                            pass
                    
                    # Get result
                    doc_result = await task
                    
                    # Render
                    md_output = render_markdown(doc_result.final_doc)
                    
                    # Persist to disk
                    OUTPUT_DIR.mkdir(exist_ok=True)
                    
                    base_name = Path(filename).stem
                    out_md_path = OUTPUT_DIR / f"{base_name}_doc.md"
                    out_json_path = OUTPUT_DIR / f"{base_name}_doc.json"
                    
                    with open(out_md_path, "w", encoding="utf-8") as f:
                        f.write(md_output)
                    with open(out_json_path, "w", encoding="utf-8") as f:
                        f.write(doc_result.final_doc.model_dump_json(indent=2))
                    
                    res_data = {
                        "filename": filename,
                        "markdown": md_output,
                        "json": doc_result.final_doc.model_dump(),
                        "saved_to": str(out_md_path.absolute()),
                        "review_report": doc_result.final_doc.review_report.model_dump() if doc_result.final_doc.review_report else None
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
                    yield f"data: {{\"error\": \"Error processing {filename}: {str(e)}\"}}\n\n"

            end_time = time.time()
            duration = end_time - start_time
            yield f"data: {{\"status\": \"Completed in {duration:.2f} seconds\"}}\n\n"

            # Final result - send each result separately for real-time updates
            for res in results:
                yield f"data: {json.dumps({'result': res})}\n\n"
            
            yield "data: {\"complete\": true}\n\n"
            
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

@app.get("/v1/metrics")
async def get_metrics():
    """
    Returns CPU, RAM, and GPU usage metrics.
    """
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    
    gpu_usage = None
    if nvml_initialized:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            # Memory utilized / memory total
            gpu_usage = (info.used / info.total) * 100
        except Exception:
            pass
            
    return {
        "cpu": cpu_usage,
        "ram": ram_usage,
        "gpu": gpu_usage
    }

@app.get("/v1/outputs")
async def list_outputs():
    """
    List all generated markdown documents.
    """
    if not OUTPUT_DIR.exists():
        return {"outputs": []}
    
    files = [f.name for f in OUTPUT_DIR.glob("*.md")]
    # Sort by modification time (newest first)
    files.sort(key=lambda f: (OUTPUT_DIR / f).stat().st_mtime, reverse=True)
    return {"outputs": files}

@app.get("/v1/outputs/{filename}")
async def get_output(filename: str):
    """
    Get the content of a specific markdown document.
    """
    output_path = OUTPUT_DIR / filename
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filename": filename, "markdown": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SaveOutputRequest(BaseModel):
    markdown: str

@app.post("/v1/outputs/{filename}")
async def save_output(filename: str, request: SaveOutputRequest):
    """
    Save edited markdown content.
    """
    output_path = OUTPUT_DIR / filename
    if not output_path.exists():
        # Allow creating new files? For now, only existing
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(request.markdown)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/stop")
def stop_server():
    """
    Gracefully stop the server.
    """
    import os
    import signal
    import threading
    
    def kill():
        time.sleep(1) # Give time to respond
        os.kill(os.getpid(), signal.SIGTERM)
        
    threading.Thread(target=kill).start()
    return {"status": "stopping"}

@app.post("/v1/open_outputs")
def open_outputs():
    try:
        output_dir = OUTPUT_DIR.resolve()
        output_dir.mkdir(exist_ok=True)
        os.startfile(str(output_dir))
        return {"status": "ok", "path": str(output_dir)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/v1/outputs/{filename}")
async def delete_output(filename: str):
    """
    Delete a specific output file (both .md and .json).
    """
    md_path = OUTPUT_DIR / filename
    
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Delete the markdown file
        md_path.unlink()
        
        # Also delete the corresponding JSON file if exists
        json_path = OUTPUT_DIR / filename.replace(".md", ".json")
        if json_path.exists():
            json_path.unlink()
            
        return {"status": "ok", "deleted": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

