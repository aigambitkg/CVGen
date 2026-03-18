"""Shared types for the quantum computing framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np


class JobStatus(Enum):
    """Status of a quantum job."""

    PENDING = auto()
    QUEUED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class GateType(Enum):
    """Supported quantum gate types."""

    # Single-qubit gates
    H = "h"
    X = "x"
    Y = "y"
    Z = "z"
    S = "s"
    T = "t"
    # Parametric single-qubit gates
    RX = "rx"
    RY = "ry"
    RZ = "rz"
    # Two-qubit gates
    CX = "cx"
    CZ = "cz"
    SWAP = "swap"
    # Three-qubit gates
    CCX = "ccx"
    # Measurement
    MEASURE = "measure"
    # Barrier (no-op, for visualization)
    BARRIER = "barrier"


@dataclass(frozen=True)
class GateOp:
    """A single gate operation in a quantum circuit."""

    gate_type: GateType
    targets: tuple[int, ...]
    params: tuple[float, ...] = ()
    classical_target: int | None = None

    @property
    def num_qubits(self) -> int:
        return len(self.targets)


@dataclass
class CircuitResult:
    """Result of executing a quantum circuit."""

    counts: dict[str, int]
    shots: int
    statevector: np.ndarray | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def probabilities(self) -> dict[str, float]:
        """Convert counts to probabilities."""
        return {k: v / self.shots for k, v in self.counts.items()}

    def most_likely(self) -> str:
        """Return the most frequently measured bitstring."""
        return max(self.counts, key=self.counts.get)  # type: ignore[arg-type]

    def expectation_value(self, observable: dict[str, float]) -> float:
        """Compute expectation value of an observable given as {bitstring: eigenvalue}."""
        probs = self.probabilities
        return sum(observable.get(k, 0.0) * probs.get(k, 0.0) for k in observable)


@dataclass
class JobConfig:
    """Configuration for executing a quantum job."""

    shots: int = 1024
    optimization_level: int = 1
    seed: int | None = None
    return_statevector: bool = False
    backend_options: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackendCapabilities:
    """Capabilities of a quantum backend."""

    max_qubits: int
    supported_gates: set[GateType]
    supports_statevector: bool = False
    supports_mid_circuit_measurement: bool = False
    native_gates: set[GateType] = field(default_factory=set)
    connectivity: list[tuple[int, int]] | None = None
