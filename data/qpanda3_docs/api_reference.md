# QPanda3 API Reference

## Core Module: qpanda3

### Program Creation

```python
from qpanda3 import *

# Create an empty quantum program
prog = cq_program()

# Allocate qubits (quantum bits)
qubits = prog.allocate_qubits(n)  # Returns list of n qubits

# Allocate classical bits for measurement
cbits = prog.allocate_cbits(n)   # Returns list of n classical bits
```

## Single-Qubit Gates

### Clifford Gates

```python
# Hadamard - creates equal superposition
H(qubit)

# Pauli gates
X(qubit)  # Pauli-X (NOT gate)
Y(qubit)  # Pauli-Y
Z(qubit)  # Pauli-Z (phase flip)

# Clifford phase gates
S(qubit)  # Phase gate (applies π/2 phase)
T(qubit)  # T gate (applies π/4 phase)
```

### Rotation Gates

```python
# Rotations around axes (angle in radians)
RX(qubit, angle)  # Rotation around X-axis
RY(qubit, angle)  # Rotation around Y-axis
RZ(qubit, angle)  # Rotation around Z-axis

# General rotation
U3(qubit, theta, phi, lambda)  # General single-qubit unitary
```

## Two-Qubit Gates

### Standard Two-Qubit Gates

```python
# Controlled NOT (CNOT/CX)
CNOT(control_qubit, target_qubit)
CX(control_qubit, target_qubit)  # Alias for CNOT

# Controlled Z
CZ(control_qubit, target_qubit)

# Controlled Y
CY(control_qubit, target_qubit)

# iSWAP
iSWAP(qubit1, qubit2)

# SWAP
SWAP(qubit1, qubit2)
```

### Parametric Two-Qubit Gates

```python
# Controlled rotations
CRX(control, target, angle)
CRY(control, target, angle)
CRZ(control, target, angle)

# XX, YY, ZZ interactions
XX(qubit1, qubit2, angle)
YY(qubit1, qubit2, angle)
ZZ(qubit1, qubit2, angle)
```

## Multi-Qubit Gates

```python
# Toffoli (Controlled-Controlled-NOT)
Toffoli(control1, control2, target)
CCX(control1, control2, target)  # Alias

# Fredkin (Controlled-SWAP)
Fredkin(control, target1, target2)
CSWAP(control, target1, target2)  # Alias

# Multi-controlled gates
controlled_gate(base_gate, control_qubits)
```

## Circuit Construction

### Adding Gates to Program

```python
# Single gate
prog << H(qubit)

# Multiple gates (chaining)
prog << H(qubit1) << X(qubit2) << CNOT(qubit1, qubit2)

# Gate sequences
for i in range(n):
    prog << H(qubits[i])
    prog << RZ(qubits[i], angles[i])
```

### Circuits (Sub-programs)

```python
# Create a sub-circuit (function returning operations)
def bell_circuit(q0, q1):
    circuit = QCircuit()
    circuit << H(q0)
    circuit << CNOT(q0, q1)
    return circuit

# Use in main program
prog << bell_circuit(qubits[0], qubits[1])
```

## Measurement

### Measuring Qubits

```python
# Measure in computational basis (Z basis)
prog << measure(qubit, classical_bit)

# Measure multiple qubits
prog << measure(qubits_list, cbits_list)

# Measure single qubit to multiple classical bits (not standard)
prog << measure(qubit, cbit)
```

### Measurement Results

```python
# Access measurement counts
counts = result.get_counts()  # Returns {outcome: count}
# Example: {'00': 512, '11': 488}

# Get counts as probabilities
probs = result.get_probabilities()

# Get individual measurements
shots = result.get_shots()  # All individual measurement results
```

## Execution

### Running Circuits

```python
# Run on different backends
# Simulator
result = run(prog, "qsim", shots=1000)

# Quantum Virtual Machine
result = run(prog, "qvm", shots=1000)

# Origin Pilot
result = run(prog, "origin-pilot", shots=1000)

# IBM Quantum (requires token)
result = run(prog, "ibm", shots=1000, backend="ibm_brisbane")

# AWS Braket (requires credentials)
result = run(prog, "braket", shots=1000)
```

### Advanced Execution Options

```python
# Get state vector (only simulators)
result = run(prog, "qsim", mode="state_vector")

# Get unitary matrix
unitary = get_unitary(prog)

# Partial trace (reduced density matrix)
reduced_dm = partial_trace(prog, keep_qubits=[0, 1])
```

## Circuit Analysis

### Circuit Information

```python
# Get number of qubits and classical bits
n_qubits = prog.get_qubit_num()
n_cbits = prog.get_cbit_num()

# Get circuit depth
depth = prog.get_circuit_depth()

# Count gate types
gate_counts = prog.count_gates()  # Returns {gate_type: count}
```

### Circuit Transformations

```python
# Optimize circuit
optimized = prog.optimization()

# Get circuit matrix representation
circuit_matrix = prog.get_circuit_matrix()

# Reverse circuit (hermitian conjugate)
reversed_prog = prog.dagger()
```

## Error Handling

```python
try:
    result = run(prog, "qsim", shots=1000)
    counts = result.get_counts()
except QFileError as e:
    print(f"File error: {e}")
except QException as e:
    print(f"Quantum exception: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Common Patterns

### Bell State (Entanglement)

```python
prog = cq_program()
q0, q1 = prog.allocate_qubits(2)

prog << H(q0)
prog << CNOT(q0, q1)
```

### Superposition

```python
prog = cq_program()
qubits = prog.allocate_qubits(3)

for q in qubits:
    prog << H(q)
```

### Phase Kickback

```python
prog = cq_program()
q_control, q_target = prog.allocate_qubits(2)

prog << X(q_target)  # |-> state
prog << H(q_target)
prog << CNOT(q_control, q_target)
```

## Backend-Specific Features

### Ollama LLM Integration

CVGen uses Ollama for natural language to quantum circuit conversion using this API.

### Origin Pilot Features

- ZMQ-based distributed quantum processing
- Telemetry and metrics collection
- Job queuing and scheduling

### Cloud Backends

IBM Quantum, AWS Braket, and Azure Quantum support:
- Real hardware execution
- Error mitigation techniques
- Job queuing and monitoring
- Billing and resource management

---

**API Version**: QPanda3 3.x
**Last Updated**: 2026-03-18
