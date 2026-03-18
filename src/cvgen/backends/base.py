"""Abstract base class for quantum backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import BackendCapabilities, CircuitResult, JobConfig, JobStatus


class QuantumBackend(ABC):
    """Abstract interface for quantum execution backends.

    All backends (simulators, cloud APIs, hardware) implement this interface
    to provide a unified execution model for quantum circuits.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""

    @property
    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """Backend capabilities and constraints."""

    @abstractmethod
    def execute(self, circuit: QuantumCircuit, config: JobConfig | None = None) -> CircuitResult:
        """Execute a quantum circuit and return results.

        Args:
            circuit: The quantum circuit to execute.
            config: Execution configuration. Uses defaults if None.

        Returns:
            CircuitResult with measurement counts and optional statevector.
        """

    def validate_circuit(self, circuit: QuantumCircuit) -> list[str]:
        """Check if a circuit is compatible with this backend.

        Returns:
            List of validation error messages. Empty list means valid.
        """
        errors = []
        caps = self.capabilities
        if circuit.num_qubits > caps.max_qubits:
            errors.append(
                f"Circuit requires {circuit.num_qubits} qubits, "
                f"backend supports max {caps.max_qubits}"
            )
        for op in circuit.operations:
            if op.gate_type not in caps.supported_gates:
                errors.append(f"Unsupported gate: {op.gate_type.value}")
        return errors

    @property
    def status(self) -> JobStatus:
        """Current backend status. Override for remote backends."""
        return JobStatus.COMPLETED

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
