"""Quantum gate matrix definitions."""

from __future__ import annotations

import numpy as np

# --- Single-qubit gates ---

# Pauli gates
I = np.array([[1, 0], [0, 1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)

# Hadamard
H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

# Phase gates
S = np.array([[1, 0], [0, 1j]], dtype=complex)
T = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)


# --- Parametric single-qubit gates ---

def rx(theta: float) -> np.ndarray:
    """Rotation around X-axis."""
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


def ry(theta: float) -> np.ndarray:
    """Rotation around Y-axis."""
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def rz(theta: float) -> np.ndarray:
    """Rotation around Z-axis."""
    return np.array(
        [[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=complex
    )


# --- Two-qubit gates ---

# CNOT (controlled-X)
CX = np.array(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex
)

# Controlled-Z
CZ = np.array(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, -1]], dtype=complex
)

# SWAP
SWAP = np.array(
    [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex
)

# --- Three-qubit gates ---

# Toffoli (CCX)
CCX = np.eye(8, dtype=complex)
CCX[6, 6] = 0
CCX[7, 7] = 0
CCX[6, 7] = 1
CCX[7, 6] = 1


def get_gate_matrix(gate_name: str, params: tuple[float, ...] = ()) -> np.ndarray:
    """Get the matrix representation of a gate by name."""
    static_gates = {
        "h": H, "x": X, "y": Y, "z": Z, "s": S, "t": T,
        "cx": CX, "cz": CZ, "swap": SWAP, "ccx": CCX, "i": I,
    }
    parametric_gates = {"rx": rx, "ry": ry, "rz": rz}

    if gate_name in static_gates:
        return static_gates[gate_name]
    if gate_name in parametric_gates:
        if not params:
            raise ValueError(f"Gate '{gate_name}' requires parameters")
        return parametric_gates[gate_name](params[0])
    raise ValueError(f"Unknown gate: {gate_name}")
