#!/usr/bin/env python3
"""Hybrid VQE: Variational Quantum Eigensolver.

Demonstrates:
- Hybrid quantum-classical optimization
- Variational ansatz with parameterized gates
- Classical optimizer driving quantum circuit parameters
- Finding the ground state energy of a simple Hamiltonian
"""

from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask
from cvgen.backends.simulator import StateVectorSimulator


def main():
    sim = StateVectorSimulator()

    # --- Example 1: Simple 1-qubit optimization ---
    print("=== VQE: 1-Qubit Optimization ===")
    print("Goal: Minimize cost = P(|1⟩), i.e., find parameters that produce |0⟩")
    print()

    # Observable: |0⟩ has cost 0, |1⟩ has cost 1
    observable_1q = {"0": 0.0, "1": 1.0}

    task = VariationalTask(
        num_qubits=1,
        cost_observable=observable_1q,
        ansatz_depth=1,
        max_iterations=50,
        optimizer_method="COBYLA",
    )

    agent = HybridAgent(sim, shots=512, name="VQE_1Q")
    result = agent.run(task)

    print(f"Optimal cost: {result.value['optimal_cost']:.6f}")
    print(f"Converged: {result.value['converged']}")
    print(f"Circuit evaluations: {result.value['num_evaluations']}")
    print(f"Optimal params: {[f'{p:.4f}' for p in result.value['optimal_params']]}")

    # Show convergence
    costs = agent.opt_history.costs
    print(f"\nConvergence: {costs[0]:.4f} → {costs[-1]:.4f}")
    print(f"  First 5 costs: {[f'{c:.4f}' for c in costs[:5]]}")
    print(f"  Last 5 costs:  {[f'{c:.4f}' for c in costs[-5:]]}")

    # --- Example 2: 2-qubit optimization ---
    print("\n=== VQE: 2-Qubit Optimization ===")
    print("Goal: Minimize cost = P(|01⟩) + P(|10⟩), i.e., find |00⟩ or |11⟩")
    print()

    # Observable: penalize anti-correlated states
    observable_2q = {
        "00": 0.0,
        "01": 1.0,
        "10": 1.0,
        "11": 0.0,
    }

    task = VariationalTask(
        num_qubits=2,
        cost_observable=observable_2q,
        ansatz_depth=2,
        max_iterations=80,
        optimizer_method="COBYLA",
    )

    agent = HybridAgent(sim, shots=1024, name="VQE_2Q")
    result = agent.run(task)

    print(f"Optimal cost: {result.value['optimal_cost']:.6f}")
    print(f"Converged: {result.value['converged']}")
    print(f"Circuit evaluations: {result.value['num_evaluations']}")

    costs = agent.opt_history.costs
    print(f"\nConvergence: {costs[0]:.4f} → {costs[-1]:.4f}")

    # Verify the result by running the optimal circuit
    from cvgen.agents.tools import build_variational_ansatz
    from cvgen.core.types import JobConfig

    optimal_circuit = build_variational_ansatz(
        2, depth=2, params=result.value["optimal_params"]
    )
    optimal_circuit.measure_all()
    verification = sim.execute(optimal_circuit, JobConfig(shots=5000, seed=42))

    print("\nVerification (optimal circuit, 5000 shots):")
    for bs, count in sorted(verification.counts.items(), key=lambda x: -x[1]):
        prob = count / verification.shots
        bar = "█" * int(prob * 30)
        print(f"  |{bs}⟩: {prob:.1%} {bar}")


if __name__ == "__main__":
    main()
