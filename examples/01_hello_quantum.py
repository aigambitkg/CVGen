#!/usr/bin/env python3
"""Hello Quantum: Basic circuit execution with CVGen.

Demonstrates:
- Creating a quantum circuit
- Building a Bell state (maximally entangled pair)
- Executing on the built-in simulator
- Analyzing measurement results
"""

from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import JobConfig


def main():
    # Create a 2-qubit quantum circuit
    qc = QuantumCircuit(2)
    qc.name = "Bell State"

    # Build a Bell state: (|00⟩ + |11⟩) / √2
    qc.h(0)       # Hadamard on qubit 0 → superposition
    qc.cx(0, 1)   # CNOT → entanglement
    qc.measure_all()

    print(f"Circuit: {qc}")
    print(f"  Depth: {qc.depth}")
    print(f"  Gates: {qc.gate_count}")
    print()

    # Execute on the built-in simulator
    sim = StateVectorSimulator()
    config = JobConfig(shots=10000, seed=42)
    result = sim.execute(qc, config)

    # Analyze results
    print("Measurement Results:")
    for bitstring, count in sorted(result.counts.items()):
        prob = count / result.shots
        bar = "█" * int(prob * 40)
        print(f"  |{bitstring}⟩: {count:5d} ({prob:.1%}) {bar}")

    print(f"\nMost likely outcome: |{result.most_likely()}⟩")
    print()

    # Demonstrate statevector mode
    sv = sim.run_statevector(qc)
    print("Statevector (before measurement):")
    for i, amp in enumerate(sv):
        if abs(amp) > 1e-10:
            bitstring = format(i, f"0{qc.num_qubits}b")
            print(f"  |{bitstring}⟩: {amp:.4f} (prob={abs(amp)**2:.4f})")

    # GHZ state example
    print("\n--- 3-Qubit GHZ State ---")
    ghz = QuantumCircuit(3)
    ghz.name = "GHZ"
    ghz.h(0)
    for i in range(1, 3):
        ghz.cx(0, i)
    ghz.measure_all()

    result = sim.execute(ghz, JobConfig(shots=5000, seed=42))
    print("Measurement Results:")
    for bitstring, count in sorted(result.counts.items()):
        prob = count / result.shots
        print(f"  |{bitstring}⟩: {count:5d} ({prob:.1%})")


if __name__ == "__main__":
    main()
