"""Task scheduler for routing quantum jobs to backends."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult, JobConfig, JobStatus


@dataclass
class JobRecord:
    """Record of a submitted quantum job."""

    job_id: str
    circuit_name: str
    backend_name: str
    status: JobStatus
    submitted_at: float
    completed_at: float | None = None
    result: CircuitResult | None = None
    error: str | None = None


@dataclass
class BackendRequirements:
    """Requirements for selecting a backend."""

    min_qubits: int = 1
    preferred_backend: str | None = None
    needs_statevector: bool = False
    tags: dict[str, Any] = field(default_factory=dict)


class TaskScheduler:
    """Routes quantum circuits to appropriate backends.

    Manages multiple backends and selects the best one based on
    circuit requirements and backend capabilities.
    """

    def __init__(self) -> None:
        self._backends: dict[str, QuantumBackend] = {}
        self._jobs: dict[str, JobRecord] = {}

    def register_backend(self, name: str, backend: QuantumBackend) -> None:
        """Register a backend with a given name."""
        self._backends[name] = backend

    def remove_backend(self, name: str) -> None:
        """Remove a registered backend."""
        self._backends.pop(name, None)

    @property
    def backends(self) -> dict[str, QuantumBackend]:
        return dict(self._backends)

    def select_backend(
        self, requirements: BackendRequirements | None = None
    ) -> tuple[str, QuantumBackend]:
        """Select the best backend for the given requirements.

        Returns:
            Tuple of (backend_name, backend_instance).

        Raises:
            RuntimeError: If no suitable backend is found.
        """
        if not self._backends:
            raise RuntimeError("No backends registered")

        requirements = requirements or BackendRequirements()

        # Prefer explicitly requested backend
        if requirements.preferred_backend and requirements.preferred_backend in self._backends:
            return requirements.preferred_backend, self._backends[requirements.preferred_backend]

        # Filter by capabilities
        candidates = []
        for name, backend in self._backends.items():
            caps = backend.capabilities
            if caps.max_qubits >= requirements.min_qubits:
                if requirements.needs_statevector and not caps.supports_statevector:
                    continue
                candidates.append((name, backend))

        if not candidates:
            raise RuntimeError(
                f"No backend meets requirements: min_qubits={requirements.min_qubits}, "
                f"needs_statevector={requirements.needs_statevector}"
            )

        # Pick the one with the most qubits (best capability)
        candidates.sort(key=lambda x: x[1].capabilities.max_qubits, reverse=True)
        return candidates[0]

    def submit(
        self,
        circuit: QuantumCircuit,
        config: JobConfig | None = None,
        requirements: BackendRequirements | None = None,
    ) -> JobRecord:
        """Submit a circuit for execution on the best available backend.

        Returns:
            JobRecord with execution results.
        """
        config = config or JobConfig()
        req = requirements or BackendRequirements(min_qubits=circuit.num_qubits)

        # Ensure min_qubits covers the circuit
        if req.min_qubits < circuit.num_qubits:
            req = BackendRequirements(
                min_qubits=circuit.num_qubits,
                preferred_backend=req.preferred_backend,
                needs_statevector=req.needs_statevector,
                tags=req.tags,
            )

        name, backend = self.select_backend(req)

        job_id = str(uuid.uuid4())[:8]
        record = JobRecord(
            job_id=job_id,
            circuit_name=circuit.name or "unnamed",
            backend_name=name,
            status=JobStatus.RUNNING,
            submitted_at=time.time(),
        )
        self._jobs[job_id] = record

        try:
            result = backend.execute(circuit, config)
            record.result = result
            record.status = JobStatus.COMPLETED
        except Exception as e:
            record.error = str(e)
            record.status = JobStatus.FAILED
            raise
        finally:
            record.completed_at = time.time()

        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    @property
    def job_history(self) -> list[JobRecord]:
        return list(self._jobs.values())
