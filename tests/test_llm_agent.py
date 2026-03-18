"""Tests for LLM quantum agent and RAG system."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from cvgen.agents.llm_quantum_agent import LLMAgentResult, LLMQuantumAgent
from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.types import CircuitResult
from cvgen.rag.indexer import Document, DocumentChunker, RAGIndexer
from cvgen.rag.retriever import RAGRetriever, RetrievalResult


# --- Document Chunker Tests ---


class TestDocumentChunker:
    """Tests for the DocumentChunker class."""

    def test_chunk_basic(self) -> None:
        """Chunker should split text into chunks."""
        chunker = DocumentChunker()
        text = "Hello world. " * 100
        chunks = chunker.chunk(text, chunk_size=50, overlap=10)

        assert len(chunks) > 1
        assert all(len(c) > 0 for c in chunks)

    def test_chunk_with_overlap(self) -> None:
        """Chunks should have overlap."""
        chunker = DocumentChunker()
        text = "The quick brown fox jumps over the lazy dog. " * 50
        chunks = chunker.chunk(text, chunk_size=100, overlap=20)

        if len(chunks) > 1:
            # Check that adjacent chunks overlap
            for i in range(len(chunks) - 1):
                chunk1 = chunks[i]
                chunk2 = chunks[i + 1]
                # There should be some overlap in content
                overlap_text = chunk1[-20:]
                assert overlap_text in chunk2 or len(chunks) <= 2

    def test_chunk_empty_text(self) -> None:
        """Chunker should handle empty text."""
        chunker = DocumentChunker()
        chunks = chunker.chunk("", chunk_size=100, overlap=10)
        assert chunks == []

    def test_chunk_invalid_sizes(self) -> None:
        """Chunker should validate sizes."""
        chunker = DocumentChunker()

        with pytest.raises(ValueError):
            chunker.chunk("text", chunk_size=-1)

        with pytest.raises(ValueError):
            chunker.chunk("text", overlap=-1)

        with pytest.raises(ValueError):
            chunker.chunk("text", chunk_size=10, overlap=20)

    def test_chunk_single_chunk(self) -> None:
        """Small text should result in single chunk."""
        chunker = DocumentChunker()
        text = "Hello world"
        chunks = chunker.chunk(text, chunk_size=1000)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_recursive_splitting(self) -> None:
        """Chunker should use recursive splitting with multiple separators."""
        chunker = DocumentChunker()
        text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3. Sentence 2."
        chunks = chunker.chunk(text, chunk_size=50, overlap=5)

        assert len(chunks) > 0
        assert all(len(c.strip()) > 0 for c in chunks)


# --- RAG Indexer Tests ---


class TestRAGIndexer:
    """Tests for the RAG indexer."""

    @pytest.fixture
    def indexer(self) -> RAGIndexer:
        """Create a RAG indexer."""
        return RAGIndexer()

    def test_indexer_initialization(self, indexer: RAGIndexer) -> None:
        """Indexer should initialize properly."""
        assert indexer.collection_name == "cvgen_qpanda3"
        assert indexer.qdrant_url == "http://localhost:6333"
        assert indexer.embedding_model == "nomic-embed-text"
        assert isinstance(indexer.chunker, DocumentChunker)

    def test_tfidf_embeddings(self, indexer: RAGIndexer) -> None:
        """Indexer should generate TF-IDF embeddings as fallback."""
        texts = [
            "Quantum computing is fascinating",
            "QPanda3 is a quantum library",
        ]
        embeddings = indexer._get_tfidf_embeddings(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) > 0
        assert len(embeddings[0]) == len(embeddings[1])

    def test_tfidf_embeddings_similarity(self, indexer: RAGIndexer) -> None:
        """Similar texts should have similar embeddings."""
        texts = [
            "quantum computing with QPanda3",
            "quantum computing library",
            "something completely different",
        ]
        embeddings = indexer._get_tfidf_embeddings(texts)

        # Calculate simple dot product similarity
        def dot_product(a: list[float], b: list[float]) -> float:
            return sum(x * y for x, y in zip(a, b))

        sim_01 = dot_product(embeddings[0], embeddings[1])
        sim_02 = dot_product(embeddings[0], embeddings[2])

        # First two should be more similar than first and third
        assert sim_01 > sim_02

    @patch("requests.get")
    def test_qdrant_health_check_failure(self, mock_get: Mock, indexer: RAGIndexer) -> None:
        """Health check should return False on connection error."""
        mock_get.side_effect = Exception("Connection failed")
        assert indexer._check_qdrant_health() is False

    @patch("requests.get")
    def test_qdrant_health_check_success(self, mock_get: Mock, indexer: RAGIndexer) -> None:
        """Health check should return True on 200 response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert indexer._check_qdrant_health() is True

    def test_create_collection_if_not_exists_new(self, indexer: RAGIndexer) -> None:
        """Should create collection if it doesn't exist."""
        with patch.object(indexer, "_check_qdrant_health", return_value=True):
            with patch("cvgen.rag.indexer.requests.get") as mock_get:
                with patch("cvgen.rag.indexer.requests.put") as mock_put:
                    # First call (check) returns 404, second call (create) returns 201
                    mock_response = Mock()
                    mock_response.status_code = 404
                    mock_get.return_value = mock_response

                    mock_create = Mock()
                    mock_create.status_code = 201
                    mock_put.return_value = mock_create

                    indexer._vector_size = 768
                    result = indexer._create_collection_if_not_exists()

                    assert result is True
                    assert mock_put.called

    @patch("cvgen.rag.indexer.requests.put")
    def test_index_documents_mock(self, mock_put: Mock, indexer: RAGIndexer) -> None:
        """Should index documents successfully."""
        # Mock Qdrant health check and collection creation
        with patch.object(indexer, "_check_qdrant_health", return_value=True):
            with patch.object(indexer, "_create_collection_if_not_exists", return_value=True):
                with patch.object(
                    indexer, "_get_embeddings", return_value=[[0.1, 0.2], [0.3, 0.4]]
                ):
                    # Mock the points upload
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_put.return_value = mock_response

                    docs = [
                        Document(
                            content="QPanda3 tutorial",
                            source="docs/tutorial.md",
                            metadata={"type": "tutorial"},
                        ),
                        Document(
                            content="QPanda3 API reference",
                            source="docs/api.md",
                            metadata={"type": "api"},
                        ),
                    ]

                    result = indexer.index_documents(docs)

                    assert result == 2

    def test_index_empty_documents(self, indexer: RAGIndexer) -> None:
        """Should handle empty document list."""
        result = indexer.index_documents([])
        assert result == 0


