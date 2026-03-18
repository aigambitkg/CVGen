"""Azure Quantum backend for IonQ and Quantinuum hardware.

Provides access to quantum processors through Microsoft Azure Quantum.
Supports IonQ (trapped ion) and Quantinuum (trapped ion) systems.

Setup:
    export AZURE_QUANTUM_RESOURCE_ID=/subscriptions/.../resourceGroups/.../providers/Microsoft.Quantum/Workspaces/...
    pip install azure-quantum qiskit-azure-quantum
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
    JobStatus,
)

logger = logging.getLogger(__name__)

try:
    from azure.quantum import Workspace
    from azure.quantum.qiskit import AzureQuantumProvider

    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False

try:
    from qiskit import QuantumCircuit as QiskitCircuit

    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False

# Common Azure Quantum targets
AZURE_TARGETS = {
    "ionq_simulator": "ionq.simulator",
    "ionq_harmony": "ionq.qpu",
    "ionq_aria": "ionq.qpu.aria-1",
    "quantinuum_h1_emulator": "quantinuum.sim.h1-1e",
    "quantinuum_h1": "quantinuum.qpu.h1-1",
    "quantinuum_h2": "quantinuum.qpu.h2-1",
    "rigetti_ankaa": "rigetti.sim.ankaa-2",
}


class AzureQuantumBackend(QuantumBackend):
    """Backend for Azure Quantum service.

    Supports IonQ and Quantinuum quantum processors, plus their simulators.
    Uses Qiskit as the circuit format for Azure Quantum integration.

    Args:
        resource_id: Azure Quantum workspace resource ID.
        location: Azure region (e.g. 'eastus', 'westus').
        target: Target backend name or shorthand.
    """

    def __init__(
        self,
        resource_id: str = "",
        location: str = "eastus",
        target: str = "ionq.simulator",
    ) -> None:
        if not HAS_AZURE:
            raise ImportError(
                "Azure Quantum SDK is required: pip install azure-quantum"
            )
        if not HAS_QISKIT:
            raise ImportError("Qiskit is required for Azure Quantum: pip install qiskit")

        self._resource_id = resource_id
        self._location = location
        self._target = AZURE_TARGETS.get(target, target)
        self._provider: Any = None
        self._az_backend: Any = None

    def _connect(self) -> None:
        """Lazy connection to Azure Quantum."""
        if self._provider is None:
            workspace = Workspace(
                resource_id=self._resource_id,
                location=self._location,
            )
            self._provider = AzureQuantumProvider(workspace)
            self._az_backend = self._provider.get_backend(self._target)
            logger.info(f"Connected to Azure Quantum: {self._target}")

    @property
    def name(self) -> str:
        return f"azure_{self._target.replace('.', '_')}"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_qubits=29,  # IonQ Aria: 25, Quantinuum H2: 32
            supported_gates={
                GateType.H, GateType.X, GateType.Y, GateType.Z,
                GateType.S, GateType.T,
                GateType.RX, GateType.RY, GateType.RZ,
                GateType.CX, GateType.CZ, GateType.SWAP, GateType.CCX,
                GateType.MEASURE, GateType.BARRIER,
            },
            supports_statevector=False,
            supports_mid_circuit_measurement=True,
        )

    def execute(
        self, circuit: QuantumCircuit, config: JobConfig | None = None
    ) -> CircuitResult:
        """Execute circuit on Azure Quantum."""
        config = config or JobConfig()
        self._connect()

        qc = self._translate_circuit(circuit)

        # Execute on Azure Quantum backend
        job = self._az_backend.run(qc, shots=config.shots)
        result = job.result()

        counts = result.get_counts(qc)
        counts = {k: int(v) for k, v in counts.items()}

        return CircuitResult(
            counts=counts,
            shots=config.shots,
            metadata={
                "backend": self.name,
                "target": self._target,
                "job_id": job.id(),
            },
        )

    def _translate_circuit(self, circuit: QuantumCircuit) -> Any:
        """Translate CVGen circuit to Qiskit format for Azure."""
        qc = QiskitCircuit(circuit.num_qubits, circuit.num_clbits)

        for op in circuit.operations:
            gt = op.gate_type
            t = op.targets
            if gt == GateType.BARRIER:
                qc.barrier()
            elif gt == GateType.MEASURE:
                qc.measure(t[0], op.classical_target or 0)
            elif gt == GateType.H:
                qc.h(t[0])
            elif gt == GateType.X:
                qc.x(t[0])
            elif gt == GateType.Y:
                qc.y(t[0])
            elif gt == GateType.Z:
                qc.z(t[0])
            elif gt == GateType.S:
                qc.s(t[0])
            elif gt == GateType.T:
                qc.t(t[0])
            elif gt == GateType.RX:
                qc.rx(op.params[0], t[0])
            elif gt == GateType.RY:
                qc.ry(op.params[0], t[0])
            elif gt == GateType.RZ:
                qc.rz(op.params[0], t[0])
            elif gt == GateType.CX:
                qc.cx(t[0], t[1])
            elif gt == GateType.CZ:
                qc.cz(t[0], t[1])
            elif gt == GateType.SWAP:
                qc.swap(t[0], t[1])
            elif gt == GateType.CCX:
                qc.ccx(t[0], t[1], t[2])

        return qc

    @property
    def status(self) -> JobStatus:
        try:
            self._connect()
            return JobStatus.COMPLETED
        except Exception:
            return JobStatus.FAILED
