"""API routes for LLM quantum agent and RAG endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cvgen.agents.llm_quantum_agent import LLMQuantumAgent
from cvgen.rag.indexer import RAGIndexer
from cvgen.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])
rag_router = APIRouter(prefix="/rag", tags=["rag"])


# --- Request/Response Models ---


class QuantumAskRequest(BaseModel):
    """Request for LLM quantum code generation."""

    question: str = Field(..., description="Natural language quantum computing task")
    backend: str = Field(default="simulator", description="Quantum backend to use")
    model: str = Field(default="qwen2.5:32b", description="LLM model to use")
    use_rag: bool = Field(default=True, description="Use RAG for documentation context")


class QuantumAskResponse(BaseModel):
    """Response from LLM quantum code generation."""

    success: bool
    generated_code: str
    result: dict | None = None
    interpretation: str
    model: str
    retries: int = 0
    rag_context_used: bool = False


class RAGStatusResponse(BaseModel):
    """Status of the RAG system."""

    indexed_documents: int = 0
    collection_exists: bool = False
    qdrant_connected: bool = False


class RAGIndexRequest(BaseModel):
    """Request to index documents."""

    docs_path: str = Field(..., description="Path to documentation directory")


class RAGIndexResponse(BaseModel):
    """Response from indexing operation."""

    success: bool
    documents_indexed: int
    message: str


# --- Quantum Ask Endpoints ---


@router.post("/quantum-ask", response_model=QuantumAskResponse)
async def run_quantum_ask(req: QuantumAskRequest) -> QuantumAskResponse:
    """Generate and execute QPanda3 code based on natural language question.

    Generates QPanda3 quantum circuit code using an LLM, optionally
    augmented with RAG-retrieved documentation.

    Args:
        req: QuantumAskRequest with the task description.

    Returns:
        QuantumAskResponse with generated code and execution results.
    """
    try:
        # Import here to avoid circular dependency
        from cvgen.api.app import get_backend

        backend = get_backend(req.backend)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid backend '{req.backend}': {str(e)}",
        )

    # Initialize RAG retriever if requested
    rag_retriever = None
    if req.use_rag:
        try:
            rag_retriever = RAGRetriever(model=req.model)
        except Exception as e:
            logger.warning(f"Failed to initialize RAG retriever: {e}")

    # Create and run agent
    try:
        agent = LLMQuantumAgent(
            backend=backend,
            model=req.model,
            rag_retriever=rag_retriever,
            max_code_retries=3,
        )

        result = agent.run(req.question)

        # Convert CircuitResult to dict
        result_dict = None
        if result.execution_result:
            result_dict = {
                "counts": result.execution_result.counts,
                "shots": result.execution_result.shots,
                "probabilities": result.execution_result.probabilities,
                "most_likely": result.execution_result.most_likely(),
                "metadata": result.execution_result.metadata,
            }

        return QuantumAskResponse(
            success=result.success,
            generated_code=result.generated_code,
            result=result_dict,
            interpretation=result.interpretation,
            model=result.model_used,
            retries=result.retries,
            rag_context_used=result.rag_context_used,
        )

    except Exception as e:
        logger.error(f"Quantum ask failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Quantum ask execution failed: {str(e)}",
        )


# --- RAG Endpoints ---


@rag_router.get("/status", response_model=RAGStatusResponse)
async def get_rag_status() -> RAGStatusResponse:
    """Get the status of the RAG system.

    Returns information about indexed documents and system health.

    Returns:
        RAGStatusResponse with system status.
    """
    try:
        retriever = RAGRetriever()

        # Check Qdrant connection
        qdrant_connected = retriever._check_qdrant_health()

        # Try to get collection info
        collection_exists = False
        indexed_documents = 0

        if qdrant_connected:
            import requests

            try:
                response = requests.get(
                    f"{retriever.qdrant_url}/collections/{retriever.collection_name}",
                    timeout=2,
                )
                if response.status_code == 200:
                    collection_exists = True
                    data = response.json()
                    # Get point count from collection stats
                    if "result" in data:
                        indexed_documents = data["result"].get("points_count", 0)
            except Exception as e:
                logger.warning(f"Failed to get collection info: {e}")

        return RAGStatusResponse(
            indexed_documents=indexed_documents,
            collection_exists=collection_exists,
            qdrant_connected=qdrant_connected,
        )

    except Exception as e:
        logger.error(f"Failed to get RAG status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get RAG status: {str(e)}",
        )


@rag_router.post("/index", response_model=RAGIndexResponse)
async def index_documents(req: RAGIndexRequest) -> RAGIndexResponse:
    """Index QPanda3 documentation from a directory.

    Reads .md, .txt, .py, and .rst files from the specified directory
    and indexes them in Qdrant for RAG retrieval.

    Args:
        req: RAGIndexRequest with the documentation path.

    Returns:
        RAGIndexResponse with indexing results.
    """
    try:
        indexer = RAGIndexer()

        # Index documents
        num_indexed = indexer.index_qpanda3_docs(req.docs_path)

        if num_indexed > 0:
            return RAGIndexResponse(
                success=True,
                documents_indexed=num_indexed,
                message=f"Successfully indexed {num_indexed} documents",
            )
        else:
            return RAGIndexResponse(
                success=False,
                documents_indexed=0,
                message=f"Failed to index documents from {req.docs_path}",
            )

    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Indexing failed: {str(e)}",
        )
