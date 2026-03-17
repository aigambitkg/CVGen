"""Shared test fixtures."""

import pytest

from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.circuit import QuantumCircuit


@pytest.fixture
def simulator():
    """A fresh StateVectorSimulator instance."""
    return StateVectorSimulator(max_qubits=10)


@pytest.fixture
def bell_circuit():
    """A Bell state circuit (2 qubits)."""
    qc = QuantumCircuit(2)
    qc.name = "bell"
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    return qc


@pytest.fixture
def ghz3_circuit():
    """A 3-qubit GHZ state circuit."""
    qc = QuantumCircuit(3)
    qc.name = "ghz3"
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(0, 2)
    qc.measure_all()
    return qc
