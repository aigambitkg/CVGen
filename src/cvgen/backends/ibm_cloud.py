"""IBM Quantum Cloud backend via Qiskit Runtime.

Provides access to real IBM quantum processors (superconducting qubits)
through IBM Quantum Platform. Requires an IBM Quantum API token.

Setup:
    export IBM_QUANTUM_TOKEN=your_token_here
    pip install qiskit-ibm-runtime
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
    from qiskit import QuantumCircuit as QiskitCircuit
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    HAS_QISKIT = True
except ImportError:
    HAS_QISKIT = False

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

    HAS_IBM_RUNTIME = True
except ImportError:
    HAS_IBM_RUNTIME = False


class IBMCloudBackend(QuantumBackend):
    """Backend for IBM Quantum Cloud via Qiskit Runtime.

    Executes circuits on real IBM quantum processors or cloud simulators.
    Supports automatic transpilation for hardware topology.

    Args:
        token: IBM Quantum API token.
        instance: IBM Quantum instance (e.g. 'ibm-q/open/main').
        backend_name: Target backend (e.g. 'ibm_brisbane', 'ibm_osaka').
    """

    def __init__(
        self,
        token: str | None = None,
        instance: str = "ibm-q/open/main",
        backend_name: str = "ibm_brisbane",
    ) -> None:
        if not HAS_QISKIT:
            raise ImportError("Qiskit is required: pip install qiskit")
        if not HAS_IBM_RUNTIME:
            raise ImportError("qiskit-ibm-runtime is required: pip install qiskit-ibm-runtime")

        self._token = token
        self._instance = instance
        self._backend_name = backend_name
        self._service: Any = None
        self._hw_backend: Any = None

    def _connect(self) -> None:
        """Lazy connection to IBM Quantum."""
        if self._service is None:
            self._service = QiskitRuntimeService(
                channel="ibm_quantum",
                token=self._token,
                instance=self._instance,
            )
            self._hw_backend = self._service.backend(self._backend_name)
            logger.info(f"Connected to IBM Quantum: {self._backend_name}")

    @property
    def name(self) -> str:
        return f"ibm_cloud_{self._backend_name}"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_qubits=127,  # Eagle processors
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
            supports_statevector=False,
            supports_mid_circuit_measurement=True,
        )

    def execute(self, circuit: QuantumCircuit, config: JobConfig | None = None) -> CircuitResult:
        """Execute circuit on IBM Quantum hardware."""
        config = config or JobConfig()
        self._connect()

        # Translate CVGen circuit to Qiskit
        qc = self._translate_circuit(circuit)

        # Transpile for hardware topology
        pm = generate_preset_pass_manager(
            optimization_level=config.optimization_level,
            backend=self._hw_backend,
        )
        transpiled = pm.run(qc)

        # Execute via Sampler
        sampler = SamplerV2(backend=self._hw_backend)
        job = sampler.run([transpiled], shots=config.shots)
        result = job.result()

        # Parse results
        counts_raw = result[0].data.meas.get_counts()
        counts = {k: int(v) for k, v in counts_raw.items()}

        return CircuitResult(
            counts=counts,
            shots=config.shots,
            metadata={
                "backend": self.name,
                "hw_backend": self._backend_name,
                "transpiled_depth": transpiled.depth(),
            },
        )

    def _translate_circuit(self, circuit: QuantumCircuit) -> Any:
        """Translate CVGen circuit to Qiskit format."""
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
            st = self._hw_backend.status()
            if st.operational:
                return JobStatus.COMPLETED
            return JobStatus.PENDING
        except Exception:
            return JobStatus.FAILED
