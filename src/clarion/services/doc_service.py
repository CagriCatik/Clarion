import asyncio
import shutil
import tempfile
import time
import json
import os
from pathlib import Path
from typing import List, Optional, AsyncGenerator

from fastapi import UploadFile, HTTPException

from clarion.schemas import InstructionConfig, GenerationConfig, DocResult, MultiDocResponse, DocumentResult
from clarion.pipeline import run_pipeline
from clarion.providers import OllamaProvider
from clarion.renderer import render_markdown

class DocService:
    @staticmethod
    async def save_uploads(
        files: List[UploadFile], 
        prompt_files: List[UploadFile]
    ) -> tuple[Path, List[str], List[str]]:
        """
        Saves uploaded files to a temp directory.
        Returns (temp_dir_path, saved_input_files, saved_prompt_files).
        """
        request_temp_dir = tempfile.mkdtemp()
        request_temp_path = Path(request_temp_dir)
        
        try:
            # Save prompt files
            saved_prompt_files = []
            for pf in prompt_files:
                p_path = request_temp_path / f"prompt_{pf.filename}"
                def save_prompt_file(path, file_obj):
                    with open(path, "wb") as f:
                        shutil.copyfileobj(file_obj, f)
                await asyncio.to_thread(save_prompt_file, p_path, pf.file)
                saved_prompt_files.append(str(p_path))
                
            # Save input files
            saved_input_files = []
            for file in files:
                i_path = request_temp_path / file.filename
                def save_input_file(path, file_obj):
                    with open(path, "wb") as f:
                        shutil.copyfileobj(file_obj, f)
                    print(f"DEBUG: Saved input file {path} (Size: {path.stat().st_size} bytes)")

                await asyncio.to_thread(save_input_file, i_path, file.file)
                saved_input_files.append(str(i_path))
                
            return request_temp_path, saved_input_files, saved_prompt_files
            
        except Exception as e:
            await asyncio.to_thread(shutil.rmtree, request_temp_dir)
            raise e

    @staticmethod
    async def process_request_stream(
        files: List[UploadFile],
        instruction: Optional[str],
        prompt_files: List[UploadFile],
        model: str,
        gen_config_data: dict,
        use_rag: bool,
        embedding_model: Optional[str],
        rag_k: int,
        chunk_size: int,
        chunk_overlap: int,
        selected_kb_ids: Optional[str]
    ) -> AsyncGenerator[str, None]:
        
        # 1. Save files
        try:
            temp_path, saved_input_files, saved_prompt_files = await DocService.save_uploads(files, prompt_files)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save uploaded files: {e}")

        # 2. Generator logic
        try:
            start_time = time.time()
            
            config = InstructionConfig(
                user_prompt_files=saved_prompt_files,
                inline_instruction=instruction
            )
            
            gen_config = GenerationConfig(
                **gen_config_data,
                rag_k=rag_k,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            provider = OllamaProvider(model_name=model)
            results = []
            
            for i, input_path_str in enumerate(saved_input_files):
                filename = Path(input_path_str).name
                yield f"event: status\ndata: Processing file {i+1}/{len(saved_input_files)}: {filename}...\n\n"
                await asyncio.sleep(0.1)
                
                # --- KB ONLY MODE HANDLING ---
                kb_ids = []
                if selected_kb_ids:
                    try:
                        kb_ids = json.loads(selected_kb_ids)
                    except:
                        if isinstance(selected_kb_ids, str):
                            kb_ids = json.loads(selected_kb_ids) if selected_kb_ids.startswith("[") else [selected_kb_ids]

                if filename == "KB_Context_Request.txt" and kb_ids and embedding_model:
                     from clarion.knowledge import get_vector_store
                     try:
                        yield f"event: status\ndata: [{filename}] Fetching content of {len(kb_ids)} KB documents...\n\n"
                        vs = get_vector_store(embedding_model=embedding_model)
                        full_kb_content = ""
                        for doc_id in kb_ids:
                             content = vs.get_full_document(doc_id)
                             if content: full_kb_content += f"\n\n# Source: {doc_id}\n\n{content}"
                        
                        if full_kb_content.strip():
                            await asyncio.to_thread(lambda p, t: open(p, "w", encoding="utf-8").write(t), input_path_str, full_kb_content)
                            if len(kb_ids) == 1: filename = (Path(kb_ids[0]).name if Path(kb_ids[0]).name.lower().endswith(('.md', '.txt')) else Path(kb_ids[0]).name + ".md")
                            else: filename = "Combined_Knowledge_Context.md"
                            yield f"event: status\ndata: [{filename}] Loaded {len(full_kb_content)} chars from KB docs.\n\n"
                     except Exception as e:
                          yield f"event: status\ndata: [{filename}] Failed to fetch KB content: {e}\n\n"

                try:
                    # Status synchronization queue
                    status_queue = asyncio.Queue()
                    async def progress_callback(msg: str): await status_queue.put(msg)

                    # Run pipeline task
                    pipeline_task = asyncio.create_task(
                        run_pipeline(config, input_path_str, provider, gen_config, progress_callback, 
                                     use_rag=use_rag, embedding_model=embedding_model, selected_kb_ids=kb_ids)
                    )

                    # Process results and status updates concurrently
                    try:
                        while not pipeline_task.done():
                            try:
                                msg = await asyncio.wait_for(status_queue.get(), timeout=0.5)
                                clean_msg = msg.replace("\n", " ")
                                yield f"event: status\ndata: [{filename}] {clean_msg}\n\n"
                            except asyncio.TimeoutError:
                                continue
                        
                        while not status_queue.empty():
                            msg = status_queue.get_nowait()
                            clean_msg = msg.replace("\n", " ")
                            yield f"event: status\ndata: [{filename}] {clean_msg}\n\n"

                        doc_result = await pipeline_task
                    finally:
                        if not pipeline_task.done():
                            pipeline_task.cancel()
                            try: await pipeline_task
                            except: pass

                    md_output = render_markdown(doc_result.final_doc)
                    
                    # Persist
                    output_dir = Path("outputs")
                    output_dir.mkdir(exist_ok=True)
                    
                    base_name = Path(filename).stem
                    out_md_path = output_dir / f"{base_name}_doc.md"
                    out_json_path = output_dir / f"{base_name}_doc.json"
                    
                    def write_results(md_path, json_path, md_content, json_content):
                        with open(md_path, "w", encoding="utf-8") as f: f.write(md_content)
                        with open(json_path, "w", encoding="utf-8") as f: f.write(json_content)

                    await asyncio.to_thread(write_results, out_md_path, out_json_path, md_output, 
                                           doc_result.final_doc.model_dump_json(indent=2))
                    
                    file_duration = time.time() - start_time
                    results.append({
                        "filename": filename, "markdown": md_output, "json": doc_result.final_doc.model_dump(),
                        "saved_to": str(out_md_path.absolute()), "thought_process": doc_result.final_doc.thought_process,
                        "generation_time": file_duration
                    })

                except Exception as e:
                    import traceback
                    print(traceback.format_exc())
                    err_msg = str(e)
                    if "weekly usage limit" in err_msg.lower() or "rate limit" in err_msg.lower():
                        err_msg = f"⚠️ API Rate Limit: {err_msg}"
                    elif "max retries" in err_msg.lower():
                        err_msg = f"❌ Generation Failed: {err_msg}"
                    
                    yield f"event: error\ndata: [{filename}] {err_msg}\n\n"
                    results.append({"filename": filename, "error": err_msg})

            end_time = time.time()
            duration = end_time - start_time
            
            successful_docs = [r for r in results if 'error' not in r]
            
            if not successful_docs:
                yield f"event: error\ndata: All {len(results)} file(s) failed to process.\n\n"
                yield "event: complete\ndata: failed\n\n"
                return

            yield f"event: status\ndata: Successfully processed {len(successful_docs)}/{len(results)} files in {duration:.2f}s\n\n"
            
            multi_response = MultiDocResponse(
                documents=[
                    DocumentResult(
                        filename=r['filename'],
                        content=r['markdown'],
                        thought_process=r.get('thought_process'),
                        generation_time=r['generation_time']
                    ) for r in successful_docs
                ],
                total_time=duration,
                total_files=len(successful_docs)
            )
            
            yield f"event: result\ndata: {multi_response.model_dump_json()}\n\n"
            yield "event: complete\ndata: success\n\n"
            
        finally:
            try:
                await asyncio.to_thread(shutil.rmtree, temp_path)
            except Exception as e:
                print(f"Failed to cleanup temp dir {temp_path}: {e}")
