"""AWS Braket backend for multi-vendor quantum hardware.

Provides access to quantum processors from IonQ, Rigetti, and OQC
through Amazon Braket. Requires AWS credentials and the Braket SDK.

Setup:
    export AWS_DEFAULT_REGION=us-east-1
    pip install amazon-braket-sdk
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
    from braket.aws import AwsDevice, AwsQuantumTask
    from braket.circuits import Circuit as BraketCircuit

    HAS_BRAKET = True
except ImportError:
    HAS_BRAKET = False

# Common device ARNs
BRAKET_DEVICES = {
    "ionq_harmony": "arn:aws:braket:::device/qpu/ionq/Harmony",
    "ionq_aria": "arn:aws:braket:::device/qpu/ionq/Aria-1",
    "rigetti_ankaa": "arn:aws:braket:::device/qpu/rigetti/Ankaa-3",
    "oqc_lucy": "arn:aws:braket:::device/qpu/oqc/Lucy",
    "sv1_simulator": "arn:aws:braket:::device/quantum-simulator/amazon/sv1",
    "dm1_simulator": "arn:aws:braket:::device/quantum-simulator/amazon/dm1",
    "tn1_simulator": "arn:aws:braket:::device/quantum-simulator/amazon/tn1",
}


class AWSBraketBackend(QuantumBackend):
    """Backend for Amazon Braket quantum computing service.

    Supports IonQ (trapped ion), Rigetti (superconducting), and OQC
    quantum processors, plus Amazon's managed simulators (SV1, DM1, TN1).

    Args:
        device_arn: AWS device ARN or shorthand name (e.g. 'ionq_harmony', 'sv1_simulator').
        s3_bucket: S3 bucket for storing results.
        s3_prefix: S3 key prefix for results.
    """

    def __init__(
        self,
        device_arn: str = "arn:aws:braket:::device/quantum-simulator/amazon/sv1",
        s3_bucket: str = "",
        s3_prefix: str = "cvgen-results",
    ) -> None:
        if not HAS_BRAKET:
            raise ImportError(
                "Amazon Braket SDK is required: pip install amazon-braket-sdk"
            )

        # Resolve shorthand names
        self._device_arn = BRAKET_DEVICES.get(device_arn, device_arn)
        self._s3_bucket = s3_bucket
        self._s3_prefix = s3_prefix
        self._device: Any = None

    def _get_device(self) -> Any:
        """Lazy device connection."""
        if self._device is None:
            self._device = AwsDevice(self._device_arn)
            logger.info(f"Connected to AWS Braket: {self._device.name}")
        return self._device

    @property
    def name(self) -> str:
        # Extract readable name from ARN
        parts = self._device_arn.split("/")
        return f"braket_{parts[-1]}" if parts else "braket"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_qubits=25,  # IonQ Harmony: 11, Aria: 25, Rigetti: 84
            supported_gates={
                GateType.H, GateType.X, GateType.Y, GateType.Z,
                GateType.S, GateType.T,
                GateType.RX, GateType.RY, GateType.RZ,
                GateType.CX, GateType.CZ, GateType.SWAP, GateType.CCX,
                GateType.MEASURE, GateType.BARRIER,
            },
            supports_statevector=False,
            supports_mid_circuit_measurement=False,
        )

    def execute(
        self, circuit: QuantumCircuit, config: JobConfig | None = None
    ) -> CircuitResult:
        """Execute circuit on AWS Braket."""
        config = config or JobConfig()
        device = self._get_device()

        braket_circuit = self._translate_circuit(circuit)

        # Build S3 output location
        s3_location = None
        if self._s3_bucket:
            s3_location = (self._s3_bucket, self._s3_prefix)

        # Submit task
        task = device.run(braket_circuit, shots=config.shots, s3_destination_folder=s3_location)
        result = task.result()

        # Parse measurement counts
        counts = {}
        for measurements in result.measurement_counts.items():
            bitstring, count = measurements
            counts[str(bitstring)] = int(count)

        return CircuitResult(
            counts=counts,
            shots=config.shots,
            metadata={
                "backend": self.name,
                "device_arn": self._device_arn,
                "task_id": task.id,
            },
        )

    def _translate_circuit(self, circuit: QuantumCircuit) -> Any:
        """Translate CVGen circuit to Braket format."""
        bc = BraketCircuit()

        for op in circuit.operations:
            gt = op.gate_type
            t = op.targets

            if gt == GateType.BARRIER:
                continue  # Braket doesn't have barriers
            elif gt == GateType.MEASURE:
                continue  # Braket measures all qubits automatically
            elif gt == GateType.H:
                bc.h(t[0])
            elif gt == GateType.X:
                bc.x(t[0])
            elif gt == GateType.Y:
                bc.y(t[0])
            elif gt == GateType.Z:
                bc.z(t[0])
            elif gt == GateType.S:
                bc.s(t[0])
            elif gt == GateType.T:
                bc.t(t[0])
            elif gt == GateType.RX:
                bc.rx(t[0], op.params[0])
            elif gt == GateType.RY:
                bc.ry(t[0], op.params[0])
            elif gt == GateType.RZ:
                bc.rz(t[0], op.params[0])
            elif gt == GateType.CX:
                bc.cnot(t[0], t[1])
            elif gt == GateType.CZ:
                bc.cz(t[0], t[1])
            elif gt == GateType.SWAP:
                bc.swap(t[0], t[1])
            elif gt == GateType.CCX:
                bc.ccnot(t[0], t[1], t[2])

        return bc

    @property
    def status(self) -> JobStatus:
        try:
            device = self._get_device()
            if device.is_available:
                return JobStatus.COMPLETED
            return JobStatus.QUEUED
        except Exception:
            return JobStatus.FAILED
