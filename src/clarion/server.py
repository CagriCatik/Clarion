from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from pathlib import Path

from clarion.providers import OllamaProvider
from clarion.services.doc_service import DocService

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

app = FastAPI(
    title="Clarion API",
    version="0.1.0",
    description="Deterministic scientific documentation generator using LLMs.",
    contact={
        "name": "Cagri Catik",
        "email": "test@gmail.com",
    },
    openapi_tags=[
        {"name": "Core", "description": "Core documentation generation operations"},
        {"name": "Outputs", "description": "Operations for managing generated documents"},
        {"name": "System", "description": "Health, models, and system metrics"},
    ]
)

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

@app.post(
    "/v1/docgen",
    tags=["Core"],
    summary="Generate Documentation",
    description="Process uploaded markdown files with server-sent events for progress tracking and final results."
)
async def generate_doc(
    files: List[UploadFile] = File(...),
    instruction: Optional[str] = Form(None),
    prompt_files: List[UploadFile] = File(default=[]),
    model: str = Form("llama3.1"),
    word_budget: int = Form(2000),
    overlap: int = Form(2),
    temperature: float = Form(0.2),
    top_p: float = Form(0.9),
    num_ctx: int = Form(8192),
    presence_penalty: float = Form(0.0),
    frequency_penalty: float = Form(0.0),
    repeat_penalty: float = Form(1.1),
    top_k: int = Form(40),
    num_predict: int = Form(4096),
    fast_mode: bool = Form(False),
    use_rag: bool = Form(False),
    embedding_model: Optional[str] = Form(None),
    rag_k: int = Form(5),
    chunk_size: int = Form(4000),
    chunk_overlap: int = Form(500),
    selected_kb_ids: Optional[str] = Form(None)
):
    """
    Process uploaded markdown files with server-sent events for progress.
    """
    """
    Process uploaded markdown files with server-sent events for progress.
    """
    from clarion.services.doc_service import DocService

    gen_config_data = {
        "temperature": temperature,
        "top_p": top_p,
        "num_ctx": num_ctx,
        "num_predict": num_predict,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "repeat_penalty": repeat_penalty,
        "top_k": top_k,
        "fast_mode": fast_mode,
        "word_budget": word_budget,
        "overlap": overlap
    }

    return StreamingResponse(
        DocService.process_request_stream(
            files=files,
            instruction=instruction,
            prompt_files=prompt_files,
            model=model,
            gen_config_data=gen_config_data,
            use_rag=use_rag,
            embedding_model=embedding_model,
            rag_k=rag_k,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            selected_kb_ids=selected_kb_ids
        ),
        media_type="text/event-stream"
    )

@app.get(
    "/v1/models",
    tags=["System"],
    summary="List Available Models",
    description="Lists the available Ollama models separated by generation and embedding capabilities."
)
async def list_models():
    provider = OllamaProvider()
    all_models = await provider.list_models()
    
    # Heuristic: models containing "embed" or "embedding" are for embeddings
    # Others are for generation.
    generation_models = []
    embedding_models = []
    
    for m in all_models:
        name = m.lower()
        if any(x in name for x in ["embed", "bge", "bert", "minilm", "snowflake"]):
            embedding_models.append(m)
        else:
            generation_models.append(m)
            
    return {
        "models": generation_models,
        "embeddings": embedding_models
    }

@app.get(
    "/v1/health",
    tags=["System"],
    summary="Health Check",
    description="Simple endpoint to verify the API server is running."
)
def health():
    return {"status": "ok"}

@app.get(
    "/v1/metrics",
    tags=["System"],
    summary="Get System Metrics",
    description="Returns real-time CPU, RAM, and GPU usage metrics."
)
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

@app.get(
    "/v1/outputs",
    tags=["Outputs"],
    summary="List Generated Outputs",
    description="Lists all generated markdown documents in the outputs directory, sorted by newest first."
)
async def list_outputs():
    """
    List all generated markdown documents.
    """
    output_dir = Path("outputs")
    if not output_dir.exists():
        return {"outputs": []}
    
    files = [f.name for f in output_dir.glob("*.md")]
    # Sort by modification time (newest first)
    files.sort(key=lambda f: (output_dir / f).stat().st_mtime, reverse=True)
    return {"outputs": files}

@app.get("/v1/outputs/{filename}")
async def get_output(filename: str):
    """
    Get the content of a specific markdown document.
    """
    output_path = Path("outputs") / filename
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

@app.post(
    "/v1/outputs/{filename}",
    tags=["Outputs"],
    summary="Save Output Changes",
    description="Saves edited markdown content back to the specified output file."
)
async def save_output(filename: str, request: SaveOutputRequest):
    """
    Save edited markdown content.
    """
    output_path = Path("outputs") / filename
    if not output_path.exists():
        # Allow creating new files? For now, only existing
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(request.markdown)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(
    "/v1/kb/documents",
    tags=["System"],
    summary="List KB Documents",
    description="Lists all documents currently indexed in the persistent Knowledge Base."
)
async def list_kb_documents(embedding_model: Optional[str] = None):
    from clarion.knowledge import get_vector_store
    vs = get_vector_store(embedding_model=embedding_model)
    return {"documents": vs.list_indexed_documents()}

@app.post(
    "/v1/kb/index",
    tags=["System"],
    summary="Index Document to KB",
    description="Adds a file to the persistent Knowledge Base for later retrieval."
)
async def index_to_kb(file: UploadFile = File(...), embedding_model: Optional[str] = Form(None)):
    from clarion.knowledge import get_vector_store
    vs = get_vector_store(embedding_model=embedding_model)
    
    content = (await file.read()).decode("utf-8")
    vs.index_document(file.filename, content)
    
    return {"status": "ok", "filename": file.filename}

@app.post("/v1/open_outputs")
async def open_outputs():
    try:
        output_dir = Path("outputs").resolve()
        output_dir.mkdir(exist_ok=True)
        # Run os.startfile in thread as it spawns a process
        await asyncio.to_thread(os.startfile, str(output_dir))
        return {"status": "ok", "path": str(output_dir)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
