"""Linear algebra utilities for quantum simulation."""

from __future__ import annotations

import numpy as np


def tensor_product(*matrices: np.ndarray) -> np.ndarray:
    """Compute the tensor (Kronecker) product of multiple matrices."""
    result = matrices[0]
    for m in matrices[1:]:
        result = np.kron(result, m)
    return result


def normalize_statevector(sv: np.ndarray) -> np.ndarray:
    """Normalize a statevector to unit length."""
    norm = np.linalg.norm(sv)
    if norm < 1e-15:
        raise ValueError("Cannot normalize zero vector")
    return sv / norm


def partial_trace(statevector: np.ndarray, num_qubits: int, keep: list[int]) -> np.ndarray:
    """Compute the reduced density matrix by tracing out qubits not in 'keep'."""
    rho = np.outer(statevector, np.conj(statevector))
    dim = 2**num_qubits
    assert rho.shape == (dim, dim)

    trace_out = sorted(set(range(num_qubits)) - set(keep))
    if not trace_out:
        return rho

    # Reshape into tensor with 2 indices per qubit
    shape = [2] * (2 * num_qubits)
    rho_tensor = rho.reshape(shape)

    # Trace out qubits from highest index to lowest to maintain index validity
    for q in reversed(trace_out):
        rho_tensor = np.trace(
            rho_tensor, axis1=q, axis2=q + num_qubits - (num_qubits - len(shape) // 2)
        )

    keep_dim = 2 ** len(keep)
    return rho_tensor.reshape(keep_dim, keep_dim)


def fidelity(state_a: np.ndarray, state_b: np.ndarray) -> float:
    """Compute the fidelity between two pure states (statevectors)."""
    return float(abs(np.vdot(state_a, state_b)) ** 2)
