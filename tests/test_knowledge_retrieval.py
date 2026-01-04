import pytest
import shutil
import os
from unittest.mock import patch
from clarion.knowledge import VectorStore
# Try to inherit from actual base class if available, else just match signature
try:
    from chromadb.utils import embedding_functions
    BaseEF = embedding_functions.EmbeddingFunction
except ImportError:
    BaseEF = object

@pytest.fixture
def clean_db(tmp_path):
    db_dir = tmp_path / "test_db"
    yield str(db_dir)
    # Cleanup on Windows often fails due to open handles to SQLite
    # We ignore errors here as it doesn't affect test validity
    if db_dir.exists():
        shutil.rmtree(db_dir, ignore_errors=True)

class MockEF(BaseEF):
    def __call__(self, input):
        # Explicit 'input' name triggers chromadb validation correctly
        return [[0.1]*1024]*len(input)

def test_vector_store_indexing_and_retrieval(clean_db):
    # Use patch to return our proper MockEF instance
    with patch('clarion.knowledge.OllamaEmbeddingFunction') as mock_ef_class:
        mock_ef_class.return_value = MockEF()
        
        vs = VectorStore(persist_directory=clean_db, embedding_model="mock")
        
        # 1. Test Indexing
        guidelines = "# G1\nRule 1"
        vs.index_guidelines(guidelines)
        assert vs.guidelines_collection.count() == 1
        
        # 2. Test Idempotency (Hash Check) village
        # Calling index again with same content should NOT increase count or re-upsert
        # We can verify by checking if the hash was set
        assert vs._last_guideline_hash is not None
        initial_hash = vs._last_guideline_hash
        vs.index_guidelines(guidelines)
        assert vs._last_guideline_hash == initial_hash
        
        # 3. Test Retrieval
        results = vs.get_relevant_guidelines("query", n_results=1)
        assert len(results) > 0

def test_terminology_management(clean_db):
    with patch('clarion.knowledge.OllamaEmbeddingFunction') as mock_ef_class:
        mock_ef_class.return_value = MockEF()
        vs = VectorStore(persist_directory=clean_db, embedding_model="mock")
        
        # Add Term
        vs.add_terminology("SaaS", "Software as a Service")
        assert vs.terminology_collection.count() == 1
        
        # Retrieve Term
        related = vs.get_related_terminology("SaaS", n_results=1)
        assert "SaaS" in related

def test_persistence_across_restarts(clean_db):
    # Simulate server restart by creating new VectorStore on same dir
    with patch('clarion.knowledge.OllamaEmbeddingFunction') as mock_ef_class:
        mock_ef_class.return_value = MockEF()
        
        # Instance 1
        vs1 = VectorStore(persist_directory=clean_db, embedding_model="mock")
        vs1.index_guidelines("# Rule 1\nPersist me")
        
        # Instance 2 (Simulated restart)
        vs2 = VectorStore(persist_directory=clean_db, embedding_model="mock")
        # Should verify that collection still has data
        assert vs2.guidelines_collection.count() == 1
        
        # Check retrieval works in new instance
        res = vs2.get_relevant_guidelines("query")
        assert "Persist me" in res

def test_guideline_chunking(tmp_path):
    db_dir = tmp_path / "chunk_db"
    vs = VectorStore(persist_directory=str(db_dir))
    
    guidelines = "# Rule 1\nContent 1\n\n# Rule 2\nContent 2"
    vs.index_guidelines(guidelines)
    assert vs.guidelines_collection.count() >= 2
    
def test_empty_retrieval(clean_db):
    with patch('clarion.knowledge.OllamaEmbeddingFunction') as mock_ef_class:
        mock_ef_class.return_value = MockEF()
        vs = VectorStore(persist_directory=clean_db, embedding_model="mock")
        
        # Empty DB, should handle safely
        res = vs.get_relevant_guidelines("query")
        assert res == ""
