"""Translate quantum circuits to various execution formats."""

from __future__ import annotations

import math
from typing import Optional

from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import GateType


class CircuitTranslator:
    """Translates QuantumCircuit to executable formats for different backends."""

    @staticmethod
    def translate_to_qpanda(circuit: QuantumCircuit) -> str:
        """Translate a QuantumCircuit to executable QPanda3 Python code.

        Args:
            circuit: QuantumCircuit to translate

        Returns:
            QPanda3 Python code as a string

        Raises:
            ValueError: If circuit contains unsupported gates
        """
        lines = []
        lines.append("from pyqpanda import *")
        lines.append("")
        lines.append("def circuit_program():")
        lines.append(f"    qvm = CPUQVM()")
        lines.append(f"    qvm.initState_computational_basis()")
        lines.append(f"    q = qvm.qAlloc_qubits({circuit.num_qubits})")
        lines.append(f"    c = qvm.cAlloc_cbits({circuit.num_clbits})")
        lines.append("")
        lines.append("    # Build circuit")
        lines.append(f"    prog = QProg()")
        lines.append("")

        # Add gate operations
        for op in circuit.operations:
            gate_line = CircuitTranslator._gate_to_qpanda(op)
            lines.append(f"    prog << {gate_line}")

        # Ensure measurements if not present
        if not circuit.has_measurements:
            lines.append("")
            lines.append("    # Add measurements")
            for i in range(circuit.num_qubits):
                lines.append(f"    prog << Measure(q[{i}], c[{i}])")

        lines.append("")
        lines.append("    # Execute")
        lines.append("    qvm.directly_run(prog)")
        lines.append("    result = qvm.getCBitMeasResult()")
        lines.append("    return result")
        lines.append("")
        lines.append("if __name__ == '__main__':")
        lines.append("    result = circuit_program()")
        lines.append("    print('Result:', result)")

        return "\n".join(lines)

    @staticmethod
    def translate_to_openqasm(circuit: QuantumCircuit) -> str:
        """Translate a QuantumCircuit to OpenQASM 2.0 format.

        Args:
            circuit: QuantumCircuit to translate

        Returns:
            OpenQASM 2.0 code as a string

        Raises:
            ValueError: If circuit contains unsupported gates
        """
        lines = []
        lines.append("OPENQASM 2.0;")
        lines.append('include "qelib1.inc";')
        lines.append(f"qreg q[{circuit.num_qubits}];")
        lines.append(f"creg c[{circuit.num_clbits}];")
        lines.append("")

        # Add gate operations
        for op in circuit.operations:
            gate_line = CircuitTranslator._gate_to_openqasm(op)
            lines.append(gate_line)

        # Ensure measurements if not present
        if not circuit.has_measurements:
            for i in range(circuit.num_qubits):
                lines.append(f"measure q[{i}] -> c[{i}];")

        return "\n".join(lines)

    @staticmethod
    def _gate_to_qpanda(op) -> str:
        """Convert a GateOp to QPanda3 gate notation.

        Args:
            op: GateOp to convert

        Returns:
            QPanda3 gate string

        Raises:
            ValueError: If gate type is unsupported
        """
        gate_type = op.gate_type

        if gate_type == GateType.H:
            return f"H(q[{op.targets[0]}])"
        elif gate_type == GateType.X:
            return f"X(q[{op.targets[0]}])"
        elif gate_type == GateType.Y:
            return f"Y(q[{op.targets[0]}])"
        elif gate_type == GateType.Z:
            return f"Z(q[{op.targets[0]}])"
        elif gate_type == GateType.S:
            return f"S(q[{op.targets[0]}])"
        elif gate_type == GateType.T:
            return f"T(q[{op.targets[0]}])"
        elif gate_type == GateType.RX:
            angle = op.params[0] if op.params else 0.0
            return f"RX(q[{op.targets[0]}], {angle})"
        elif gate_type == GateType.RY:
            angle = op.params[0] if op.params else 0.0
            return f"RY(q[{op.targets[0]}], {angle})"
        elif gate_type == GateType.RZ:
            angle = op.params[0] if op.params else 0.0
            return f"RZ(q[{op.targets[0]}], {angle})"
        elif gate_type == GateType.CX:
            return f"CNOT(q[{op.targets[0]}], q[{op.targets[1]}])"
        elif gate_type == GateType.CZ:
            return f"CZ(q[{op.targets[0]}], q[{op.targets[1]}])"
        elif gate_type == GateType.SWAP:
            return f"SWAP(q[{op.targets[0]}], q[{op.targets[1]}])"
        elif gate_type == GateType.CCX:
            return f"Toffoli(q[{op.targets[0]}], q[{op.targets[1]}], q[{op.targets[2]}])"
        elif gate_type == GateType.MEASURE:
            clbit = op.classical_target if op.classical_target is not None else op.targets[0]
            return f"Measure(q[{op.targets[0]}], c[{clbit}])"
        elif gate_type == GateType.BARRIER:
            return "Barrier()"
        else:
            raise ValueError(f"Unsupported gate type: {gate_type}")

    @staticmethod
    def _gate_to_openqasm(op) -> str:
        """Convert a GateOp to OpenQASM 2.0 notation.

        Args:
            op: GateOp to convert

        Returns:
            OpenQASM 2.0 gate statement

        Raises:
            ValueError: If gate type is unsupported
        """
        gate_type = op.gate_type

        if gate_type == GateType.H:
            return f"h q[{op.targets[0]}];"
        elif gate_type == GateType.X:
            return f"x q[{op.targets[0]}];"
        elif gate_type == GateType.Y:
            return f"y q[{op.targets[0]}];"
        elif gate_type == GateType.Z:
            return f"z q[{op.targets[0]}];"
        elif gate_type == GateType.S:
            return f"s q[{op.targets[0]}];"
        elif gate_type == GateType.T:
            return f"t q[{op.targets[0]}];"
        elif gate_type == GateType.RX:
            angle = op.params[0] if op.params else 0.0
            return f"rx({angle}) q[{op.targets[0]}];"
        elif gate_type == GateType.RY:
            angle = op.params[0] if op.params else 0.0
            return f"ry({angle}) q[{op.targets[0]}];"
        elif gate_type == GateType.RZ:
            angle = op.params[0] if op.params else 0.0
            return f"rz({angle}) q[{op.targets[0]}];"
        elif gate_type == GateType.CX:
            return f"cx q[{op.targets[0]}],q[{op.targets[1]}];"
        elif gate_type == GateType.CZ:
            return f"cz q[{op.targets[0]}],q[{op.targets[1]}];"
        elif gate_type == GateType.SWAP:
            return f"swap q[{op.targets[0]}],q[{op.targets[1]}];"
        elif gate_type == GateType.CCX:
            return f"ccx q[{op.targets[0]}],q[{op.targets[1]}],q[{op.targets[2]}];"
        elif gate_type == GateType.MEASURE:
            clbit = op.classical_target if op.classical_target is not None else op.targets[0]
            return f"measure q[{op.targets[0]}] -> c[{clbit}];"
        elif gate_type == GateType.BARRIER:
            return "barrier;"
        else:
            raise ValueError(f"Unsupported gate type: {gate_type}")
