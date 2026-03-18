"""Metrics collection for quantum execution tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult


@dataclass
class ExecutionRecord:
    """Record of a single circuit execution."""

    circuit_name: str
    num_qubits: int
    circuit_depth: int
    gate_count: int
    shots: int
    duration_s: float
    num_unique_outcomes: int
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Collects and summarizes quantum execution metrics.

    Tracks circuit executions to provide insights into
    resource utilization and performance.
    """

    def __init__(self) -> None:
        self._records: list[ExecutionRecord] = []

    def record_execution(
        self,
        circuit: QuantumCircuit,
        result: CircuitResult,
        duration_s: float,
    ) -> ExecutionRecord:
        """Record a circuit execution."""
        record = ExecutionRecord(
            circuit_name=circuit.name or "unnamed",
            num_qubits=circuit.num_qubits,
            circuit_depth=circuit.depth,
            gate_count=circuit.gate_count,
            shots=result.shots,
            duration_s=duration_s,
            num_unique_outcomes=len(result.counts),
        )
        self._records.append(record)
        return record

    @property
    def total_executions(self) -> int:
        return len(self._records)

    @property
    def total_shots(self) -> int:
        return sum(r.shots for r in self._records)

    @property
    def total_duration_s(self) -> float:
        return sum(r.duration_s for r in self._records)

    def summary(self) -> dict:
        """Return a summary of all collected metrics."""
        if not self._records:
            return {"total_executions": 0}

        depths = [r.circuit_depth for r in self._records]
        gates = [r.gate_count for r in self._records]
        qubits = [r.num_qubits for r in self._records]

        return {
            "total_executions": self.total_executions,
            "total_shots": self.total_shots,
            "total_duration_s": round(self.total_duration_s, 4),
            "avg_circuit_depth": round(sum(depths) / len(depths), 2),
            "max_circuit_depth": max(depths),
            "avg_gate_count": round(sum(gates) / len(gates), 2),
            "max_gate_count": max(gates),
            "avg_qubits": round(sum(qubits) / len(qubits), 2),
            "max_qubits": max(qubits),
        }

    def reset(self) -> None:
        """Clear all collected records."""
        self._records.clear()

    @property
    def records(self) -> list[ExecutionRecord]:
        return list(self._records)
