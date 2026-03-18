"""Reusable tools for quantum agents.

Tools are functions and circuit builders that agents can use
to construct quantum circuits for common tasks.
"""

from __future__ import annotations

import math

import numpy as np

from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult


def build_superposition_circuit(num_qubits: int) -> QuantumCircuit:
    """Build a circuit that creates an equal superposition of all states."""
    qc = QuantumCircuit(num_qubits)
    qc.name = "superposition"
    for i in range(num_qubits):
        qc.h(i)
    qc.measure_all()
    return qc


def build_bell_pair(qubit_a: int = 0, qubit_b: int = 1) -> QuantumCircuit:
    """Build a circuit that creates a Bell pair (maximally entangled state)."""
    n = max(qubit_a, qubit_b) + 1
    qc = QuantumCircuit(n)
    qc.name = "bell_pair"
    qc.h(qubit_a)
    qc.cx(qubit_a, qubit_b)
    qc.measure_all()
    return qc


def build_ghz_state(num_qubits: int) -> QuantumCircuit:
    """Build a GHZ state circuit: (|00...0⟩ + |11...1⟩) / √2."""
    qc = QuantumCircuit(num_qubits)
    qc.name = "ghz"
    qc.h(0)
    for i in range(1, num_qubits):
        qc.cx(0, i)
    qc.measure_all()
    return qc


def build_qrng_circuit(num_bits: int) -> QuantumCircuit:
    """Build a quantum random number generator circuit."""
    qc = QuantumCircuit(num_bits)
    qc.name = "qrng"
    for i in range(num_bits):
        qc.h(i)
    qc.measure_all()
    return qc


def build_grover_oracle(num_qubits: int, target_state: int) -> QuantumCircuit:
    """Build a Grover oracle circuit that marks a target state.

    The oracle flips the phase of the target state |target⟩.
    Uses multi-controlled Z gate decomposition.
    """
    qc = QuantumCircuit(num_qubits)
    qc.name = f"grover_oracle_{target_state}"

    # Flip qubits where target has 0 bits
    for i in range(num_qubits):
        if not (target_state >> (num_qubits - 1 - i)) & 1:
            qc.x(i)

    # Multi-controlled Z: Apply Z to last qubit controlled by all others
    # For 2 qubits: CZ; For 3+: decompose into CX + Toffoli chains
    if num_qubits == 1:
        qc.z(0)
    elif num_qubits == 2:
        qc.cz(0, 1)
    elif num_qubits == 3:
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)
    else:
        # For larger circuits, use simple phase kickback approach
        qc.h(num_qubits - 1)
        # Chain of Toffoli gates (simplified for small circuits)
        for i in range(num_qubits - 2):
            qc.ccx(i, i + 1, min(i + 2, num_qubits - 1))
        qc.h(num_qubits - 1)

    # Unflip
    for i in range(num_qubits):
        if not (target_state >> (num_qubits - 1 - i)) & 1:
            qc.x(i)

    return qc


def build_grover_diffusion(num_qubits: int) -> QuantumCircuit:
    """Build the Grover diffusion operator (amplitude amplification)."""
    qc = QuantumCircuit(num_qubits)
    qc.name = "grover_diffusion"

    # H on all qubits
    for i in range(num_qubits):
        qc.h(i)

    # X on all qubits
    for i in range(num_qubits):
        qc.x(i)

    # Multi-controlled Z
    if num_qubits == 1:
        qc.z(0)
    elif num_qubits == 2:
        qc.cz(0, 1)
    elif num_qubits == 3:
        qc.h(2)
        qc.ccx(0, 1, 2)
        qc.h(2)

    # X on all qubits
    for i in range(num_qubits):
        qc.x(i)

    # H on all qubits
    for i in range(num_qubits):
        qc.h(i)

    return qc


def build_variational_ansatz(
    num_qubits: int, depth: int = 1, params: list[float] | None = None
) -> QuantumCircuit:
    """Build a hardware-efficient variational ansatz.

    Structure per layer:
    - RY rotation on each qubit
    - RZ rotation on each qubit
    - CNOT entangling layer (linear chain)
    """
    num_params = num_qubits * 2 * depth
    if params is None:
        params = [0.0] * num_params
    if len(params) != num_params:
        raise ValueError(f"Expected {num_params} parameters, got {len(params)}")

    qc = QuantumCircuit(num_qubits)
    qc.name = f"variational_d{depth}"
    idx = 0

    for _ in range(depth):
        # RY layer
        for q in range(num_qubits):
            qc.ry(q, params[idx])
            idx += 1
        # RZ layer
        for q in range(num_qubits):
            qc.rz(q, params[idx])
            idx += 1
        # Entangling layer
        for q in range(num_qubits - 1):
            qc.cx(q, q + 1)

    return qc


def optimal_grover_iterations(num_qubits: int, num_solutions: int = 1) -> int:
    """Calculate the optimal number of Grover iterations."""
    n = 2**num_qubits
    return max(1, round(math.pi / 4 * math.sqrt(n / num_solutions)))


def analyze_result(result: CircuitResult) -> dict:
    """Analyze a circuit result and return summary statistics."""
    probs = result.probabilities
    sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)

    # Shannon entropy
    entropy = -sum(p * np.log2(p) for p in probs.values() if p > 0)

    return {
        "most_likely": sorted_probs[0] if sorted_probs else None,
        "num_unique_outcomes": len(probs),
        "entropy": float(entropy),
        "top_5": sorted_probs[:5],
        "shots": result.shots,
    }
