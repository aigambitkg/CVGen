"""Quantum circuit representation."""

from __future__ import annotations

from copy import deepcopy
from typing import Self

from cvgen.core.types import GateOp, GateType


class QuantumCircuit:
    """A quantum circuit composed of gate operations on qubits.

    Args:
        num_qubits: Number of quantum bits.
        num_clbits: Number of classical bits for measurement results.
                    Defaults to num_qubits if not specified.
    """

    def __init__(self, num_qubits: int, num_clbits: int | None = None) -> None:
        if num_qubits < 1:
            raise ValueError("Circuit must have at least 1 qubit")
        self._num_qubits = num_qubits
        self._num_clbits = num_clbits if num_clbits is not None else num_qubits
        self._operations: list[GateOp] = []
        self._name: str = ""

    @property
    def num_qubits(self) -> int:
        return self._num_qubits

    @property
    def num_clbits(self) -> int:
        return self._num_clbits

    @property
    def operations(self) -> list[GateOp]:
        return list(self._operations)

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def depth(self) -> int:
        """Calculate the circuit depth (longest path through the circuit)."""
        if not self._operations:
            return 0
        qubit_depths: list[int] = [0] * self._num_qubits
        for op in self._operations:
            if op.gate_type in (GateType.MEASURE, GateType.BARRIER):
                continue
            max_depth = max(qubit_depths[q] for q in op.targets)
            for q in op.targets:
                qubit_depths[q] = max_depth + 1
        return max(qubit_depths) if qubit_depths else 0

    @property
    def gate_count(self) -> int:
        """Number of non-measurement gate operations."""
        return sum(
            1 for op in self._operations
            if op.gate_type not in (GateType.MEASURE, GateType.BARRIER)
        )

    @property
    def has_measurements(self) -> bool:
        return any(op.gate_type == GateType.MEASURE for op in self._operations)

    def _validate_qubit(self, qubit: int) -> None:
        if not 0 <= qubit < self._num_qubits:
            raise ValueError(
                f"Qubit {qubit} out of range for {self._num_qubits}-qubit circuit"
            )

    def _validate_clbit(self, clbit: int) -> None:
        if not 0 <= clbit < self._num_clbits:
            raise ValueError(
                f"Classical bit {clbit} out of range for {self._num_clbits}-clbit circuit"
            )

    # --- Single-qubit gates ---

    def h(self, qubit: int) -> Self:
        """Apply Hadamard gate."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.H, (qubit,)))
        return self

    def x(self, qubit: int) -> Self:
        """Apply Pauli-X (NOT) gate."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.X, (qubit,)))
        return self

    def y(self, qubit: int) -> Self:
        """Apply Pauli-Y gate."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.Y, (qubit,)))
        return self

    def z(self, qubit: int) -> Self:
        """Apply Pauli-Z gate."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.Z, (qubit,)))
        return self

    def s(self, qubit: int) -> Self:
        """Apply S (phase) gate."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.S, (qubit,)))
        return self

    def t(self, qubit: int) -> Self:
        """Apply T gate."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.T, (qubit,)))
        return self

    def rx(self, qubit: int, theta: float) -> Self:
        """Apply rotation around X-axis."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.RX, (qubit,), (theta,)))
        return self

    def ry(self, qubit: int, theta: float) -> Self:
        """Apply rotation around Y-axis."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.RY, (qubit,), (theta,)))
        return self

    def rz(self, qubit: int, theta: float) -> Self:
        """Apply rotation around Z-axis."""
        self._validate_qubit(qubit)
        self._operations.append(GateOp(GateType.RZ, (qubit,), (theta,)))
        return self

    # --- Two-qubit gates ---

    def cx(self, control: int, target: int) -> Self:
        """Apply CNOT (controlled-X) gate."""
        self._validate_qubit(control)
        self._validate_qubit(target)
        if control == target:
            raise ValueError("Control and target must be different qubits")
        self._operations.append(GateOp(GateType.CX, (control, target)))
        return self

    def cz(self, qubit_a: int, qubit_b: int) -> Self:
        """Apply controlled-Z gate."""
        self._validate_qubit(qubit_a)
        self._validate_qubit(qubit_b)
        if qubit_a == qubit_b:
            raise ValueError("CZ gate requires two different qubits")
        self._operations.append(GateOp(GateType.CZ, (qubit_a, qubit_b)))
        return self

    def swap(self, qubit_a: int, qubit_b: int) -> Self:
        """Apply SWAP gate."""
        self._validate_qubit(qubit_a)
        self._validate_qubit(qubit_b)
        if qubit_a == qubit_b:
            raise ValueError("SWAP gate requires two different qubits")
        self._operations.append(GateOp(GateType.SWAP, (qubit_a, qubit_b)))
        return self

    # --- Three-qubit gates ---

    def ccx(self, control_a: int, control_b: int, target: int) -> Self:
        """Apply Toffoli (CCX) gate."""
        for q in (control_a, control_b, target):
            self._validate_qubit(q)
        if len({control_a, control_b, target}) != 3:
            raise ValueError("Toffoli gate requires three different qubits")
        self._operations.append(GateOp(GateType.CCX, (control_a, control_b, target)))
        return self

    # --- Measurement ---

    def measure(self, qubit: int, clbit: int) -> Self:
        """Measure a qubit into a classical bit."""
        self._validate_qubit(qubit)
        self._validate_clbit(clbit)
        self._operations.append(
            GateOp(GateType.MEASURE, (qubit,), classical_target=clbit)
        )
        return self

    def measure_all(self) -> Self:
        """Measure all qubits into corresponding classical bits."""
        for i in range(self._num_qubits):
            self.measure(i, i)
        return self

    # --- Utility ---

    def barrier(self) -> Self:
        """Add a barrier (no-op separator for visualization)."""
        self._operations.append(
            GateOp(GateType.BARRIER, tuple(range(self._num_qubits)))
        )
        return self

    def copy(self) -> QuantumCircuit:
        """Create a deep copy of this circuit."""
        return deepcopy(self)

    def compose(self, other: QuantumCircuit) -> Self:
        """Append all operations from another circuit onto this one."""
        if other.num_qubits != self._num_qubits:
            raise ValueError(
                f"Cannot compose circuits with different qubit counts "
                f"({self._num_qubits} vs {other.num_qubits})"
            )
        self._operations.extend(other.operations)
        return self

    def bind_parameters(self, params: dict[int, float]) -> QuantumCircuit:
        """Create a new circuit with parametric gate angles replaced.

        Args:
            params: Mapping from operation index to new parameter value.
        """
        new_circuit = self.copy()
        new_ops = []
        for i, op in enumerate(new_circuit._operations):
            if i in params and op.params:
                new_ops.append(
                    GateOp(op.gate_type, op.targets, (params[i],), op.classical_target)
                )
            else:
                new_ops.append(op)
        new_circuit._operations = new_ops
        return new_circuit

    def parameter_indices(self) -> list[int]:
        """Return indices of parametric gates."""
        return [
            i for i, op in enumerate(self._operations)
            if op.gate_type in (GateType.RX, GateType.RY, GateType.RZ)
        ]

    def __repr__(self) -> str:
        name = f" '{self._name}'" if self._name else ""
        return (
            f"QuantumCircuit({self._num_qubits}q, {self._num_clbits}c{name}, "
            f"depth={self.depth}, gates={self.gate_count})"
        )

    def __len__(self) -> int:
        return len(self._operations)
