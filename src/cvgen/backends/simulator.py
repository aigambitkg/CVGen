"""Built-in state vector quantum simulator.

A pure NumPy-based simulator that can run quantum circuits locally
without any external quantum hardware or cloud services.
"""

from __future__ import annotations

import numpy as np

from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.gates import get_gate_matrix
from cvgen.core.types import (
    BackendCapabilities,
    CircuitResult,
    GateOp,
    GateType,
    JobConfig,
)


class StateVectorSimulator(QuantumBackend):
    """State vector simulator using dense matrix operations.

    Simulates quantum circuits by maintaining the full 2^n state vector
    and applying gate operations as matrix multiplications.

    Args:
        max_qubits: Maximum number of qubits to simulate (default 20).
    """

    def __init__(self, max_qubits: int = 20) -> None:
        self._max_qubits = max_qubits

    @property
    def name(self) -> str:
        return "statevector_simulator"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_qubits=self._max_qubits,
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

        errors = self.validate_circuit(circuit)
        if errors:
            raise ValueError(f"Circuit validation failed: {'; '.join(errors)}")

        rng = np.random.default_rng(config.seed)
        n = circuit.num_qubits
        dim = 2**n

        # Run shots and collect measurement outcomes
        counts: dict[str, int] = {}
        final_statevector = None

        for _ in range(config.shots):
            # Initialize |0...0⟩
            statevector = np.zeros(dim, dtype=complex)
            statevector[0] = 1.0

            # Classical register
            clbits = [0] * circuit.num_clbits

            for op in circuit.operations:
                if op.gate_type == GateType.BARRIER:
                    continue
                elif op.gate_type == GateType.MEASURE:
                    statevector, outcome = self._measure_qubit(statevector, n, op.targets[0], rng)
                    if op.classical_target is not None:
                        clbits[op.classical_target] = outcome
                else:
                    statevector = self._apply_gate(statevector, n, op)

            # Record measurement result
            bitstring = "".join(str(b) for b in clbits)
            counts[bitstring] = counts.get(bitstring, 0) + 1
            final_statevector = statevector

        return CircuitResult(
            counts=counts,
            shots=config.shots,
            statevector=final_statevector if config.return_statevector else None,
            metadata={
                "backend": self.name,
                "num_qubits": n,
                "circuit_depth": circuit.depth,
                "gate_count": circuit.gate_count,
            },
        )

    def run_statevector(self, circuit: QuantumCircuit) -> np.ndarray:
        """Run circuit and return the final statevector (no measurement collapse).

        This ignores measurement operations and returns the pure state.
        Useful for debugging and verification.
        """
        errors = self.validate_circuit(circuit)
        if errors:
            raise ValueError(f"Circuit validation failed: {'; '.join(errors)}")

        n = circuit.num_qubits
        dim = 2**n
        statevector = np.zeros(dim, dtype=complex)
        statevector[0] = 1.0

        for op in circuit.operations:
            if op.gate_type in (GateType.BARRIER, GateType.MEASURE):
                continue
            statevector = self._apply_gate(statevector, n, op)

        return statevector

    def _apply_gate(self, statevector: np.ndarray, num_qubits: int, op: GateOp) -> np.ndarray:
        """Apply a gate operation to the statevector."""
        gate_matrix = get_gate_matrix(op.gate_type.value, op.params)
        targets = op.targets

        if len(targets) == 1:
            return self._apply_single_qubit_gate(statevector, num_qubits, gate_matrix, targets[0])
        elif len(targets) == 2:
            return self._apply_two_qubit_gate(
                statevector, num_qubits, gate_matrix, targets[0], targets[1]
            )
        elif len(targets) == 3:
            return self._apply_three_qubit_gate(
                statevector, num_qubits, gate_matrix, targets[0], targets[1], targets[2]
            )
        else:
            raise ValueError(f"Gates on {len(targets)} qubits not supported")

    def _apply_single_qubit_gate(
        self,
        statevector: np.ndarray,
        num_qubits: int,
        gate: np.ndarray,
        target: int,
    ) -> np.ndarray:
        """Efficiently apply single-qubit gate using reshape trick."""
        n = num_qubits
        sv = statevector.reshape([2] * n)
        # Apply gate to the target qubit axis
        sv = np.tensordot(gate, sv, axes=([1], [target]))
        # Move the result axis back to the correct position
        sv = np.moveaxis(sv, 0, target)
        return sv.reshape(2**n)

    def _apply_two_qubit_gate(
        self,
        statevector: np.ndarray,
        num_qubits: int,
        gate: np.ndarray,
        qubit_a: int,
        qubit_b: int,
    ) -> np.ndarray:
        """Apply a two-qubit gate."""
        n = num_qubits
        dim = 2**n
        gate_4x4 = gate.reshape(2, 2, 2, 2)
        sv = statevector.reshape([2] * n)

        # Contract over the two target qubits
        sv = np.tensordot(gate_4x4, sv, axes=([2, 3], [qubit_a, qubit_b]))
        # Axes 0, 1 of result correspond to new qubit_a, qubit_b
        # Move them to the correct positions
        # Result shape: (2, 2, remaining dims...)
        # Need to move axis 0 -> qubit_a and axis 1 -> qubit_b
        # Current positions: gate outputs are at 0 and 1
        # We need to put them at qubit_a and qubit_b
        source = [0, 1]
        dest = sorted([qubit_a, qubit_b])
        sv = np.moveaxis(sv, source, dest)
        return sv.reshape(dim)

    def _apply_three_qubit_gate(
        self,
        statevector: np.ndarray,
        num_qubits: int,
        gate: np.ndarray,
        q0: int,
        q1: int,
        q2: int,
    ) -> np.ndarray:
        """Apply a three-qubit gate (e.g., Toffoli)."""
        n = num_qubits
        dim = 2**n
        gate_8 = gate.reshape(2, 2, 2, 2, 2, 2)
        sv = statevector.reshape([2] * n)

        sv = np.tensordot(gate_8, sv, axes=([3, 4, 5], [q0, q1, q2]))
        dest = sorted([q0, q1, q2])
        sv = np.moveaxis(sv, [0, 1, 2], dest)
        return sv.reshape(dim)

    def _measure_qubit(
        self,
        statevector: np.ndarray,
        num_qubits: int,
        target: int,
        rng: np.random.Generator,
    ) -> tuple[np.ndarray, int]:
        """Measure a single qubit, collapsing the statevector.

        Returns:
            Tuple of (collapsed statevector, measurement outcome 0 or 1).
        """
        n = num_qubits
        dim = 2**n
        probs = np.abs(statevector) ** 2

        # Calculate probability of measuring 0 on the target qubit
        prob_0 = 0.0
        for i in range(dim):
            if (i >> (n - 1 - target)) & 1 == 0:
                prob_0 += probs[i]

        # Sample outcome
        outcome = 0 if rng.random() < prob_0 else 1

        # Collapse statevector
        new_sv = np.zeros(dim, dtype=complex)
        for i in range(dim):
            bit = (i >> (n - 1 - target)) & 1
            if bit == outcome:
                new_sv[i] = statevector[i]

        # Renormalize
        norm = np.linalg.norm(new_sv)
        if norm > 1e-15:
            new_sv /= norm

        return new_sv, outcome
