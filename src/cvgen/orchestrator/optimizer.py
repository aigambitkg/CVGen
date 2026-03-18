"""Quantum circuit optimizer."""

from __future__ import annotations

from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import GateOp, GateType

# Gates that are self-inverse (applying twice = identity)
_SELF_INVERSE = {GateType.X, GateType.Y, GateType.Z, GateType.H, GateType.SWAP}


class CircuitOptimizer:
    """Optimizes quantum circuits by reducing gate count and depth.

    Optimization levels:
        0: No optimization (pass-through)
        1: Remove redundant adjacent gates (XX=I, HH=I, etc.)
        2: Level 1 + merge consecutive single-qubit rotations
    """

    def optimize(self, circuit: QuantumCircuit, level: int = 1) -> QuantumCircuit:
        """Optimize a circuit at the given level.

        Args:
            circuit: Input circuit.
            level: Optimization level (0, 1, or 2).

        Returns:
            New optimized circuit.
        """
        if level == 0:
            return circuit.copy()

        ops = list(circuit.operations)

        if level >= 1:
            ops = self._eliminate_redundant(ops)

        if level >= 2:
            ops = self._merge_rotations(ops)

        # Build new circuit
        new_circuit = QuantumCircuit(circuit.num_qubits, circuit.num_clbits)
        new_circuit.name = circuit.name
        new_circuit._operations = ops
        return new_circuit

    def _eliminate_redundant(self, ops: list[GateOp]) -> list[GateOp]:
        """Remove consecutive self-inverse gate pairs."""
        changed = True
        while changed:
            changed = False
            new_ops: list[GateOp] = []
            i = 0
            while i < len(ops):
                if i + 1 < len(ops):
                    a, b = ops[i], ops[i + 1]
                    if (
                        a.gate_type == b.gate_type
                        and a.targets == b.targets
                        and a.gate_type in _SELF_INVERSE
                        and not a.params
                    ):
                        # Skip both — they cancel out
                        i += 2
                        changed = True
                        continue
                new_ops.append(ops[i])
                i += 1
            ops = new_ops
        return ops

    def _merge_rotations(self, ops: list[GateOp]) -> list[GateOp]:
        """Merge consecutive same-axis rotations on the same qubit."""
        import math

        result: list[GateOp] = []
        i = 0
        while i < len(ops):
            if i + 1 < len(ops):
                a, b = ops[i], ops[i + 1]
                if (
                    a.gate_type == b.gate_type
                    and a.targets == b.targets
                    and a.gate_type in (GateType.RX, GateType.RY, GateType.RZ)
                    and a.params
                    and b.params
                ):
                    merged_angle = a.params[0] + b.params[0]
                    # Normalize to [-2π, 2π]
                    merged_angle = merged_angle % (2 * math.pi)
                    if abs(merged_angle) < 1e-10:
                        # Rotation cancels out
                        i += 2
                        continue
                    result.append(GateOp(a.gate_type, a.targets, (merged_angle,)))
                    i += 2
                    continue
            result.append(ops[i])
            i += 1
        return result
