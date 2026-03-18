#!/usr/bin/env python3
"""Quantum Agent: Grover's search algorithm.

Demonstrates:
- Using the QuantumAgent for unstructured search
- Grover's algorithm amplifying the correct answer
- Agent perceive → decide → act loop
"""

from cvgen.agents.quantum_agent import QuantumAgent, SearchTask
from cvgen.backends.simulator import StateVectorSimulator


def main():
    sim = StateVectorSimulator()

    # --- Example 1: 2-qubit search (4 states) ---
    print("=== Grover Search: 2-qubit (4 states) ===")
    target_2q = 3  # Find |11⟩

    task = SearchTask(
        num_qubits=2,
        oracle_fn=lambda x: x == target_2q,
        max_solutions=1,
    )

    agent = QuantumAgent(sim, shots=1024, name="Grover2Q")
    result = agent.run(task)

    print(f"Target: |{format(target_2q, '02b')}⟩ (decimal {target_2q})")
    print(f"Solutions found: {result.value}")
    print(f"Steps taken: {result.total_steps}")
    print(f"Quantum circuits executed: {len(result.quantum_results)}")

    if result.quantum_results:
        last_result = result.quantum_results[-1]
        print("\nFinal measurement distribution:")
        for bs, count in sorted(last_result.counts.items(), key=lambda x: -x[1]):
            prob = count / last_result.shots
            bar = "█" * int(prob * 30)
            print(f"  |{bs}⟩: {prob:.1%} {bar}")

    # --- Example 2: 3-qubit search (8 states) ---
    print("\n=== Grover Search: 3-qubit (8 states) ===")
    target_3q = 5  # Find |101⟩

    task = SearchTask(
        num_qubits=3,
        oracle_fn=lambda x: x == target_3q,
        max_solutions=1,
    )

    agent = QuantumAgent(sim, shots=2048, name="Grover3Q")
    result = agent.run(task)

    print(f"Target: |{format(target_3q, '03b')}⟩ (decimal {target_3q})")
    print(f"Solutions found: {result.value}")
    print(f"Steps taken: {result.total_steps}")

    if result.quantum_results:
        last_result = result.quantum_results[-1]
        print("\nFinal measurement distribution:")
        for bs, count in sorted(last_result.counts.items(), key=lambda x: -x[1])[:5]:
            prob = count / last_result.shots
            bar = "█" * int(prob * 30)
            print(f"  |{bs}⟩: {prob:.1%} {bar}")

    # --- Example 3: Multiple solutions ---
    print("\n=== Grover Search: Multiple Solutions ===")
    targets = {2, 5}  # Find |010⟩ and |101⟩

    task = SearchTask(
        num_qubits=3,
        oracle_fn=lambda x: x in targets,
        max_solutions=2,
    )

    agent = QuantumAgent(sim, shots=2048, name="GroverMulti")
    solutions = agent.run_search(task)

    print(f"Targets: {[format(t, '03b') for t in targets]}")
    print(f"Found: {[format(s, '03b') for s in solutions]}")
    print(f"All targets found: {targets.issubset(set(solutions))}")


if __name__ == "__main__":
    main()
