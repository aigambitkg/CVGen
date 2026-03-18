"""Document indexing and retrieval using Qdrant vector store."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """A document to be indexed in the RAG system."""

    content: str
    metadata: dict[str, Any]
    source: str


class DocumentChunker:
    """Splits documents into chunks using sliding window approach."""

    def __init__(self) -> None:
        """Initialize the document chunker."""
        pass

    def chunk(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[str]:
        """Split text into overlapping chunks using a simple sliding window.

        Args:
            text: Text to chunk.
            chunk_size: Maximum size of each chunk.
            overlap: Number of characters to overlap between chunks.

        Returns:
            List of text chunks.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        if not text.strip():
            return []

        chunks = []
        start = 0

        while start < len(text):
            # Get the end position for this chunk
            end = min(start + chunk_size, len(text))

            # Extract chunk
            chunk = text[start:end]

            # Only add non-empty chunks
            if chunk.strip():
                chunks.append(chunk)

            # If we've reached the end, break
            if end >= len(text):
                break

            # Move start position by (chunk_size - overlap)
            start = end - overlap

        return chunks if chunks else []


class RAGIndexer:
    """Indexes documents in a Qdrant vector store for retrieval.

    Uses Ollama for embeddings with a fallback TF-IDF implementation.
    """

    def __init__(
        self,
        collection_name: str = "cvgen_qpanda3",
        qdrant_url: str = "http://localhost:6333",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        """Initialize the RAG indexer.

        Args:
            collection_name: Name of the Qdrant collection.
            qdrant_url: URL of the Qdrant server.
            embedding_model: Name of the embedding model to use.
        """
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self.embedding_model = embedding_model
        self.chunker = DocumentChunker()
        self._vector_size: int | None = None
        self._embeddings_cache: dict[str, list[float]] = {}

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

    def _create_collection_if_not_exists(self) -> bool:
        """Create the collection if it doesn't exist.

        Returns:
            True if successful, False otherwise.
        """
        if not self._check_qdrant_health():
            return False

        try:
            # Check if collection exists
            response = requests.get(
                f"{self.qdrant_url}/collections/{self.collection_name}",
                timeout=5,
            )

            if response.status_code == 200:
                logger.info(f"Collection '{self.collection_name}' already exists")
                return True

            # Create new collection
            vector_size = self._vector_size or 768  # Default embedding size

            payload = {
                "vectors": {
                    "size": vector_size,
                    "distance": "Cosine",
                }
            }

            response = requests.put(
                f"{self.qdrant_url}/collections/{self.collection_name}",
                json=payload,
                timeout=5,
            )

            if response.status_code in [200, 201]:
                logger.info(f"Collection '{self.collection_name}' created successfully")
                return True
            else:
                logger.error(
                    f"Failed to create collection: {response.status_code} "
                    f"- {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return False

    def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for texts using Ollama with TF-IDF fallback.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        # Try Ollama first
        ollama_embeddings = self._get_ollama_embeddings(texts)
        if ollama_embeddings:
            return ollama_embeddings

        # Fallback to TF-IDF based embeddings
        logger.info("Ollama unavailable, using TF-IDF embeddings")
        return self._get_tfidf_embeddings(texts)

    def _get_ollama_embeddings(self, texts: list[str]) -> list[list[float]] | None:
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
        # Simple TF-IDF: collect all words, create sparse vectors
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

    def index_documents(self, documents: list[Document]) -> int:
        """Index documents in Qdrant.

        Args:
            documents: List of documents to index.

        Returns:
            Number of documents indexed.
        """
        if not documents:
            logger.warning("No documents to index")
            return 0

        if not self._check_qdrant_health():
            logger.error("Qdrant server is not available")
            return 0

        if not self._create_collection_if_not_exists():
            logger.error("Failed to create/access collection")
            return 0

        try:
            # Extract content and get embeddings
            contents = [doc.content for doc in documents]
            embeddings = self._get_embeddings(contents)

            if not embeddings or len(embeddings) != len(documents):
                logger.error("Failed to get embeddings for all documents")
                return 0

            # Prepare points for Qdrant
            points = []

            for idx, (doc, embedding) in enumerate(zip(documents, embeddings)):
                point = {
                    "id": idx + 1,
                    "vector": embedding,
                    "payload": {
                        "content": doc.content,
                        "source": doc.source,
                        "metadata": doc.metadata,
                    },
                }
                points.append(point)

            # Upload points to Qdrant
            response = requests.put(
                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                json={"points": points},
                timeout=30,
            )

            if response.status_code in [200, 201]:
                logger.info(f"Indexed {len(documents)} documents successfully")
                return len(documents)
            else:
                logger.error(
                    f"Failed to index documents: {response.status_code} "
                    f"- {response.text}"
                )
                return 0

        except Exception as e:
            logger.error(f"Error indexing documents: {e}")
            return 0

    def index_qpanda3_docs(self, docs_dir: str) -> int:
        """Index QPanda3 documentation files from a directory.

        Indexes .md, .txt, .py, and .rst files.

        Args:
            docs_dir: Path to the directory containing documentation.

        Returns:
            Number of documents indexed.
        """
        docs_path = Path(docs_dir)

        if not docs_path.is_dir():
            logger.error(f"Directory not found: {docs_dir}")
            return 0

        documents = []
        file_extensions = {".md", ".txt", ".py", ".rst"}

        for file_path in docs_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in file_extensions:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")

                    if not content.strip():
                        continue

                    doc = Document(
                        content=content,
                        source=str(file_path.relative_to(docs_path)),
                        metadata={
                            "file_type": file_path.suffix,
                            "file_name": file_path.name,
                        },
                    )
                    documents.append(doc)

                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")
                    continue

        if not documents:
            logger.warning(f"No documents found in {docs_dir}")
            return 0

        # Chunk documents for better retrieval
        chunked_documents = []

        for doc in documents:
            chunks = self.chunker.chunk(doc.content)

            for chunk_idx, chunk in enumerate(chunks):
                chunked_doc = Document(
                    content=chunk,
                    source=doc.source,
                    metadata={
                        **doc.metadata,
                        "chunk_index": chunk_idx,
                        "total_chunks": len(chunks),
                    },
                )
                chunked_documents.append(chunked_doc)

        logger.info(f"Created {len(chunked_documents)} chunks from {len(documents)} files")

        return self.index_documents(chunked_documents)