# --- RAG Retriever Tests ---


class TestRAGRetriever:
    """Tests for the RAG retriever."""

    @pytest.fixture
    def retriever(self) -> RAGRetriever:
        """Create a RAG retriever."""
        return RAGRetriever(top_k=5)

    def test_retriever_initialization(self, retriever: RAGRetriever) -> None:
        """Retriever should initialize properly."""
        assert retriever.collection_name == "cvgen_qpanda3"
        assert retriever.qdrant_url == "http://localhost:6333"
        assert retriever.embedding_model == "nomic-embed-text"
        assert retriever.top_k == 5

    def test_tfidf_embeddings(self, retriever: RAGRetriever) -> None:
        """Retriever should generate TF-IDF embeddings."""
        texts = ["quantum computing", "classical computing"]
        embeddings = retriever._get_tfidf_embeddings(texts)

        assert len(embeddings) == 2
        assert all(len(e) > 0 for e in embeddings)

    @patch("requests.get")
    def test_retrieve_no_qdrant(self, mock_get: Mock, retriever: RAGRetriever) -> None:
        """Retrieve should return empty list if Qdrant unavailable."""
        mock_get.side_effect = Exception("Connection failed")

        results = retriever.retrieve("quantum computing")

        assert results == []

    @patch("requests.post")
    def test_retrieve_with_results(self, mock_post: Mock, retriever: RAGRetriever) -> None:
        """Retrieve should return results from Qdrant."""
        with patch.object(retriever, "_check_qdrant_health", return_value=True):
            with patch.object(retriever, "_get_embeddings", return_value=[[0.1, 0.2, 0.3]]):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "result": [
                        {
                            "score": 0.95,
                            "payload": {
                                "content": "QPanda3 documentation",
                                "source": "docs.md",
                                "metadata": {"type": "doc"},
                            },
                        },
                        {
                            "score": 0.85,
                            "payload": {
                                "content": "Tutorial content",
                                "source": "tutorial.md",
                                "metadata": {"type": "tutorial"},
                            },
                        },
                    ]
                }
                mock_post.return_value = mock_response

                results = retriever.retrieve("quantum computing")

                assert len(results) == 2
                assert results[0].score == 0.95
                assert results[0].source == "docs.md"
                assert results[1].score == 0.85

    def test_build_context(self, retriever: RAGRetriever) -> None:
        """Build context should concatenate documents."""
        with patch.object(
            retriever,
            "retrieve",
            return_value=[
                RetrievalResult(
                    content="Content 1",
                    score=0.95,
                    metadata={},
                    source="doc1.md",
                ),
                RetrievalResult(
                    content="Content 2",
                    score=0.85,
                    metadata={},
                    source="doc2.md",
                ),
            ],
        ):
            context = retriever.build_context("query")

            assert "Content 1" in context
            assert "Content 2" in context
            assert "doc1.md" in context
            assert "doc2.md" in context

    def test_build_context_empty_results(self, retriever: RAGRetriever) -> None:
        """Build context should handle no results."""
        with patch.object(retriever, "retrieve", return_value=[]):
            context = retriever.build_context("query")

            assert "No relevant documents" in context

    def test_build_context_max_tokens(self, retriever: RAGRetriever) -> None:
        """Build context should respect max_tokens."""
        long_content = "x" * 5000

        with patch.object(
            retriever,
            "retrieve",
            return_value=[
                RetrievalResult(
                    content=long_content,
                    score=0.95,
                    metadata={},
                    source="doc1.md",
                ),
            ],
        ):
            context = retriever.build_context("query", max_tokens=500)

            assert len(context) <= 600  # Allow some margin


