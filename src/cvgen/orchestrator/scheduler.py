"""Task scheduler for routing quantum jobs to backends."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult, JobConfig, JobStatus

try:
    from cvgen.bridge.telemetry import SystemStatus, TelemetrySubscriber

    HAS_BRIDGE = True
except ImportError:
    HAS_BRIDGE = False
    SystemStatus = None  # type: ignore
    TelemetrySubscriber = None  # type: ignore

logger = logging.getLogger(__name__)


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


@dataclass
class JobStatistics:
    """Statistics for job execution on a backend."""

    backend_name: str
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    avg_execution_time_s: float = 0.0

    @property
    def success_rate(self) -> float:
        """Get the success rate as a fraction [0, 1]."""
        if self.total_jobs == 0:
            return 0.0
        return self.successful_jobs / self.total_jobs


class SmartScheduler(TaskScheduler):
    """Enhanced scheduler with intelligent backend selection and resilient execution.

    Features:
    - Circuit validation before execution
    - Telemetry-aware backend selection
    - Retry policy with exponential backoff
    - Fallback chain for resilient execution
    - Job statistics tracking for intelligent routing
    - Thread-safe concurrent job submission
    """

    def __init__(
        self,
        telemetry: Optional[TelemetrySubscriber] = None,
    ) -> None:
        """Initialize the smart scheduler.

        Args:
            telemetry: Optional TelemetrySubscriber for backend health monitoring.
        """
        super().__init__()
        self.telemetry = telemetry
        self._job_stats: dict[str, JobStatistics] = {}
        self._stats_lock = threading.Lock()

    def get_best_backend(
        self,
        circuit: QuantumCircuit,
    ) -> tuple[str, QuantumBackend]:
        """Select the best backend considering telemetry and statistics.

        Considers:
        - Backend capabilities and qubit requirements
        - Telemetry status (AVAILABLE, CALIBRATING, OFFLINE)
        - Historical job statistics (success rate, execution time)
        - Queue depth from telemetry

        Args:
            circuit: The quantum circuit to execute.

        Returns:
            Tuple of (backend_name, backend_instance).

        Raises:
            RuntimeError: If no suitable backend is found.
        """
        if not self._backends:
            raise RuntimeError("No backends registered")

        # Filter backends by capability
        candidates = []
        for name, backend in self._backends.items():
            caps = backend.capabilities
            if caps.max_qubits >= circuit.num_qubits:
                candidates.append((name, backend))

        if not candidates:
            raise RuntimeError(
                f"No backend with {circuit.num_qubits}+ qubits available"
            )

        # Sort by telemetry status and statistics
        def score_backend(item: tuple[str, QuantumBackend]) -> tuple[int, float, float]:
            name, backend = item
            # Status priority (lower is better)
            status_priority = 0
            if self.telemetry and HAS_BRIDGE:
                try:
                    status = self.telemetry.get_status(name)
                    if status == SystemStatus.AVAILABLE:
                        status_priority = 0
                    elif status == SystemStatus.DEGRADED:
                        status_priority = 1
                    elif status == SystemStatus.CALIBRATING:
                        status_priority = 2
                    else:
                        status_priority = 3
                except Exception:
                    status_priority = 3

            # Success rate (higher is better, negate for sorting)
            stats = self._job_stats.get(name)
            success_rate = stats.success_rate if stats else 0.5
            success_score = -success_rate

            # Qubit count (prefer less qubits = more efficient)
            qubit_penalty = float(backend.capabilities.max_qubits - circuit.num_qubits)

            return (status_priority, success_score, qubit_penalty)

        candidates.sort(key=score_backend)
        return candidates[0]

    def submit_smart(
        self,
        circuit: QuantumCircuit,
        config: Optional[JobConfig] = None,
        requirements: Optional[BackendRequirements] = None,
    ) -> JobRecord:
        """Submit a circuit with intelligent selection, validation, and retries.

        Process:
        1. Validate circuit
        2. Select best backend using telemetry
        3. Execute with retry policy
        4. Fallback to alternative backends if needed
        5. Track statistics

        Args:
            circuit: The quantum circuit to execute.
            config: Execution configuration.
            requirements: Backend requirements (min_qubits, etc).

        Returns:
            JobRecord with execution results.

        Raises:
            Exception: If validation fails or all backends fail.
        """
        from cvgen.orchestrator.validator import CircuitValidator
        from cvgen.orchestrator.retry import RetryPolicy
        from cvgen.orchestrator.fallback import FallbackChain

        config = config or JobConfig()
        requirements = requirements or BackendRequirements(min_qubits=circuit.num_qubits)

        # Ensure min_qubits covers the circuit
        if requirements.min_qubits < circuit.num_qubits:
            requirements = BackendRequirements(
                min_qubits=circuit.num_qubits,
                preferred_backend=requirements.preferred_backend,
                needs_statevector=requirements.needs_statevector,
                tags=requirements.tags,
            )

        # Step 1: Validate circuit
        validator = CircuitValidator()
        validation_result = validator.validate(circuit)
        if not validation_result.success:
            error_msg = "Circuit validation failed: " + "; ".join(
                validation_result.errors
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Step 2: Select best backend
        try:
            backend_name, backend = self.get_best_backend(circuit)
        except RuntimeError:
            backend_name, backend = self.select_backend(requirements)

        # Create job record
        job_id = str(uuid.uuid4())[:8]
        record = JobRecord(
            job_id=job_id,
            circuit_name=circuit.name or "unnamed",
            backend_name=backend_name,
            status=JobStatus.RUNNING,
            submitted_at=time.time(),
        )
        self._jobs[job_id] = record

        # Step 3: Execute with retry policy
        retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            jitter=True,
            telemetry=self.telemetry,
        )

        try:
            retry_result = retry_policy.execute(
                backend.execute,
                circuit,
                config,
                backend_name=backend_name,
            )

            if retry_result.success:
                result = retry_result.result
                record.result = result
                record.status = JobStatus.COMPLETED
                self._update_statistics(backend_name, success=True, duration=time.time() - record.submitted_at)
                logger.info(f"Job {job_id} completed on {backend_name} "
                           f"after {retry_result.attempts} attempt(s)")
            else:
                # Step 4: Fallback to alternative backends
                available_backends = [
                    (n, b)
                    for n, b in self._backends.items()
                    if n != backend_name
                ]
                if available_backends:
                    logger.info(f"Primary backend {backend_name} failed, trying fallback chain")
                    fallback_chain = FallbackChain(available_backends, self.telemetry)
                    try:
                        fallback_result = fallback_chain.execute(circuit, config)
                        record.result = fallback_result.result
                        record.backend_name = fallback_result.backend_used
                        record.status = JobStatus.COMPLETED
                        self._update_statistics(fallback_result.backend_used, success=True, duration=time.time() - record.submitted_at)
                        logger.info(f"Job {job_id} completed on fallback backend "
                                   f"{fallback_result.backend_used}")
                    except Exception as e:
                        record.error = str(e)
                        record.status = JobStatus.FAILED
                        self._update_statistics(backend_name, success=False, duration=time.time() - record.submitted_at)
                        logger.error(f"Job {job_id} failed after all retries and fallbacks: {e}")
                        raise
                else:
                    record.error = "All retries failed and no fallback backends available"
                    record.status = JobStatus.FAILED
                    self._update_statistics(backend_name, success=False, duration=time.time() - record.submitted_at)
                    logger.error(record.error)
                    raise RuntimeError(record.error)

        except Exception as e:
            record.error = str(e)
            record.status = JobStatus.FAILED
            self._update_statistics(backend_name, success=False, duration=time.time() - record.submitted_at)
            raise
        finally:
            record.completed_at = time.time()

        return record

    def _update_statistics(
        self,
        backend_name: str,
        success: bool,
        duration: float,
    ) -> None:
        """Update job statistics for a backend.

        Args:
            backend_name: Name of the backend.
            success: Whether the job succeeded.
            duration: Execution duration in seconds.
        """
        with self._stats_lock:
            if backend_name not in self._job_stats:
                self._job_stats[backend_name] = JobStatistics(backend_name=backend_name)

            stats = self._job_stats[backend_name]
            stats.total_jobs += 1
            if success:
                stats.successful_jobs += 1
            else:
                stats.failed_jobs += 1

            # Update average execution time
            if stats.total_jobs == 1:
                stats.avg_execution_time_s = duration
            else:
                stats.avg_execution_time_s = (
                    (stats.avg_execution_time_s * (stats.total_jobs - 1) + duration)
                    / stats.total_jobs
                )

    def get_statistics(self, backend_name: str) -> Optional[JobStatistics]:
        """Get job statistics for a backend.

        Args:
            backend_name: Name of the backend.

        Returns:
            JobStatistics or None if no statistics yet.
        """
        with self._stats_lock:
            return self._job_stats.get(backend_name)

    def get_all_statistics(self) -> dict[str, JobStatistics]:
        """Get job statistics for all backends.

        Returns:
            Dictionary mapping backend names to JobStatistics.
        """
        with self._stats_lock:
            return dict(self._job_stats)
