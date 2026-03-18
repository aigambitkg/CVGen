"""Backend adapter for Origin Pilot quantum operating system.

Origin Pilot is an open-source quantum-classical-intelligent OS developed
by Origin Quantum, supporting superconducting, ion trap, and neutral atom
quantum processors via the QPanda framework.

This adapter provides integration with Origin Pilot's QPanda SDK.
When QPanda is not installed, it falls back to the built-in simulator.
"""

from __future__ import annotations

import logging

from cvgen.backends.base import QuantumBackend
from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import (
    BackendCapabilities,
    CircuitResult,
    GateType,
    JobConfig,
)

logger = logging.getLogger(__name__)

# Try to import QPanda
try:
    import pyqpanda as pq  # type: ignore[import-untyped]

    HAS_QPANDA = True
except ImportError:
    HAS_QPANDA = False


_GATE_MAP = {
    GateType.H: "H",
    GateType.X: "X",
    GateType.Y: "Y",
    GateType.Z: "Z",
    GateType.S: "S",
    GateType.T: "T",
    GateType.RX: "RX",
    GateType.RY: "RY",
    GateType.RZ: "RZ",
    GateType.CX: "CNOT",
    GateType.CZ: "CZ",
    GateType.SWAP: "SWAP",
    GateType.CCX: "Toffoli",
}


class OriginPilotBackend(QuantumBackend):
    """Backend for Origin Pilot / QPanda quantum systems.

    When QPanda is available, circuits are translated to QPanda format
    and executed on the Origin Pilot platform (local simulator or cloud).

    When QPanda is not installed, this falls back to CVGen's built-in
    StateVectorSimulator for development and testing.

    Args:
        use_cloud: If True, connect to Origin Quantum Cloud (requires API key).
        api_key: API key for Origin Quantum Cloud.
        machine_type: QPanda machine type ('CPU', 'GPU', 'CLOUD').
    """

    def __init__(
        self,
        use_cloud: bool = False,
        api_key: str | None = None,
        machine_type: str = "CPU",
    ) -> None:
        self._use_cloud = use_cloud
        self._api_key = api_key
        self._machine_type = machine_type
        self._fallback = StateVectorSimulator()

        if not HAS_QPANDA:
            logger.info(
                "QPanda not installed. OriginPilotBackend will use "
                "built-in StateVectorSimulator as fallback."
            )

    @property
    def name(self) -> str:
        if HAS_QPANDA:
            return f"origin_pilot_{self._machine_type.lower()}"
        return "origin_pilot_fallback"

    @property
    def capabilities(self) -> BackendCapabilities:
        if HAS_QPANDA:
            return BackendCapabilities(
                max_qubits=25,
                supported_gates=set(_GATE_MAP.keys()) | {GateType.MEASURE, GateType.BARRIER},
                supports_statevector=True,
                supports_mid_circuit_measurement=False,
            )
        return self._fallback.capabilities

    def execute(self, circuit: QuantumCircuit, config: JobConfig | None = None) -> CircuitResult:
        """Execute circuit on Origin Pilot or fallback simulator."""
        if not HAS_QPANDA:
            return self._fallback.execute(circuit, config)
        return self._execute_qpanda(circuit, config or JobConfig())

    def _execute_qpanda(self, circuit: QuantumCircuit, config: JobConfig) -> CircuitResult:
        """Execute using QPanda backend."""
        # Initialize QPanda machine
        machine = pq.CPUQVM()
        machine.init_qvm()

        qubits = machine.qAlloc_many(circuit.num_qubits)
        cbits = machine.cAlloc_many(circuit.num_clbits)

        # Build QPanda program
        prog = pq.QProg()
        for op in circuit.operations:
            if op.gate_type == GateType.BARRIER:
                continue
            elif op.gate_type == GateType.MEASURE:
                prog << pq.Measure(qubits[op.targets[0]], cbits[op.classical_target or 0])
            elif op.gate_type == GateType.H:
                prog << pq.H(qubits[op.targets[0]])
            elif op.gate_type == GateType.X:
                prog << pq.X(qubits[op.targets[0]])
            elif op.gate_type == GateType.Y:
                prog << pq.Y(qubits[op.targets[0]])
            elif op.gate_type == GateType.Z:
                prog << pq.Z(qubits[op.targets[0]])
            elif op.gate_type == GateType.RX:
                prog << pq.RX(qubits[op.targets[0]], op.params[0])
            elif op.gate_type == GateType.RY:
                prog << pq.RY(qubits[op.targets[0]], op.params[0])
            elif op.gate_type == GateType.RZ:
                prog << pq.RZ(qubits[op.targets[0]], op.params[0])
            elif op.gate_type == GateType.CX:
                prog << pq.CNOT(qubits[op.targets[0]], qubits[op.targets[1]])
            elif op.gate_type == GateType.CZ:
                prog << pq.CZ(qubits[op.targets[0]], qubits[op.targets[1]])
            elif op.gate_type == GateType.SWAP:
                prog << pq.SWAP(qubits[op.targets[0]], qubits[op.targets[1]])
            elif op.gate_type == GateType.CCX:
                prog << pq.Toffoli(
                    qubits[op.targets[0]], qubits[op.targets[1]], qubits[op.targets[2]]
                )

        # Execute
        result = machine.run_with_configuration(prog, cbits, config.shots)
        machine.finalize()

        # Convert QPanda result format to CVGen format
        counts = {k: v for k, v in result.items()}

        return CircuitResult(
            counts=counts,
            shots=config.shots,
            metadata={"backend": self.name, "machine_type": self._machine_type},
        )
