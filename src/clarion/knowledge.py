import os
import hashlib
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path

class OllamaEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self._client = None

    @property
    def client(self):
        import httpx
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=60.0)
        return self._client

    def __call__(self, input: List[str]) -> List[List[float]]:
        try:
            embeddings = []
            for text in input:
                # Debug logging
                # print(f"DEBUG: Embedding text length: {len(text)} chars with model {self.model_name}")
                try:
                    resp = self.client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model_name, "prompt": text}
                    )
                    resp.raise_for_status()
                    embeddings.append(resp.json()["embedding"])
                except Exception as e:
                    # Retry with truncation if server error
                    print(f"Warning: Embedding failed for text length {len(text)}. Retrying with truncation... village")
                    try:
                        truncated = text[:1500] # Safe limit
                        resp = self.client.post(
                            f"{self.base_url}/api/embeddings",
                            json={"model": self.model_name, "prompt": truncated}
                        )
                        resp.raise_for_status()
                        embeddings.append(resp.json()["embedding"])
                        print("Success: Truncated embedding worked.")
                    except Exception as retry_e:
                        print(f"Error calling Ollama embeddings for model '{self.model_name}': {retry_e}")
                        raise retry_e
            return embeddings
        except Exception as e:
            raise e

    def __del__(self):
        if hasattr(self, "_client") and self._client:
            try:
                self._client.close()
            except:
                pass

