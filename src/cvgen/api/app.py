"""CVGen FastAPI application — Quantum Computing for every device."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from cvgen import __version__
from cvgen.api.models import HealthResponse
from cvgen.api.routes import agents, backends, circuits, jobs
from cvgen.backends.base import QuantumBackend
from cvgen.backends.simulator import StateVectorSimulator

# Global backend registry
backend_registry: dict[str, QuantumBackend] = {}


def _init_backends() -> None:
    """Initialize available quantum backends."""
    # Built-in simulator is always available
    backend_registry["simulator"] = StateVectorSimulator()

    # Try to load Origin Pilot
    try:
        from cvgen.backends.origin_pilot import OriginPilotBackend
        backend_registry["origin_pilot"] = OriginPilotBackend()
    except Exception:
        pass

    # Try to load Qiskit
    try:
        from cvgen.backends.qiskit_backend import QiskitBackend
        backend_registry["qiskit"] = QiskitBackend()
    except Exception:
        pass

    # Try to load IBM Cloud
    try:
        from cvgen.backends.ibm_cloud import IBMCloudBackend
        token = os.environ.get("IBM_QUANTUM_TOKEN")
        if token:
            backend_registry["ibm_cloud"] = IBMCloudBackend(token=token)
    except Exception:
        pass

    # Try to load AWS Braket
    try:
        from cvgen.backends.aws_braket import AWSBraketBackend
        if os.environ.get("AWS_DEFAULT_REGION"):
            backend_registry["aws_braket"] = AWSBraketBackend()
    except Exception:
        pass

    # Try to load Azure Quantum
    try:
        from cvgen.backends.azure_quantum import AzureQuantumBackend
        resource_id = os.environ.get("AZURE_QUANTUM_RESOURCE_ID")
        if resource_id:
            backend_registry["azure_quantum"] = AzureQuantumBackend(resource_id=resource_id)
    except Exception:
        pass


def get_backend(name: str) -> QuantumBackend:
    """Get a backend by name, or raise 404."""
    backend = backend_registry.get(name)
    if backend is None:
        available = list(backend_registry.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Backend '{name}' not found. Available: {available}",
        )
    return backend


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown."""
    _init_backends()
    yield
    backend_registry.clear()


app = FastAPI(
    title="CVGen Quantum API",
    description="Quantum Computing accessible from any device — execute circuits, run quantum agents, and leverage real quantum hardware.",
    version=__version__,
    lifespan=lifespan,
)

# CORS — allow all origins for universal device access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(circuits.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(backends.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")

# Serve web UI static files
_web_static = Path(__file__).resolve().parent.parent / "web" / "static"
if _web_static.is_dir():
    app.mount("/static", StaticFiles(directory=str(_web_static)), name="static")

    from fastapi.responses import FileResponse

    @app.get("/", include_in_schema=False)
    async def serve_ui() -> FileResponse:
        return FileResponse(str(_web_static / "index.html"))


@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        backends_available=len(backend_registry),
    )
