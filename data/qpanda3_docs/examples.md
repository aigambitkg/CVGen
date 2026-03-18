# QPanda3 Code Examples

## Example 1: Bell State (Maximum Entanglement)

A Bell state creates perfect quantum entanglement between two qubits. The measurement results are always correlated: if qubit 0 is |0⟩, qubit 1 is always |0⟩, and vice versa.

```python
from qpanda3 import *

# Create program
prog = cq_program()
q0, q1 = prog.allocate_qubits(2)
c0, c1 = prog.allocate_cbits(2)

# Create Bell state: (|00⟩ + |11⟩) / √2
prog << H(q0)                    # Create superposition on q0
prog << CNOT(q0, q1)             # Entangle q0 and q1

# Measure both qubits
prog << measure(q0, c0)
prog << measure(q1, c1)

# Execute
result = run(prog, "qsim", shots=1000)
print("Bell State Results:", result.get_counts())
# Output: {'00': 490, '11': 510}
```

## Example 2: Superposition of Three Qubits

Create an equal superposition of all 8 basis states using Hadamard gates.

```python
from qpanda3 import *

prog = cq_program()
qubits = prog.allocate_qubits(3)
cbits = prog.allocate_cbits(3)

# Apply Hadamard to each qubit
for q in qubits:
    prog << H(q)

# Measure all qubits
prog << measure(qubits, cbits)

# Execute
result = run(prog, "qsim", shots=1000)
counts = result.get_counts()

# All 8 states should appear roughly equally
for state in ['000', '001', '010', '011', '100', '101', '110', '111']:
    print(f"{state}: {counts.get(state, 0)}")
```

## Example 3: Grover's Algorithm (2-Qubit Search)

Find a marked element in an unstructured list quadratically faster than classical search.

```python
from qpanda3 import *
import math

def oracle(prog, qubits, marked):
    """Mark the target state by flipping its phase"""
    # For marked state |marked⟩, apply Z gate
    # This is simplified - full version requires multi-controlled gates
    if marked % 2 == 1:
        prog << Z(qubits[0])

def diffusion(prog, qubits):
    """Amplitude amplification operator"""
    # Apply 2^n Hadamard
    for q in qubits:
        prog << H(q)

    # Apply 2^n (2|0⟩⟨0| - I)
    for q in qubits:
        prog << X(q)

    prog << Z(qubits[0])

    for q in qubits:
        prog << X(q)

    for q in qubits:
        prog << H(q)

# Setup: 2 qubits can encode 4 states, search for marked state
prog = cq_program()
qubits = prog.allocate_qubits(2)
cbits = prog.allocate_cbits(2)

# Initialize superposition
for q in qubits:
    prog << H(q)

# Apply Grover iteration (optimal for 2 qubits is 1 iteration)
iterations = int(math.pi / 4 * math.sqrt(2**2))
for _ in range(iterations):
    oracle(prog, qubits, marked=1)
    diffusion(prog, qubits)

# Measure
prog << measure(qubits, cbits)

result = run(prog, "qsim", shots=1000)
print("Grover Search Results:", result.get_counts())
# Should show marked state with high probability
```

## Example 4: Quantum Phase Estimation

Estimate the phase of an eigenstate - fundamental for many quantum algorithms.

```python
from qpanda3 import *
import numpy as np

prog = cq_program()
counting_qubits = prog.allocate_qubits(3)  # Precision qubits
state_qubit = prog.allocate_qubits(1)[0]
cbits = prog.allocate_cbits(3)

# Prepare eigenstate (for T gate eigenstate |1⟩, phase is π/4)
prog << X(state_qubit)

# Controlled unitary operations with different powers
# For T gate: controlled-T^(2^k)
for k, control_q in enumerate(counting_qubits):
    prog << H(control_q)
    # Controlled unitary (simplified)
    prog << CZ(control_q, state_qubit)

# Inverse QFT
for j in range(len(counting_qubits)):
    prog << H(counting_qubits[j])
    for k in range(j + 1, len(counting_qubits)):
        angle = 2 * np.pi / (2**(k - j + 1))
        # Controlled phase rotation (simplified)
        prog << RZ(counting_qubits[k], angle)

# Measure counting qubits
prog << measure(counting_qubits, cbits)

result = run(prog, "qsim", shots=1000)
counts = result.get_counts()
print("Phase Estimation Results:", counts)
```

## Example 5: Variational Quantum Eigensolver (VQE)

Find the ground state energy of a Hamiltonian using hybrid quantum-classical optimization.

```python
from qpanda3 import *
import numpy as np
from scipy.optimize import minimize

def vqe_ansatz(theta_list, qubits):
    """Parameterized quantum circuit"""
    prog = cq_program()

    # First rotation layer
    prog << RY(qubits[0], theta_list[0])
    prog << RZ(qubits[0], theta_list[1])
    prog << RY(qubits[1], theta_list[2])
    prog << RZ(qubits[1], theta_list[3])

    # Entangling layer
    prog << CNOT(qubits[0], qubits[1])

    # Second rotation layer
    prog << RY(qubits[0], theta_list[4])
    prog << RZ(qubits[0], theta_list[5])

    return prog

def measure_energy(theta_list, qubits):
    """Evaluate expectation value of Hamiltonian"""
    prog = vqe_ansatz(theta_list, qubits)

    # Measure Z_0 * Z_1 expectation
    cbits = prog.allocate_cbits(2)
    prog << measure(qubits, cbits)

    result = run(prog, "qsim", shots=1000)
    counts = result.get_counts()

    # Calculate <Z_0 Z_1>
    energy = 0
    for bitstring, count in counts.items():
        z0 = 1 if bitstring[0] == '0' else -1
        z1 = 1 if bitstring[1] == '0' else -1
        energy += z0 * z1 * count / 1000

    return energy

# Prepare qubits
prog = cq_program()
qubits = prog.allocate_qubits(2)

# Classical optimization
initial_params = np.random.random(6)
result = minimize(
    measure_energy,
    initial_params,
    args=(qubits,),
    method='COBYLA'
)

print(f"Optimized parameters: {result.x}")
print(f"Minimum energy: {result.fun}")
```

