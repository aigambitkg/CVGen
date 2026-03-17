"""Tests for the StateVectorSimulator."""

import math

import numpy as np
import pytest

from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import JobConfig


@pytest.fixture
def sim():
    return StateVectorSimulator(max_qubits=10)


class TestStatevectorBasics:
    def test_initial_state(self, sim):
        """A circuit with no gates should produce |0⟩."""
        qc = QuantumCircuit(1)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [1, 0])

    def test_x_gate(self, sim):
        """X|0⟩ = |1⟩"""
        qc = QuantumCircuit(1)
        qc.x(0)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [0, 1])

    def test_h_gate(self, sim):
        """H|0⟩ = |+⟩ = (|0⟩ + |1⟩)/√2"""
        qc = QuantumCircuit(1)
        qc.h(0)
        sv = sim.run_statevector(qc)
        expected = np.array([1, 1]) / math.sqrt(2)
        np.testing.assert_allclose(sv, expected, atol=1e-10)

    def test_y_gate(self, sim):
        """Y|0⟩ = i|1⟩"""
        qc = QuantumCircuit(1)
        qc.y(0)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [0, 1j], atol=1e-10)

    def test_z_gate(self, sim):
        """Z|0⟩ = |0⟩"""
        qc = QuantumCircuit(1)
        qc.z(0)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [1, 0], atol=1e-10)

    def test_hzh_equals_x(self, sim):
        """HZH = X"""
        qc = QuantumCircuit(1)
        qc.h(0).z(0).h(0)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [0, 1], atol=1e-10)


class TestTwoQubitGates:
    def test_bell_state(self, sim):
        """H on q0, CNOT(0,1) → Bell state (|00⟩ + |11⟩)/√2"""
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1)
        sv = sim.run_statevector(qc)
        expected = np.array([1, 0, 0, 1]) / math.sqrt(2)
        np.testing.assert_allclose(sv, expected, atol=1e-10)

    def test_cnot_no_flip(self, sim):
        """CNOT with control=|0⟩ does nothing."""
        qc = QuantumCircuit(2)
        qc.cx(0, 1)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [1, 0, 0, 0], atol=1e-10)

    def test_cnot_flip(self, sim):
        """CNOT with control=|1⟩ flips target."""
        qc = QuantumCircuit(2)
        qc.x(0).cx(0, 1)
        sv = sim.run_statevector(qc)
        # |10⟩ → |11⟩
        np.testing.assert_allclose(sv, [0, 0, 0, 1], atol=1e-10)

    def test_swap_gate(self, sim):
        """SWAP |10⟩ = |01⟩"""
        qc = QuantumCircuit(2)
        qc.x(0).swap(0, 1)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [0, 1, 0, 0], atol=1e-10)

    def test_cz_gate(self, sim):
        """CZ|11⟩ = -|11⟩"""
        qc = QuantumCircuit(2)
        qc.x(0).x(1).cz(0, 1)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(sv, [0, 0, 0, -1], atol=1e-10)


class TestThreeQubitGates:
    def test_toffoli_no_flip(self, sim):
        """Toffoli with one control=|0⟩ does not flip target."""
        qc = QuantumCircuit(3)
        qc.x(0).ccx(0, 1, 2)
        sv = sim.run_statevector(qc)
        # |100⟩ stays |100⟩
        np.testing.assert_allclose(sv, [0, 0, 0, 0, 1, 0, 0, 0], atol=1e-10)

    def test_toffoli_flip(self, sim):
        """Toffoli with both controls=|1⟩ flips target."""
        qc = QuantumCircuit(3)
        qc.x(0).x(1).ccx(0, 1, 2)
        sv = sim.run_statevector(qc)
        # |110⟩ → |111⟩
        np.testing.assert_allclose(sv, [0, 0, 0, 0, 0, 0, 0, 1], atol=1e-10)


class TestParametricGates:
    def test_rx_pi(self, sim):
        """RX(π)|0⟩ = -i|1⟩"""
        qc = QuantumCircuit(1)
        qc.rx(0, math.pi)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(abs(sv[0]), 0, atol=1e-10)
        np.testing.assert_allclose(abs(sv[1]), 1, atol=1e-10)

    def test_ry_pi(self, sim):
        """RY(π)|0⟩ = |1⟩"""
        qc = QuantumCircuit(1)
        qc.ry(0, math.pi)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(abs(sv[0]), 0, atol=1e-10)
        np.testing.assert_allclose(abs(sv[1]), 1, atol=1e-10)

    def test_rz_pi(self, sim):
        """RZ(π)|0⟩ = e^{-iπ/2}|0⟩"""
        qc = QuantumCircuit(1)
        qc.rz(0, math.pi)
        sv = sim.run_statevector(qc)
        np.testing.assert_allclose(abs(sv[0]), 1, atol=1e-10)
        np.testing.assert_allclose(abs(sv[1]), 0, atol=1e-10)


class TestMeasurement:
    def test_deterministic_0(self, sim):
        """Measuring |0⟩ always gives 0."""
        qc = QuantumCircuit(1)
        qc.measure_all()
        result = sim.execute(qc, JobConfig(shots=100, seed=42))
        assert result.counts == {"0": 100}

    def test_deterministic_1(self, sim):
        """Measuring X|0⟩ = |1⟩ always gives 1."""
        qc = QuantumCircuit(1)
        qc.x(0)
        qc.measure_all()
        result = sim.execute(qc, JobConfig(shots=100, seed=42))
        assert result.counts == {"1": 100}

    def test_bell_state_measurement(self, sim):
        """Bell state should give ~50% |00⟩ and ~50% |11⟩."""
        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1)
        qc.measure_all()
        result = sim.execute(qc, JobConfig(shots=10000, seed=42))
        assert set(result.counts.keys()).issubset({"00", "11"})
        assert result.counts.get("00", 0) > 4000
        assert result.counts.get("11", 0) > 4000

    def test_statevector_return(self, sim):
        """Config with return_statevector should include it."""
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.measure_all()
        result = sim.execute(
            qc, JobConfig(shots=1, seed=42, return_statevector=True)
        )
        assert result.statevector is not None
        assert len(result.statevector) == 2

    def test_result_probabilities(self, sim):
        """Test probability calculation from counts."""
        qc = QuantumCircuit(1)
        qc.h(0)
        qc.measure_all()
        result = sim.execute(qc, JobConfig(shots=1000, seed=42))
        probs = result.probabilities
        assert abs(sum(probs.values()) - 1.0) < 1e-10

    def test_result_most_likely(self, sim):
        """most_likely should return the most common outcome."""
        qc = QuantumCircuit(1)
        qc.measure_all()
        result = sim.execute(qc, JobConfig(shots=100, seed=42))
        assert result.most_likely() == "0"


class TestValidation:
    def test_too_many_qubits(self):
        sim = StateVectorSimulator(max_qubits=3)
        qc = QuantumCircuit(5)
        qc.h(0)
        qc.measure_all()
        with pytest.raises(ValueError, match="validation failed"):
            sim.execute(qc)
