"""Backend adapter for IBM Qiskit.

Provides integration with Qiskit's simulators and IBM Quantum hardware.
Requires the optional 'qiskit' dependency: pip install cvgen[qiskit]
"""

from __future__ import annotations

import logging
from typing import Any

from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import (
    BackendCapabilities,
    CircuitResult,
    GateType,
    JobConfig,
)

logger = logging.getLogger(__name__)

try:
    from qiskit import QuantumCircuit as QiskitCircuit  # type: ignore[import-untyped]
    from qiskit.primitives import StatevectorSampler  # type: ignore[import-untyped]

    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False


class QiskitBackend(QuantumBackend):
    """Backend adapter for Qiskit execution.

    Translates CVGen circuits to Qiskit circuits and executes them
    using Qiskit's Aer simulator or IBM Quantum cloud backends.

    Raises ImportError if qiskit is not installed.

    Args:
        backend_name: Qiskit backend name (e.g., 'aer_simulator').
    """

    def __init__(self, backend_name: str = "aer_simulator") -> None:
        if not HAS_QISKIT:
            raise ImportError("Qiskit is not installed. Install it with: pip install cvgen[qiskit]")
        self._backend_name = backend_name

    @property
    def name(self) -> str:
        return f"qiskit_{self._backend_name}"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_qubits=30,
            supported_gates={
                GateType.H,
                GateType.X,
                GateType.Y,
                GateType.Z,
                GateType.S,
                GateType.T,
                GateType.RX,
                GateType.RY,
                GateType.RZ,
                GateType.CX,
                GateType.CZ,
                GateType.SWAP,
                GateType.CCX,
                GateType.MEASURE,
                GateType.BARRIER,
            },
            supports_statevector=True,
            supports_mid_circuit_measurement=True,
        )

    def execute(self, circuit: QuantumCircuit, config: JobConfig | None = None) -> CircuitResult:
        config = config or JobConfig()
        qc = self._translate_circuit(circuit)

        sampler = StatevectorSampler()
        job = sampler.run([qc], shots=config.shots)
        result = job.result()

        # Convert Qiskit counts to string format
        counts_raw = result[0].data.meas.get_counts()
        counts = {k: v for k, v in counts_raw.items()}

        return CircuitResult(
            counts=counts,
            shots=config.shots,
            metadata={"backend": self.name},
        )

    def _translate_circuit(self, circuit: QuantumCircuit) -> Any:
        """Translate a CVGen circuit to a Qiskit circuit."""
        qc = QiskitCircuit(circuit.num_qubits, circuit.num_clbits)

        for op in circuit.operations:
            if op.gate_type == GateType.BARRIER:
                qc.barrier()
            elif op.gate_type == GateType.MEASURE:
                qc.measure(op.targets[0], op.classical_target or 0)
            elif op.gate_type == GateType.H:
                qc.h(op.targets[0])
            elif op.gate_type == GateType.X:
                qc.x(op.targets[0])
            elif op.gate_type == GateType.Y:
                qc.y(op.targets[0])
            elif op.gate_type == GateType.Z:
                qc.z(op.targets[0])
            elif op.gate_type == GateType.S:
                qc.s(op.targets[0])
            elif op.gate_type == GateType.T:
                qc.t(op.targets[0])
            elif op.gate_type == GateType.RX:
                qc.rx(op.params[0], op.targets[0])
            elif op.gate_type == GateType.RY:
                qc.ry(op.params[0], op.targets[0])
            elif op.gate_type == GateType.RZ:
                qc.rz(op.params[0], op.targets[0])
            elif op.gate_type == GateType.CX:
                qc.cx(op.targets[0], op.targets[1])
            elif op.gate_type == GateType.CZ:
                qc.cz(op.targets[0], op.targets[1])
            elif op.gate_type == GateType.SWAP:
                qc.swap(op.targets[0], op.targets[1])
            elif op.gate_type == GateType.CCX:
                qc.ccx(op.targets[0], op.targets[1], op.targets[2])

        return qc
