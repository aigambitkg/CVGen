# Quantum Computing Patterns and Best Practices

## Pattern 1: Bell State (Entanglement)

Bell states are fundamental for demonstrating quantum entanglement and are building blocks for quantum protocols.

**Use cases**: Bell state test, teleportation, superdense coding

```python
from qpanda3 import *

prog = cq_program()
q0, q1 = prog.allocate_qubits(2)
c0, c1 = prog.allocate_cbits(2)

# Create |Φ+⟩ = (|00⟩ + |11⟩)/√2
prog << H(q0)
prog << CNOT(q0, q1)

prog << measure(q0, c0)
prog << measure(q1, c1)

result = run(prog, "qsim", shots=1000)
```

**Properties**:
- Perfect correlation: measurement results always match
- Demonstrates quantum entanglement
- Used in quantum key distribution

---

## Pattern 2: GHZ State (Multi-Qubit Entanglement)

Generalization of Bell states to three or more qubits.

```python
prog = cq_program()
qubits = prog.allocate_qubits(3)
cbits = prog.allocate_cbits(3)

# Create |GHZ⟩ = (|000⟩ + |111⟩)/√2
prog << H(qubits[0])
for i in range(1, len(qubits)):
    prog << CNOT(qubits[0], qubits[i])

prog << measure(qubits, cbits)
result = run(prog, "qsim", shots=1000)
```

**Properties**:
- All qubits are entangled together
- Used in quantum teleportation of multi-qubit states
- Critical for quantum error correction

---

## Pattern 3: W State

Another important multi-qubit entangled state with different properties than GHZ.

```python
def create_w_state(prog, qubits):
    """
    Create W state: (|001⟩ + |010⟩ + |100⟩)/√3
    All qubits in superposition with equal probability
    """
    n = len(qubits)

    # First qubit: H
    prog << H(qubits[0])

    # Recursive controlled rotations
    for i in range(1, n):
        angle = 2 * np.arccos(1 / np.sqrt(n - i + 1))
        prog << CRY(qubits[0], qubits[i], angle)

prog = cq_program()
qubits = prog.allocate_qubits(3)
cbits = prog.allocate_cbits(3)

create_w_state(prog, qubits)

prog << measure(qubits, cbits)
result = run(prog, "qsim", shots=1000)
```

---

## Pattern 4: Superposition Sweep

Initialize all qubits in equal superposition to explore all possible states.

```python
def create_superposition(prog, qubits):
    """Create equal superposition of all 2^n basis states"""
    for q in qubits:
        prog << H(q)
    return prog

prog = cq_program()
qubits = prog.allocate_qubits(4)
cbits = prog.allocate_cbits(4)

create_superposition(prog, qubits)

prog << measure(qubits, cbits)
result = run(prog, "qsim", shots=1000)

# Should see all 16 states roughly equally
print(f"Unique states observed: {len(result.get_counts())}")
```

---

## Pattern 5: Quantum Phase Kickback

Used in Shor's algorithm and phase estimation. Phase information is transferred to control qubit.

```python
def phase_kickback_setup(prog, control, target, phase):
    """
    Demonstrate phase kickback:
    Apply Z^phase to target (eigenstate |1⟩)
    Control qubit picks up phase
    """
    # Prepare target in |1⟩ eigenstate
    prog << X(target)

    # Create control superposition
    prog << H(control)

    # Controlled phase rotation
    prog << CRZ(control, target, 2 * phase)

    # Phase appears in control qubit state

prog = cq_program()
q_control, q_target = prog.allocate_qubits(2)
c_control, c_target = prog.allocate_cbits(2)

phase_kickback_setup(prog, q_control, q_target, np.pi / 4)

# Hadamard on control to measure phase
prog << H(q_control)

prog << measure([q_control, q_target], [c_control, c_target])
result = run(prog, "qsim", shots=1000)
```

---

## Pattern 6: Oracle Pattern

Generic template for implementing oracles in quantum algorithms.

```python
def oracle_template(prog, working_qubits, oracle_type='marked'):
    """
    Generic oracle pattern
    Marks specific states by flipping their phase
    """
    if oracle_type == 'constant_0':
        # Identity - no effect
        pass
    elif oracle_type == 'constant_1':
        # Global phase flip (unobservable)
        prog << Z(working_qubits[0])
    elif oracle_type == 'balanced':
        # Flip phase of states where x_0 = 1
        prog << Z(working_qubits[0])
    elif oracle_type == 'marked':
        # Flip phase of marked state (e.g., |11⟩ in 2 qubits)
        # Multi-controlled Z gate
        prog << CZ(working_qubits[0], working_qubits[1])

# Usage in algorithm
prog = cq_program()
qubits = prog.allocate_qubits(2)

# Setup superposition
for q in qubits:
    prog << H(q)

# Apply oracle
oracle_template(prog, qubits, 'marked')

# Continue algorithm...
```

---

## Pattern 7: Amplitude Amplification (Grover)

Amplify probability of desired states.

```python
def diffusion_operator(prog, qubits):
    """
    General amplitude amplification operator
    Part of Grover's algorithm
    """
    # H on all qubits
    for q in qubits:
        prog << H(q)

    # X on all qubits
    for q in qubits:
        prog << X(q)

    # Multi-controlled Z on all except last
    prog << Z(qubits[0])

    # X on all qubits
    for q in qubits:
        prog << X(q)

    # H on all qubits
    for q in qubits:
        prog << H(q)

def grovers_algorithm(prog, qubits, iterations):
    """Grover's search algorithm"""
    # Initialize superposition
    for q in qubits:
        prog << H(q)

    # Grover iterations
    for _ in range(iterations):
        # Oracle (marks target state)
        oracle_template(prog, qubits, 'marked')

        # Amplification
        diffusion_operator(prog, qubits)

prog = cq_program()
qubits = prog.allocate_qubits(3)

# Optimal iterations for searching 2^n items
iterations = int(np.pi / 4 * np.sqrt(2**len(qubits)))
grovers_algorithm(prog, qubits, iterations)

cbits = prog.allocate_cbits(3)
prog << measure(qubits, cbits)

result = run(prog, "qsim", shots=1000)
```

