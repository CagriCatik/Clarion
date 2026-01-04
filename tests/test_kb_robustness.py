import pytest
from unittest.mock import MagicMock, patch
import httpx
from clarion.knowledge import OllamaEmbeddingFunction, VectorStore

class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise httpx.HTTPStatusError("Mock Error", request=None, response=self)

def test_ollama_embedding_success():
    """Test standard successful embedding call."""
    embedder = OllamaEmbeddingFunction(model_name="test-model")
    
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MockResponse({"embedding": [0.1, 0.2, 0.3]}, 200)
        
        embeddings = embedder(["test text"])
        
        assert len(embeddings) == 1
        # Convert to list to avoid numpy ambiguity
        assert list(embeddings[0]) == [0.1, 0.2, 0.3]
        mock_post.assert_called_once()

def test_ollama_embedding_retry_truncation():
    """
    Test that the embedding function retries with truncated text 
    when the initial call fails (e.g., 500 error).
    """
    embedder = OllamaEmbeddingFunction(model_name="test-model")
    
    # Create a long string that would theoretically cause failure
    long_text = "A" * 5000 
    
    with patch("httpx.Client.post") as mock_post:
        # Define side effects: First call fails (500), second call succeeds (200)
        mock_post.side_effect = [
            httpx.HTTPStatusError("500 Internal Server Error", request=None, response=MockResponse({}, 500)),
            MockResponse({"embedding": [0.9, 0.9, 0.9]}, 200)
        ]
        
        embeddings = embedder([long_text])
        
        assert len(embeddings) == 1
        # Convert to list to avoid numpy ambiguity if mock returns numpy
        assert list(embeddings[0]) == [0.9, 0.9, 0.9]
        
        # Verify it was called twice
        assert mock_post.call_count == 2
        
        # Verify first call used full text
        args1, kwargs1 = mock_post.call_args_list[0]
        assert kwargs1['json']['prompt'] == long_text
        
        # Verify second call used truncated text
        args2, kwargs2 = mock_post.call_args_list[1]
        assert len(kwargs2['json']['prompt']) == 1500 # standard limit
        assert kwargs2['json']['prompt'] == long_text[:1500]

def test_vector_store_kb_methods():
    """Test the KB integration methods in VectorStore."""
    # Mock chroma client to avoid actual DB writes
    with patch("chromadb.PersistentClient") as mock_client:
        mock_collection = MagicMock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        
        # Setup getting metadata for list_indexed_documents
        mock_collection.get.return_value = {
            "metadatas": [
                {"source": "doc1.txt", "type": "document", "indexed_at": "2024-01-01"},
                {"source": "doc1.txt", "type": "document", "indexed_at": "2024-01-01"}, # duplicate chunk
                {"source": "doc2.md", "type": "document", "indexed_at": "2024-01-02"}
            ]
        }
        
        vs = VectorStore(embedding_model="default")
        
        # Test 1: List Documents (should assume unique sources)
        docs = vs.list_indexed_documents()
        assert len(docs) == 2
        names = sorted([d['name'] for d in docs])
        assert names == ["doc1.txt", "doc2.md"]
        
        # Test 2: Index Document
        vs.index_document("new_doc.txt", "Paragraph 1.\n\nParagraph 2.")
        
        # Should upsert headers
        mock_collection.upsert.assert_called()
        call_kwargs = mock_collection.upsert.call_args[1]
        assert len(call_kwargs['documents']) == 2 # 2 paragraphs
        assert call_kwargs['metadatas'][0]['source'] == "new_doc.txt"

