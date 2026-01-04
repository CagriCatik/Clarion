import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from clarion.knowledge import VectorStore
from clarion.pipeline import DirectPipeline
from clarion.schemas import FlexDoc, GenerationConfig

from chromadb import EmbeddingFunction

# Mock for OllamaEmbeddingFunction to avoid actual API calls
class MockEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input):
        # Return a fixed mock embedding for any input
        return [[0.1] * 768 for _ in input]
    
    def embed_documents(self, input):
        return self(input)

    def embed_query(self, input):
        return [0.1] * 768

    def to_json(self):
        return {"model_name": "mock-model"}

@pytest.fixture
def mock_chroma(tmp_path):
    """Mocks ChromaDB persistence path"""
    return str(tmp_path / "chroma_db")

@pytest.fixture
def vector_store(mock_chroma):
    """Creates a VectorStore with a mocked embedding function"""
    with patch("clarion.knowledge.OllamaEmbeddingFunction", return_value=MockEmbeddingFunction()):
        store = VectorStore(persist_directory=mock_chroma, embedding_model="nomic-embed-text")
        # Inject mock embedding function directly as well to be safe
        store.ef = MockEmbeddingFunction()
        return store

# --- TEST 1: Persistence ---
def test_kb_persistence(mock_chroma):
    """
    Verifies that documents indexed in one session are visible in the next,
    regardless of the embedding model passed to the constructor.
    """
    # Session 1: Index a document
    with patch("clarion.knowledge.OllamaEmbeddingFunction", return_value=MockEmbeddingFunction()):
        store1 = VectorStore(persist_directory=mock_chroma, embedding_model="nomic-embed-text")
        store1.ef = MockEmbeddingFunction()
        store1.index_document("persistent_doc.md", "This is content that should survive.")
        
        # Verify it exists in store1
        docs1 = store1.list_indexed_documents()
        assert len(docs1) == 1
        assert docs1[0]["name"] == "persistent_doc.md"

    # Session 2: Re-initialize store (simulate restart) with DIFFERENT or NO model
    # It should still find the document because we enforced a stable collection name
    with patch("clarion.knowledge.OllamaEmbeddingFunction", return_value=MockEmbeddingFunction()):
        # Passing None for embedding model, simulating startup before model selection
        store2 = VectorStore(persist_directory=mock_chroma, embedding_model=None)
        
        docs2 = store2.list_indexed_documents()
        assert len(docs2) == 1
        assert docs2[0]["name"] == "persistent_doc.md"
        print("Success: Document persisted across re-initialization.")

# --- TEST 2: Retrieval Statistics ---
def test_retrieval_stats(vector_store):
    """
    Verifies that get_relevant_kb_content returns accurate chunk hit counts.
    """
    # Index two documents
    vector_store.index_document("doc_A.md", "Content for doc A. " * 10) # Enough for 1 chunk
    vector_store.index_document("doc_B.md", "Content for doc B. " * 10) 
    
    # Mock the query result from Chroma
    # We simulate finding 2 chunks from A and 1 from B
    mock_results = {
        "documents": [["Chunk A1", "Chunk A2", "Chunk B1"]],
        "metadatas": [[
            {"source": "doc_A.md"},
            {"source": "doc_A.md"},
            {"source": "doc_B.md"}
        ]]
    }
    vector_store.kb_collection.query = MagicMock(return_value=mock_results)
    
    text, stats = vector_store.get_relevant_kb_content("query", n_results=3)
    
    assert "Chunk A1" in text
    assert stats["doc_A.md"] == 2
    assert stats["doc_B.md"] == 1
    print(f"Success: Retrieved stats: {stats}")

# --- TEST 3: Pipeline Metadata Footer ---
@pytest.mark.asyncio
async def test_pipeline_metadata_footer():
    """
    Verifies that the generation pipeline appends the correctly formatted footer
    including specific vector DB stats.
    """
    # Mock Provider
    mock_provider = AsyncMock()
    mock_provider.model_name = "test-model"
    # Mock generate_json return
    mock_provider.generate_json.return_value = FlexDoc(content="Generated content.", thought_process="Thinking...")
    
    pipeline = DirectPipeline(provider=mock_provider)
    
    # Mock VectorStore behavior inside pipeline
    # We need to mock get_vector_store to return our mock store
    mock_vs = MagicMock()
    mock_vs.get_relevant_kb_content.return_value = (
        "Relevent context", 
        {"source_A.pdf": 3, "source_B.md": 1} # Mock retrieval stats
    )
    
    with patch("clarion.knowledge.get_vector_store", return_value=mock_vs):
        # Run pipeline
        result = await pipeline.run(
            input_path="dummy.txt", 
            input_text_full="Input text",
            instruction_config=MagicMock(),
            use_rag=True, 
            selected_kb_ids=["source_A.pdf", "source_B.md"]
        )
        
        content = result.final_doc.content
        print(f"Final Content:\n{content}")
        
        # Verify Footer Elements
        assert "**Generation Metadata**" in content
        assert "Model**: test-model" in content
        assert "**Vector Context Used**:" in content
        assert "source_A.pdf (3 chunks)" in content
        assert "source_B.md (1 chunks)" in content
        print("Success: Metadata footer contains accurate RAG stats.")

if __name__ == "__main__":
    # verification manual run
    # pytest.main([__file__])
    pass
