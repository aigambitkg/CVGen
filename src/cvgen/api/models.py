"""Pydantic models for the CVGen REST API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Circuit models ---


class GateRequest(BaseModel):
    """A single gate operation."""

    gate: str = Field(
        ..., description="Gate name: h, x, y, z, s, t, rx, ry, rz, cx, cz, swap, ccx, measure"
    )
    targets: list[int] = Field(..., description="Target qubit indices")
    params: list[float] = Field(
        default_factory=list, description="Gate parameters (e.g. rotation angle)"
    )


class CircuitRequest(BaseModel):
    """Request to execute a quantum circuit."""

    num_qubits: int = Field(..., ge=1, le=20, description="Number of qubits")
    gates: list[GateRequest] = Field(..., description="List of gate operations")
    shots: int = Field(default=1024, ge=1, le=100000, description="Number of measurement shots")
    backend: str = Field(default="simulator", description="Backend to use")
    return_statevector: bool = Field(default=False, description="Return full statevector")
    seed: int | None = Field(default=None, description="Random seed for reproducibility")


class CircuitResponse(BaseModel):
    """Response from circuit execution."""

    counts: dict[str, int]
    shots: int
    probabilities: dict[str, float]
    most_likely: str
    metadata: dict = Field(default_factory=dict)


# --- Agent models ---


class GroverRequest(BaseModel):
    """Request for Grover search."""

    num_qubits: int = Field(..., ge=2, le=12, description="Search space size (2^n states)")
    target_states: list[int] = Field(..., description="Target states to search for")
    shots: int = Field(default=1024, ge=1, le=100000)
    backend: str = Field(default="simulator")


class GroverResponse(BaseModel):
    """Response from Grover search."""

    solutions: list[int]
    num_qubits: int
    search_space_size: int
    total_steps: int
    success: bool


class VQERequest(BaseModel):
    """Request for VQE optimization."""

    num_qubits: int = Field(..., ge=1, le=8, description="Number of qubits")
    cost_observable: dict[str, float] = Field(
        ..., description="Observable as {bitstring: eigenvalue}"
    )
    ansatz_depth: int = Field(default=2, ge=1, le=10)
    max_iterations: int = Field(default=50, ge=1, le=500)
    optimizer: str = Field(default="COBYLA")
    shots: int = Field(default=512, ge=1, le=100000)
    backend: str = Field(default="simulator")


class VQEResponse(BaseModel):
    """Response from VQE optimization."""

    optimal_cost: float
    optimal_params: list[float]
    converged: bool
    num_evaluations: int
    cost_history: list[float]
    success: bool


# --- Backend models ---


class BackendInfo(BaseModel):
    """Information about a quantum backend."""

    name: str
    max_qubits: int
    supported_gates: list[str]
    supports_statevector: bool
    backend_type: str = Field(default="simulator", description="simulator, cloud, or hardware")
    status: str = Field(default="available")


class BackendListResponse(BaseModel):
    """List of available backends."""

    backends: list[BackendInfo]
    default_backend: str = "simulator"


# --- Job models ---


class JobStatusResponse(BaseModel):
    """Status of a submitted job."""

    job_id: str
    status: str
    backend: str
    submitted_at: float
    completed_at: float | None = None
    result: CircuitResponse | None = None
    error: str | None = None


# --- Health ---


class HealthResponse(BaseModel):
    """API health check response."""

    status: str = "ok"
    version: str
    backends_available: int