# --- LLM Quantum Agent Tests ---


class TestLLMQuantumAgent:
    """Tests for the LLM quantum agent."""

    @pytest.fixture
    def backend(self) -> StateVectorSimulator:
        """Create a simulator backend."""
        return StateVectorSimulator()

    @pytest.fixture
    def agent(self, backend: StateVectorSimulator) -> LLMQuantumAgent:
        """Create an LLM quantum agent."""
        return LLMQuantumAgent(backend=backend)

    def test_agent_initialization(self, agent: LLMQuantumAgent) -> None:
        """Agent should initialize properly."""
        assert agent.backend is not None
        assert agent.model == "qwen2.5:32b"
        assert agent.max_code_retries == 3
        assert agent.rag_retriever is None

    def test_extract_code_python_block(self, agent: LLMQuantumAgent) -> None:
        """Should extract code from ```python blocks."""
        response = """Here's the code:

```python
q = QProg()
qvm = CPUQVM()
result = qvm.run_with_configuration(q, [0], 1024)
```

That's all!
"""
        code = agent._extract_code(response)

        assert "QProg()" in code
        assert "CPUQVM()" in code
        assert len(code) > 0

    def test_extract_code_generic_block(self, agent: LLMQuantumAgent) -> None:
        """Should extract code from generic ``` blocks."""
        response = """Here's the code:

```
q = QProg()
qvm = CPUQVM()
```

Done!
"""
        code = agent._extract_code(response)

        assert "QProg()" in code
        assert len(code) > 0

    def test_extract_code_no_block(self, agent: LLMQuantumAgent) -> None:
        """Should return empty string if no code block found."""
        response = "Just some text without code blocks"
        code = agent._extract_code(response)

        assert code == ""

    def test_validate_code_valid(self, agent: LLMQuantumAgent) -> None:
        """Should accept valid code."""
        code = """
import numpy
q = QProg()
q.insert(H(0))
"""
        is_valid, error = agent._validate_code(code)

        assert is_valid is True
        assert error == ""

    def test_validate_code_syntax_error(self, agent: LLMQuantumAgent) -> None:
        """Should reject code with syntax errors."""
        code = "if this is not valid {"
        is_valid, error = agent._validate_code(code)

        assert is_valid is False
        assert "Syntax error" in error

    def test_validate_code_disallowed_import(self, agent: LLMQuantumAgent) -> None:
        """Should reject disallowed imports."""
        code = """
import requests
import os
"""
        is_valid, error = agent._validate_code(code)

        assert is_valid is False

    def test_validate_code_file_operations(self, agent: LLMQuantumAgent) -> None:
        """Should reject file operations."""
        code = "f = open('/tmp/file.txt', 'w')"
        is_valid, error = agent._validate_code(code)

        assert is_valid is False

    def test_validate_code_network_operations(self, agent: LLMQuantumAgent) -> None:
        """Should reject network operations."""
        code = "import requests\nrequests.get('http://example.com')"
        is_valid, error = agent._validate_code(code)

        assert is_valid is False

    def test_validate_code_empty(self, agent: LLMQuantumAgent) -> None:
        """Should reject empty code."""
        is_valid, error = agent._validate_code("")

        assert is_valid is False
        assert "empty" in error.lower()

    @patch("requests.post")
    def test_call_ollama_success(self, mock_post: Mock, agent: LLMQuantumAgent) -> None:
        """Should call Ollama successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Generated code here"}
        mock_post.return_value = mock_response

        result = agent._call_ollama("prompt")

        assert result == "Generated code here"
        assert mock_post.called

    @patch("requests.post")
    def test_call_ollama_connection_error(self, mock_post: Mock, agent: LLMQuantumAgent) -> None:
        """Should handle Ollama connection errors."""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError()

        result = agent._call_ollama("prompt")

        assert result == ""

    @patch("requests.post")
    def test_run_success(self, mock_post: Mock, agent: LLMQuantumAgent) -> None:
        """Agent should run successfully with valid code."""
        # Mock Ollama response with valid code
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": """Here's the QPanda3 code:

