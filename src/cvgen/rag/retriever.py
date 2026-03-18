"""Document retrieval from Qdrant vector store."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A document retrieved from the RAG system."""

    content: str
    score: float
    metadata: dict[str, Any]
    source: str


class RAGRetriever:
    """Retrieves documents from a Qdrant vector store.

    Uses the same embedding approach as RAGIndexer for consistency.
    """

    def __init__(
        self,
        collection_name: str = "cvgen_qpanda3",
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "nomic-embed-text",
        top_k: int = 5,
    ) -> None:
        """Initialize the RAG retriever.

        Args:
            collection_name: Name of the Qdrant collection.
            qdrant_url: URL of the Qdrant server.
            embedding_model: Name of the embedding model to use.
            top_k: Number of results to retrieve.
        """
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self.embedding_model = embedding_model
        self.top_k = top_k
        self._embeddings_cache: dict[str, list[float]] = {}
        self._vector_size: int | None = None

    def _check_qdrant_health(self) -> bool:
        """Check if Qdrant server is available.

        Returns:
            True if Qdrant is healthy, False otherwise.
        """
        try:
            response = requests.get(f"{self.qdrant_url}/health", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            return False

    def _get_embeddings(self, texts: list[str]) -> list[list[float]] | None:
        """Get embeddings for texts using Ollama with TF-IDF fallback.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors or None if failed.
        """
        # Try Ollama first
        ollama_embeddings = self._get_ollama_embeddings(texts)
        if ollama_embeddings:
            return ollama_embeddings

        # Fallback to TF-IDF based embeddings
        logger.info("Ollama unavailable, using TF-IDF embeddings")
        return self._get_tfidf_embeddings(texts)

    def _get_ollama_embeddings(
        self, texts: list[str]
    ) -> list[list[float]] | None:
        """Get embeddings from Ollama.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embeddings or None if Ollama is unavailable.
        """
        try:
            embeddings = []

            for text in texts:
                # Check cache first
                if text in self._embeddings_cache:
                    embeddings.append(self._embeddings_cache[text])
                    continue

                response = requests.post(
                    "http://localhost:11434/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": text,
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    embedding = response.json().get("embedding", [])
                    if embedding:
                        self._embeddings_cache[text] = embedding
                        embeddings.append(embedding)
                    else:
                        return None
                else:
                    logger.warning(f"Ollama request failed: {response.status_code}")
                    return None

            if embeddings and len(embeddings) == len(texts):
                if embeddings:
                    self._vector_size = len(embeddings[0])
                return embeddings

            return None

        except requests.exceptions.ConnectionError:
            logger.debug("Ollama connection failed")
            return None
        except Exception as e:
            logger.warning(f"Error getting Ollama embeddings: {e}")
            return None

    def _get_tfidf_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Create simple TF-IDF based embeddings as fallback.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        # Get all unique words from all texts
        all_words: set[str] = set()

        for text in texts:
            words = re.findall(r"\b\w+\b", text.lower())
            all_words.update(words)

        word_list = sorted(list(all_words))
        embeddings = []

        for text in texts:
            words = re.findall(r"\b\w+\b", text.lower())
            word_counts = {}

            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1

            # Create TF vector
            embedding = []
            for word in word_list:
                count = word_counts.get(word, 0)
                embedding.append(float(count) / max(len(words), 1))

            embeddings.append(embedding)

        self._vector_size = len(embeddings[0]) if embeddings else 768

        return embeddings

    def retrieve(self, query: str) -> list[RetrievalResult]:
        """Retrieve documents matching a query.

        Args:
            query: Query string.

        Returns:
            List of RetrievalResult objects sorted by relevance.
        """
        if not self._check_qdrant_health():
            logger.error("Qdrant server is not available")
            return []

        try:
            # Get query embedding
            embeddings = self._get_embeddings([query])
            if not embeddings:
                logger.error("Failed to get query embedding")
                return []

            query_vector = embeddings[0]

            # Search in Qdrant
            response = requests.post(
                f"{self.qdrant_url}/collections/{self.collection_name}/points/search",
                json={
                    "vector": query_vector,
                    "limit": self.top_k,
                    "with_payload": True,
                },
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(
                    f"Search failed: {response.status_code} - {response.text}"
                )
                return []

            results = response.json().get("result", [])
            retrieval_results = []

            for result in results:
                payload = result.get("payload", {})
                retrieval_result = RetrievalResult(
                    content=payload.get("content", ""),
                    score=float(result.get("score", 0.0)),
                    metadata=payload.get("metadata", {}),
                    source=payload.get("source", ""),
                )
                retrieval_results.append(retrieval_result)

            logger.debug(f"Retrieved {len(retrieval_results)} documents for query")
            return retrieval_results

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    def build_context(self, query: str, max_tokens: int = 2000) -> str:
        """Build a context string from retrieved documents.

        Concatenates retrieved documents up to max_tokens.

        Args:
            query: Query string.
            max_tokens: Maximum number of characters in context.

        Returns:
            Context string for use in LLM prompts.
        """
        results = self.retrieve(query)

        if not results:
            return "No relevant documents found."

        context_parts = []
        total_length = 0

        for result in results:
            doc_text = f"Source: {result.source}\n\n{result.content}\n\n---\n\n"

            if total_length + len(doc_text) > max_tokens:
                # Try to fit a truncated version
                remaining = max_tokens - total_length
                if remaining > 100:  # Only add if we have meaningful space
                    doc_text = (
                        f"Source: {result.source}\n\n"
                        f"{result.content[:remaining - 30]}\n\n...[truncated]\n\n"
                    )
                    context_parts.append(doc_text)
                break
            else:
                context_parts.append(doc_text)
                total_length += len(doc_text)

        if not context_parts:
            return "No relevant documents found."

        return "".join(context_parts)