---

## Pattern 8: Parameterized Circuit

Template for variational quantum algorithms (VQE, QAOA, etc.).

```python
def parameterized_ansatz(prog, qubits, params):
    """
    Ansatz circuit with adjustable parameters
    Used in VQE and other variational algorithms
    """
    # Rotation layer 1
    for i, q in enumerate(qubits):
        prog << RY(q, params[i])
        prog << RZ(q, params[i + len(qubits)])

    # Entangling layer
    for i in range(len(qubits) - 1):
        prog << CNOT(qubits[i], qubits[i + 1])

    # Rotation layer 2
    for i, q in enumerate(qubits):
        offset = 2 * len(qubits)
        prog << RY(q, params[offset + i])
        prog << RZ(q, params[offset + i + len(qubits)])

def evaluate_ansatz(params, qubits, observable='Z'):
    """Evaluate expectation value with given parameters"""
    prog = cq_program()

    parameterized_ansatz(prog, qubits, params)

    # Basis rotation if needed
    if observable == 'X':
        for q in qubits:
            prog << H(q)
    elif observable == 'Y':
        for q in qubits:
            prog << RX(q, np.pi / 2)

    cbits = prog.allocate_cbits(len(qubits))
    prog << measure(qubits, cbits)

    result = run(prog, "qsim", shots=1000)
    counts = result.get_counts()

    # Compute expectation value
    expectation = 0
    for bitstring, count in counts.items():
        eigenvalue = 1 if bitstring[0] == '0' else -1
        expectation += eigenvalue * count / 1000

    return expectation

# Usage in VQE-like algorithm
from scipy.optimize import minimize

prog = cq_program()
qubits = prog.allocate_qubits(2)

initial_params = np.random.random(4 * len(qubits))
result = minimize(
    lambda p: evaluate_ansatz(p, qubits, 'Z'),
    initial_params,
    method='COBYLA'
)
```

---

## Pattern 9: Circuit Decomposition

Break complex gates into basic gates.

```python
def decompose_controlled_rotations(prog, control, target, angle):
    """
    Decompose controlled rotation into basic gates
    CRX(θ) = H • CRZ(θ) • H
    """
    prog << H(target)
    prog << CRZ(control, target, angle)
    prog << H(target)

def decompose_toffoli(prog, ctrl1, ctrl2, target):
    """
    Decompose Toffoli into CNOTs and single-qubit gates
    Uses CX = H • CZ • H
    """
    prog << H(target)
    prog << CNOT(ctrl2, target)
    prog << T(target).dagger()
    prog << CNOT(ctrl1, target)
    prog << T(target)
    prog << CNOT(ctrl2, target)
    prog << T(target).dagger()
    prog << CNOT(ctrl1, target)
    prog << T(ctrl2)
    prog << T(target)
    prog << CNOT(ctrl1, ctrl2)
    prog << H(target)
```

---

## Pattern 10: Measurement and Post-processing

Classical post-processing of quantum measurement results.

```python
def measure_observable(prog, qubits, observable='Z'):
    """
    Measure an observable: Z (computational), X, or Y basis
    """
    # Basis rotation
    if observable == 'X':
        for q in qubits:
            prog << H(q)
    elif observable == 'Y':
        for q in qubits:
            prog << RX(q, np.pi / 2)

    # Measurement
    cbits = prog.allocate_cbits(len(qubits))
    prog << measure(qubits, cbits)

    return prog

def compute_expectation_value(counts, observable='Z'):
    """
    Convert measurement counts to expectation value
    <O> = Σ_i (eigenvalue_i * count_i) / total_shots
    """
    expectation = 0
    total_shots = sum(counts.values())

    for bitstring, count in counts.items():
        # For Z observable: eigenvalue = 1 if bit is 0, -1 if 1
        eigenvalue = 1 if bitstring[0] == '0' else -1
        expectation += eigenvalue * count / total_shots

    return expectation

def compute_probability_distribution(counts):
    """Get probability distribution from measurement counts"""
    total_shots = sum(counts.values())
    probabilities = {state: count / total_shots for state, count in counts.items()}
    return probabilities

# Usage
prog = cq_program()
qubits = prog.allocate_qubits(2)

# Add quantum circuit...
for q in qubits:
    prog << H(q)

# Measure Z observable
measure_observable(prog, qubits, 'Z')

result = run(prog, "qsim", shots=1000)
counts = result.get_counts()

expectation = compute_expectation_value(counts, 'Z')
print(f"<Z> = {expectation}")

probabilities = compute_probability_distribution(counts)
print(f"Probabilities: {probabilities}")
```

---

## Best Practices Summary

1. **Initialization**: Always initialize qubits in known state (|0⟩ is default)
2. **Superposition**: Use Hadamard for equal superposition
3. **Entanglement**: Use CNOT for pairwise entanglement, CZ for phase entanglement
4. **Measurement**: Measure in appropriate basis (default Z, but X/Y with rotations)
5. **Variational**: Use parameterized ansätze for VQE and similar algorithms
6. **Optimization**: Classical optimizer updates parameters based on quantum measurements
7. **Simulation**: Test on simulator before hardware
8. **Noise**: Consider noise models on simulators for realistic predictions

---

**Pattern Collection**: Essential quantum computing patterns
**Framework**: QPanda3
**Last Updated**: 2026-03-18