```python
q = QProg()
qvm = CPUQVM()
result = qvm.run_with_configuration(q, [0], 1024)
print(result)
```

This creates a simple quantum circuit.
"""
        }
        mock_post.return_value = mock_response

        result = agent.run("Create a simple quantum circuit")

        assert result.success is True
        assert "QProg()" in result.generated_code
        assert result.model_used == "qwen2.5:32b"
        assert result.retries == 0

    @patch("requests.post")
    def test_run_with_rag_context(self, mock_post: Mock, agent: LLMQuantumAgent) -> None:
        """Agent should use RAG context when available."""
        # Create agent with mock RAG retriever
        mock_retriever = MagicMock()
        mock_retriever.build_context.return_value = "RAG context about QPanda3"

        agent.rag_retriever = mock_retriever

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": """```python
q = QProg()
```"""
        }
        mock_post.return_value = mock_response

        result = agent.run("Create circuit")

        assert mock_retriever.build_context.called
        assert result.rag_context_used is True

    def test_build_prompt_with_rag(self, agent: LLMQuantumAgent) -> None:
        """Should include RAG context in prompt."""
        task = "Create a Hadamard gate"
        rag_context = "Documentation about Hadamard gates"

        prompt = agent._build_prompt(task, rag_context)

        assert task in prompt
        assert rag_context in prompt

    def test_build_prompt_without_rag(self, agent: LLMQuantumAgent) -> None:
        """Should work without RAG context."""
        task = "Create a quantum circuit"

        prompt = agent._build_prompt(task, "")

        assert task in prompt

    def test_build_retry_prompt(self, agent: LLMQuantumAgent) -> None:
        """Should build retry prompt with error feedback."""
        task = "Create circuit"
        previous_code = "invalid code here"

        prompt = agent._build_retry_prompt(task, previous_code)

        assert task in prompt
        assert previous_code in prompt
        assert "retry" in prompt.lower() or "corrected" in prompt.lower()


# --- API Tests (if we're testing with FastAPI client) ---


class TestQuantumAskAPI:
    """Tests for the quantum-ask API endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient
        from cvgen.api.app import app, backend_registry

        # Make sure simulator backend is available
        from cvgen.backends.simulator import StateVectorSimulator

        backend_registry["simulator"] = StateVectorSimulator()

        return TestClient(app)

    def test_quantum_ask_endpoint(self, client) -> None:
        """Endpoint should accept quantum ask requests."""
        with patch("cvgen.agents.llm_quantum_agent.LLMQuantumAgent.run") as mock_run:
            # Mock successful agent run
            mock_run.return_value = LLMAgentResult(
                success=True,
                generated_code="q = QProg()",
                execution_result=CircuitResult(counts={"0": 512, "1": 512}, shots=1024),
                interpretation="Test interpretation",
                retries=0,
                model_used="test_model",
                rag_context_used=False,
            )

            response = client.post(
                "/api/v1/agents/quantum-ask",
                json={
                    "question": "Create a quantum circuit",
                    "backend": "simulator",
                    "use_rag": False,
                },
            )

            # Debug: print response if it fails
            if response.status_code != 200:
                print(f"Response status: {response.status_code}")
                print(f"Response text: {response.text}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["generated_code"] == "q = QProg()"

    def test_quantum_ask_invalid_backend(self, client) -> None:
        """Endpoint should reject invalid backends."""
        response = client.post(
            "/api/v1/agents/quantum-ask",
            json={
                "question": "test",
                "backend": "nonexistent_backend",
                "use_rag": False,
            },
        )

        assert response.status_code == 400

    def test_rag_status_endpoint(self, client) -> None:
        """RAG status endpoint should be accessible."""
        with patch("cvgen.rag.retriever.RAGRetriever._check_qdrant_health") as mock_health:
            mock_health.return_value = True

            response = client.get("/api/v1/rag/status")

            assert response.status_code == 200
            data = response.json()
            assert "qdrant_connected" in data

    def test_rag_index_endpoint(self, client) -> None:
        """RAG index endpoint should accept indexing requests."""
        with patch("cvgen.rag.indexer.RAGIndexer.index_qpanda3_docs") as mock_index:
            mock_index.return_value = 10

            response = client.post(
                "/api/v1/rag/index",
                json={"docs_path": "/tmp/docs"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["documents_indexed"] == 10
