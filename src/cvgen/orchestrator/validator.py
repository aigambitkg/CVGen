"""Circuit validation and complexity estimation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import GateType

logger = logging.getLogger(__name__)


@dataclass
class ComplexityEstimate:
    """Estimated complexity metrics for a quantum circuit."""

    depth: int
    gate_count: int
    two_qubit_gates: int
    estimated_runtime_ms: float

    def __repr__(self) -> str:
        return (
            f"ComplexityEstimate(depth={self.depth}, gates={self.gate_count}, "
            f"cx={self.two_qubit_gates}, runtime_ms={self.estimated_runtime_ms:.2f})"
        )


@dataclass
class ValidationResult:
    """Result of circuit validation."""

    success: bool
    errors: list[str]
    warnings: list[str]
    estimated_depth: int
    estimated_gate_count: int

    def __repr__(self) -> str:
        status = "VALID" if self.success else "INVALID"
        return (
            f"ValidationResult(status={status}, errors={len(self.errors)}, "
            f"warnings={len(self.warnings)}, depth={self.estimated_depth}, "
            f"gates={self.estimated_gate_count})"
        )


class CircuitValidator:
    """Validates quantum circuits and estimates their complexity.

    Checks circuit validity against backend capabilities and provides
    complexity estimation for resource planning.
    """

    # Estimated execution times for common gates in milliseconds
    GATE_TIMES_MS = {
        GateType.H: 0.01,
        GateType.X: 0.01,
        GateType.Y: 0.01,
        GateType.Z: 0.01,
        GateType.S: 0.01,
        GateType.T: 0.01,
        GateType.RX: 0.02,
        GateType.RY: 0.02,
        GateType.RZ: 0.02,
        GateType.CX: 0.05,
        GateType.CZ: 0.05,
        GateType.SWAP: 0.10,
        GateType.CCX: 0.15,
        GateType.MEASURE: 0.05,
        GateType.BARRIER: 0.0,
    }

    def __init__(self, enable_dry_run: bool = False) -> None:
        """Initialize the circuit validator.

        Args:
            enable_dry_run: If True, run circuits on simulator to verify executability.
        """
        self.enable_dry_run = enable_dry_run
        self._dry_run_backend: Optional[QuantumBackend] = None

    def set_dry_run_backend(self, backend: QuantumBackend) -> None:
        """Set the backend to use for dry-run validation.

        Args:
            backend: Backend instance to use for dry-run execution.
        """
        self._dry_run_backend = backend

    def validate(
        self,
        circuit: QuantumCircuit,
        backend: Optional[QuantumBackend] = None,
    ) -> ValidationResult:
        """Validate a circuit against optional backend constraints.

        Args:
            circuit: The quantum circuit to validate.
            backend: Optional backend to check compatibility against.

        Returns:
            ValidationResult with errors, warnings, and metrics.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Basic circuit structure checks
        if circuit.num_qubits < 1:
            errors.append("Circuit must have at least 1 qubit")
            return ValidationResult(
                success=False,
                errors=errors,
                warnings=warnings,
                estimated_depth=0,
                estimated_gate_count=0,
            )

        # Check for measurement operations
        has_measurement = any(op.gate_type == GateType.MEASURE for op in circuit.operations)
        if not has_measurement and len(circuit.operations) > 0:
            warnings.append("Circuit has no measurement operations")

        # Check all operations
        op_errors, op_warnings = self._validate_operations(circuit)
        errors.extend(op_errors)
        warnings.extend(op_warnings)

        # Check backend compatibility if provided
        if backend is not None:
            backend_errors = backend.validate_circuit(circuit)
            errors.extend(backend_errors)

        # Estimate complexity
        complexity = self.estimate_complexity(circuit)

        # Optional dry-run on simulator
        if self.enable_dry_run and self._dry_run_backend is not None and not errors:
            try:
                from cvgen.core.types import JobConfig

                config = JobConfig(shots=1)
                self._dry_run_backend.execute(circuit, config)
                logger.debug(f"Dry-run validation passed for circuit '{circuit.name}'")
            except Exception as e:
                errors.append(f"Dry-run execution failed: {str(e)}")

        success = len(errors) == 0
        return ValidationResult(
            success=success,
            errors=errors,
            warnings=warnings,
            estimated_depth=complexity.depth,
            estimated_gate_count=complexity.gate_count,
        )

    def _validate_operations(self, circuit: QuantumCircuit) -> tuple[list[str], list[str]]:
        """Validate all operations in the circuit.

        Args:
            circuit: The quantum circuit to validate.

        Returns:
            Tuple of (errors, warnings).
        """
        errors: list[str] = []
        warnings: list[str] = []

        if not circuit.operations:
            warnings.append("Circuit has no operations")
            return errors, warnings

        for i, op in enumerate(circuit.operations):
            # Check qubit targets are valid
            for target in op.targets:
                if target < 0 or target >= circuit.num_qubits:
                    errors.append(
                        f"Operation {i} ({op.gate_type.value}): "
                        f"qubit {target} out of range [0, {circuit.num_qubits - 1}]"
                    )

            # Check classical targets for measurements
            if op.gate_type == GateType.MEASURE:
                if op.classical_target is not None:
                    if op.classical_target < 0 or op.classical_target >= circuit.num_clbits:
                        errors.append(
                            f"Operation {i} (MEASURE): "
                            f"classical bit {op.classical_target} out of range "
                            f"[0, {circuit.num_clbits - 1}]"
                        )

            # Check parameter validity
            if op.params:
                # Parametric gates should have reasonable parameter values
                if op.gate_type in [GateType.RX, GateType.RY, GateType.RZ]:
                    if len(op.params) != 1:
                        errors.append(
                            f"Operation {i} ({op.gate_type.value}): "
                            f"expected 1 parameter, got {len(op.params)}"
                        )

        return errors, warnings

    def estimate_complexity(self, circuit: QuantumCircuit) -> ComplexityEstimate:
        """Estimate the complexity of executing a circuit.

        Args:
            circuit: The quantum circuit to estimate.

        Returns:
            ComplexityEstimate with depth and execution time.
        """
        if not circuit.operations:
            return ComplexityEstimate(
                depth=0,
                gate_count=0,
                two_qubit_gates=0,
                estimated_runtime_ms=0.0,
            )

        # Calculate depth (longest dependency chain)
        qubit_depths: dict[int, int] = {i: 0 for i in range(circuit.num_qubits)}
        max_depth = 0
        two_qubit_count = 0
        total_gate_time = 0.0

        for op in circuit.operations:
            # Get the maximum depth of qubits this operation depends on
            affected_qubits = list(op.targets)
            if affected_qubits:
                op_depth = max(qubit_depths.get(q, 0) for q in affected_qubits)
            else:
                op_depth = 0

            # Update qubit depths
            for q in affected_qubits:
                qubit_depths[q] = op_depth + 1

            max_depth = max(max_depth, op_depth + 1)

            # Count two-qubit gates
            if op.num_qubits >= 2:
                two_qubit_count += 1

            # Accumulate estimated gate time
            gate_time = self.GATE_TIMES_MS.get(op.gate_type, 0.01)
            total_gate_time += gate_time

        gate_count = len(circuit.operations)

        # Estimate total runtime: sequential execution time + parallelization benefit
        # Rough model: gates on different qubits can run in parallel
        parallel_factor = max(1, circuit.num_qubits / 2)
        estimated_runtime = total_gate_time / parallel_factor + (max_depth * 0.01)

        return ComplexityEstimate(
            depth=max_depth,
            gate_count=gate_count,
            two_qubit_gates=two_qubit_count,
            estimated_runtime_ms=estimated_runtime,
        )