## Example 6: Deutsch-Jozsa Algorithm

Determine if a function is constant or balanced with a single evaluation.

```python
from qpanda3 import *

def deutsch_jozsa_constant(prog, qubits):
    """Constant function oracle: f(x) = 0"""
    pass  # Identity

def deutsch_jozsa_balanced(prog, qubits):
    """Balanced function oracle: f(x) = x_0"""
    prog << X(qubits[-1])
    prog << CNOT(qubits[0], qubits[-1])

prog = cq_program()
input_qubits = prog.allocate_qubits(3)  # n input qubits
output_qubit = prog.allocate_qubits(1)[0]  # 1 output qubit
cbits = prog.allocate_cbits(3)

# Prepare all qubits in superposition
for q in input_qubits:
    prog << H(q)
prog << X(output_qubit)
prog << H(output_qubit)

# Apply oracle (choose one)
deutsch_jozsa_constant(prog, input_qubits + [output_qubit])

# Apply Hadamard to input qubits
for q in input_qubits:
    prog << H(q)

# Measure input qubits
prog << measure(input_qubits, cbits)

result = run(prog, "qsim", shots=1000)
counts = result.get_counts()

# If constant: always measure |00...0⟩
# If balanced: never measure |00...0⟩
print("Deutsch-Jozsa Results:", counts)
```

## Example 7: Quantum Fourier Transform

Fundamental subroutine for many quantum algorithms including Shor's factoring.

```python
from qpanda3 import *
import numpy as np

def qft(prog, qubits):
    """Quantum Fourier Transform"""
    n = len(qubits)

    for j in range(n):
        prog << H(qubits[j])
        for k in range(j + 1, n):
            angle = 2 * np.pi / (2**(k - j + 1))
            # Controlled phase rotation
            prog << CRZ(qubits[k], qubits[j], angle)

    # Swap qubits (reverse order)
    for i in range(n // 2):
        prog << SWAP(qubits[i], qubits[n - 1 - i])

def inverse_qft(prog, qubits):
    """Inverse QFT (hermitian conjugate)"""
    n = len(qubits)

    # Reverse qubits first
    for i in range(n // 2):
        prog << SWAP(qubits[i], qubits[n - 1 - i])

    for j in range(n - 1, -1, -1):
        for k in range(n - 1, j, -1):
            angle = -2 * np.pi / (2**(k - j + 1))
            prog << CRZ(qubits[k], qubits[j], angle)
        prog << H(qubits[j])

# Example: QFT of |5⟩ on 3 qubits
prog = cq_program()
qubits = prog.allocate_qubits(3)
cbits = prog.allocate_cbits(3)

# Encode 5 = 101 in binary
prog << X(qubits[0])
prog << X(qubits[2])

# Apply QFT
qft(prog, qubits)

# Measure
prog << measure(qubits, cbits)

result = run(prog, "qsim", shots=1000)
print("QFT Results:", result.get_counts())
```

## Example 8: Quantum Phase Correction (Error Correction)

Basic quantum error correction using repetition code.

```python
from qpanda3 import *

def repetition_encoding(prog, logical_qubit, physical_qubits):
    """Encode logical qubit into 3 physical qubits"""
    # Copy state to all three qubits
    prog << CNOT(logical_qubit, physical_qubits[0])
    prog << CNOT(logical_qubit, physical_qubits[1])

def extract_syndrome(prog, physical_qubits, syndrome_bits):
    """Extract error syndrome without destroying state"""
    # Parity checks
    prog << CNOT(physical_qubits[0], syndrome_bits[0])
    prog << CNOT(physical_qubits[1], syndrome_bits[0])

    prog << CNOT(physical_qubits[1], syndrome_bits[1])
    prog << CNOT(physical_qubits[2], syndrome_bits[1])

def decode(prog, logical_qubit, physical_qubits):
    """Decode physical qubits back to logical qubit"""
    # Majority voting
    prog << CNOT(physical_qubits[1], logical_qubit)
    prog << CNOT(physical_qubits[2], logical_qubit)

# Setup
prog = cq_program()
logical = prog.allocate_qubits(1)[0]
physical = prog.allocate_qubits(3)
syndrome = prog.allocate_qubits(2)
cbits = prog.allocate_cbits(3)

# Prepare state
prog << H(logical)

# Encode
repetition_encoding(prog, logical, physical)

# Simulate error on first physical qubit
# (in real scenario, this would be environmental decoherence)
prog << X(physical[0])

# Extract syndrome
extract_syndrome(prog, physical, syndrome)

# Decode (in practice, error correction would apply corrections)
decode(prog, logical, physical)

# Measure
prog << measure(physical, cbits)

result = run(prog, "qsim", shots=1000)
print("Error Correction Results:", result.get_counts())
```

---

**Example Set**: Complete quantum computing patterns
**Python Version**: 3.11+
**Last Updated**: 2026-03-18
