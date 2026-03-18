"""Tests for AI agents."""

import pytest

from cvgen.agents.quantum_agent import QuantumAgent, SearchTask
from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask
from cvgen.backends.simulator import StateVectorSimulator


@pytest.fixture
def sim():
    return StateVectorSimulator(max_qubits=10)


class TestQuantumAgent:
    def test_grover_search_2qubit(self, sim):
        """QuantumAgent should find a marked state in a 2-qubit search space."""
        target = 3  # |11⟩

        task = SearchTask(
            num_qubits=2,
            oracle_fn=lambda x: x == target,
            max_solutions=1,
        )
        agent = QuantumAgent(sim, shots=1024, name="test_grover")
        solutions = agent.run_search(task)
        assert target in solutions

    def test_grover_search_3qubit(self, sim):
        """QuantumAgent should find a marked state in a 3-qubit search space."""
        target = 5  # |101⟩

        task = SearchTask(
            num_qubits=3,
            oracle_fn=lambda x: x == target,
            max_solutions=1,
        )
        agent = QuantumAgent(sim, shots=2048)
        solutions = agent.run_search(task)
        assert target in solutions

    def test_agent_result_metadata(self, sim):
        """Agent result should contain proper metadata."""
        task = SearchTask(
            num_qubits=2,
            oracle_fn=lambda x: x == 0,
            max_solutions=1,
        )
        agent = QuantumAgent(sim, shots=512)
        result = agent.run(task)
        assert result.success
        assert result.total_steps > 0
        assert len(result.quantum_results) > 0
        assert result.metadata["agent_name"] == "QuantumAgent"


class TestHybridAgent:
    def test_vqe_simple_minimum(self, sim):
        """HybridAgent should find the minimum of a simple cost landscape."""
        # Simple observable: minimize the probability of |1⟩ state
        # The minimum is when all params produce |0⟩
        observable = {"0": 0.0, "1": 1.0}

        task = VariationalTask(
            num_qubits=1,
            cost_observable=observable,
            ansatz_depth=1,
            max_iterations=50,
            optimizer_method="COBYLA",
        )
        agent = HybridAgent(sim, shots=512)
        result = agent.run(task)

        assert result.success
        assert result.value is not None
        final_cost = result.value["optimal_cost"]
        # Should converge close to 0 (all |0⟩ probability)
        assert final_cost < 0.3, f"Cost {final_cost} did not converge to near 0"

    def test_vqe_with_initial_params(self, sim):
        """VQE should accept initial parameters."""
        observable = {"0": 0.0, "1": 1.0}

        task = VariationalTask(
            num_qubits=1,
            cost_observable=observable,
            ansatz_depth=1,
            initial_params=[0.1, 0.1],  # 1 qubit * 2 params * 1 depth
            max_iterations=30,
        )
        agent = HybridAgent(sim, shots=256)
        result = agent.run(task)
        assert result.success
        assert result.value["num_evaluations"] > 0

    def test_vqe_history_tracking(self, sim):
        """Optimization history should be tracked."""
        observable = {"0": 0.0, "1": 1.0}
        task = VariationalTask(
            num_qubits=1,
            cost_observable=observable,
            ansatz_depth=1,
            max_iterations=10,
        )
        agent = HybridAgent(sim, shots=256)
        agent.run(task)
        assert len(agent.opt_history.costs) > 0
        assert agent.opt_history.num_circuit_evals > 0