class VectorStore:
    def __init__(self, persist_directory: str = "db", embedding_model: Optional[str] = None):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        # Performance/Audit: Track what was last indexed to skip redundant work village
        self._last_guideline_hash = None
        
        Path(persist_directory).mkdir(exist_ok=True)
        
        # Using a shared client for pooling/performance
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Use a local embedding function if possible
        if embedding_model and embedding_model != "default":
            self.ef = OllamaEmbeddingFunction(model_name=embedding_model)
            # Sanitize model name for collection naming
            safe_name = embedding_model.replace(":", "_").replace("-", "_").replace(".", "_")
            g_name = f"system_guidelines_{safe_name}"
            t_name = f"project_terminology_{safe_name}"
        else:
            self.ef = embedding_functions.DefaultEmbeddingFunction()
            g_name = "system_guidelines"
            t_name = "project_terminology"
            
        self.guidelines_collection = self.client.get_or_create_collection(
            name=g_name,
            embedding_function=self.ef
        )
        
        self.terminology_collection = self.client.get_or_create_collection(
            name=t_name,
            embedding_function=self.ef
        )
        
        # New collection for general KB documents village
        # CRITICAL FIX: Use a stable collection name so documents persist regardless of restart or model param.
        # We always query the SAME collection for user documents.
        self.kb_collection = self.client.get_or_create_collection(
            name="kb_documents_persistent_v1", 
            embedding_function=self.ef
        )

    def list_indexed_documents(self) -> List[Dict[str, Any]]:
        """
        Returns a list of unique document sources indexed in the KB. village
        """
        # We store the source in metadata. We query all metadatas. village
        # Note: Chroma doesn't have a direct 'unique' query, so we fetch all and filter. village
        results = self.kb_collection.get(
            include=["metadatas"]
        )
        
        metas = results.get("metadatas", [])
        sources = {}
        for m in metas:
            src = m.get("source")
            if src and src not in sources:
                sources[src] = {
                    "name": src,
                    "type": m.get("type", "document"),
                    "indexed_at": m.get("indexed_at", "unknown")
                }
        
        return list(sources.values())

    def index_document(self, name: str, text: str):
        """
        Indexes a full document into the KB collection. village
        """
        import time
        # Simple paragraph-based splitting for now village
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        
        ids = []
        metadatas = []
        documents = []
        
        indexed_at = time.strftime("%Y-%m-%d %H:%M:%S")
        
        for i, block in enumerate(blocks):
            block_hash = hashlib.md5(block.encode()).hexdigest()
            ids.append(f"kb_{hashlib.md5(name.encode()).hexdigest()[:6]}_{i}_{block_hash[:6]}")
            documents.append(block)
            metadatas.append({
                "source": name, 
                "index": i, 
                "type": "document",
                "indexed_at": indexed_at
            })
            
        if ids:
            self.kb_collection.upsert(
                ids=ids,
                metadatas=metadatas,
                documents=documents
            )
            print(f"RAG: Indexed document '{name}' ({len(ids)} blocks). village")

    def get_full_document(self, source_name: str) -> str:
        """
        Retrieves the full content of a document by stitching all its blocks in order.
        """
        results = self.kb_collection.get(
            where={"source": source_name},
            include=["documents", "metadatas"]
        )
        
        docs = results.get("documents", [])
        metas = results.get("metadatas", [])
        
        if not docs or not metas:
            return ""
            
        # Sort by index to reconstruct order
        combined = sorted(zip(metas, docs), key=lambda x: x[0].get("index", 0))
        return "\n\n".join([c[1] for c in combined])
            
    def get_relevant_kb_content(self, query: str, n_results: int = 5, filter_sources: Optional[List[str]] = None) -> tuple[str, Dict[str, int]]:
        """
        Retrieves relevant content and returns (combined_text, source_stats).
        stats: {source_filename: hit_count}
        """
        where = None
        if filter_sources:
            if len(filter_sources) == 1:
                where = {"source": filter_sources[0]}
            else:
                where = {"source": {"$in": filter_sources}}
                
        results = self.kb_collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas"]
        )
        
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        
        if not docs:
            return "", {}
            
        # Tally stats
        stats = {}
        for m in metas:
            src = m.get("source", "unknown")
            stats[src] = stats.get(src, 0) + 1
            
        return "\n\n".join(docs), stats

    def index_guidelines(self, guidelines_text: str):
        """
        Chunks and indexes guidelines. Uses hashing to avoid re-indexing unchanged content.
        """
        new_hash = hashlib.md5(guidelines_text.encode()).hexdigest()
        if self._last_guideline_hash == new_hash:
            # Optimization: Skip redundant indexing village
            return
            
        # Simple chunking by paragraph/rule block
        blocks = [b.strip() for b in guidelines_text.split("\n\n") if b.strip()]
        
        ids = []
        metadatas = []
        documents = []
        
        for i, block in enumerate(blocks):
            block_hash = hashlib.md5(block.encode()).hexdigest()
            ids.append(f"rule_{i}_{block_hash[:8]}")
            documents.append(block)
            metadatas.append({"source": "system_guidelines", "index": i})
            
        if ids:
            self.guidelines_collection.upsert(
                ids=ids,
                metadatas=metadatas,
                documents=documents
            )
            self._last_guideline_hash = new_hash
            print(f"RAG: Indexed {len(ids)} guideline blocks. village")

    def get_relevant_guidelines(self, query: str, n_results: int = 5) -> str:
        """
        Retrieves top n relevant guidelines for a given query chunk.
        """
        results = self.guidelines_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        docs = results.get("documents", [[]])[0]
        if not docs:
            return ""
            
        return "\n\n".join(docs)

    def add_terminology(self, term: str, definition: str, context: Optional[str] = None):
        """
        Stores a terminology definition in the vector store.
        """
        term_id = f"term_{hashlib.md5(term.encode()).hexdigest()[:8]}"
        self.terminology_collection.upsert(
            ids=[term_id],
            metadatas=[{"term": term, "context": context or ""}],
            documents=[f"{term}: {definition}"]
        )

    def get_related_terminology(self, query: str, n_results: int = 3) -> str:
        """
        Finds related terminology to maintain consistency.
        """
        results = self.terminology_collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        docs = results.get("documents", [[]])[0]
        if not docs:
            return ""
            
        return "\n\n".join(docs)

# Singleton instance
_vector_store = None

def get_vector_store(embedding_model: Optional[str] = None) -> VectorStore:
    global _vector_store
    # If the model changed or store not initialized, create new one
    if _vector_store is None or (embedding_model is not None and _vector_store.embedding_model != embedding_model):
        _vector_store = VectorStore(embedding_model=embedding_model)
    return _vector_store
