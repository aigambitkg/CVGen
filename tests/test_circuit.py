"""Tests for QuantumCircuit construction and properties."""

import pytest

from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import GateType


class TestCircuitConstruction:
    def test_basic_creation(self):
        qc = QuantumCircuit(3)
        assert qc.num_qubits == 3
        assert qc.num_clbits == 3
        assert qc.depth == 0
        assert qc.gate_count == 0
        assert len(qc) == 0

    def test_custom_clbits(self):
        qc = QuantumCircuit(3, num_clbits=2)
        assert qc.num_qubits == 3
        assert qc.num_clbits == 2

    def test_zero_qubits_raises(self):
        with pytest.raises(ValueError, match="at least 1 qubit"):
            QuantumCircuit(0)

    def test_qubit_out_of_range(self):
        qc = QuantumCircuit(2)
        with pytest.raises(ValueError, match="out of range"):
            qc.h(5)

    def test_same_qubit_cx_raises(self):
        qc = QuantumCircuit(2)
        with pytest.raises(ValueError, match="different qubits"):
            qc.cx(0, 0)


class TestGateOperations:
    def test_single_qubit_gates(self):
        qc = QuantumCircuit(1)
        qc.h(0).x(0).y(0).z(0).s(0).t(0)
        assert qc.gate_count == 6
        types = [op.gate_type for op in qc.operations]
        assert types == [GateType.H, GateType.X, GateType.Y, GateType.Z, GateType.S, GateType.T]

    def test_parametric_gates(self):
        qc = QuantumCircuit(1)
        qc.rx(0, 1.5).ry(0, 2.0).rz(0, 0.5)
        assert qc.gate_count == 3
        assert qc.operations[0].params == (1.5,)
        assert qc.operations[1].params == (2.0,)

    def test_two_qubit_gates(self):
        qc = QuantumCircuit(3)
        qc.cx(0, 1).cz(1, 2).swap(0, 2)
        assert qc.gate_count == 3

    def test_toffoli(self):
        qc = QuantumCircuit(3)
        qc.ccx(0, 1, 2)
        assert qc.gate_count == 1
        assert qc.operations[0].targets == (0, 1, 2)

    def test_toffoli_same_qubit_raises(self):
        qc = QuantumCircuit(3)
        with pytest.raises(ValueError, match="three different qubits"):
            qc.ccx(0, 0, 2)

    def test_fluent_api(self):
        qc = QuantumCircuit(2)
        result = qc.h(0).cx(0, 1).measure_all()
        assert result is qc


class TestCircuitProperties:
    def test_depth_single_qubit(self):
        qc = QuantumCircuit(1)
        qc.h(0).x(0).y(0)
        assert qc.depth == 3

    def test_depth_parallel(self):
        qc = QuantumCircuit(3)
        qc.h(0).h(1).h(2)  # All parallel → depth 1
        assert qc.depth == 1

    def test_depth_sequential_cx(self):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(1, 2)
        assert qc.depth == 3

    def test_measurement(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.measure(0, 0)
        assert qc.has_measurements
        assert qc.gate_count == 1  # measure not counted

    def test_measure_all(self):
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.measure_all()
        ops = [op for op in qc.operations if op.gate_type == GateType.MEASURE]
        assert len(ops) == 3


class TestCircuitManipulation:
    def test_copy(self):
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1)
        copy = qc.copy()
        copy.x(0)
        assert qc.gate_count == 2
        assert copy.gate_count == 3

    def test_compose(self):
        qc1 = QuantumCircuit(2)
        qc1.h(0)
        qc2 = QuantumCircuit(2)
        qc2.cx(0, 1)
        qc1.compose(qc2)
        assert qc1.gate_count == 2

    def test_compose_different_sizes_raises(self):
        qc1 = QuantumCircuit(2)
        qc2 = QuantumCircuit(3)
        with pytest.raises(ValueError, match="different qubit counts"):
            qc1.compose(qc2)

    def test_bind_parameters(self):
        qc = QuantumCircuit(2)
        qc.ry(0, 0.0).ry(1, 0.0)
        bound = qc.bind_parameters({0: 1.5, 1: 2.5})
        assert bound.operations[0].params == (1.5,)
        assert bound.operations[1].params == (2.5,)
        # Original unchanged
        assert qc.operations[0].params == (0.0,)

    def test_parameter_indices(self):
        qc = QuantumCircuit(2)
        qc.h(0).rx(0, 1.0).cx(0, 1).ry(1, 2.0)
        assert qc.parameter_indices() == [1, 3]

    def test_repr(self):
        qc = QuantumCircuit(2)
        qc.name = "test"
        qc.h(0).cx(0, 1)
        r = repr(qc)
        assert "2q" in r
        assert "test" in r
