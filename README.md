# CVGen — AI Agent Framework for Quantum Operating Systems

A Python framework for building autonomous AI agents that leverage quantum computing resources. Designed to work with quantum operating systems like **Origin Pilot** and backend-agnostic across IBM Qiskit, Google Cirq, and other quantum platforms.

## Features

- **Quantum Circuit Engine** — Build, compose, and optimize quantum circuits with a fluent Python API
- **Built-in Simulator** — NumPy-based state vector simulator (no external hardware needed)
- **AI Agent Framework** — Autonomous agents with perceive → decide → act loops
- **Grover Search Agent** — Quantum-accelerated unstructured search
- **Hybrid VQE Agent** — Variational quantum-classical optimization
- **Task Orchestrator** — Route jobs to the best available quantum backend
- **Circuit Optimizer** — Reduce gate count and circuit depth automatically
- **Multi-Backend Support** — Origin Pilot (QPanda), IBM Qiskit, built-in simulator
- **Monitoring** — Track circuit metrics, execution times, and agent performance

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run examples
python examples/01_hello_quantum.py    # Bell state + GHZ state
python examples/02_quantum_agent.py    # Grover's search algorithm
python examples/03_hybrid_vqe.py       # Variational Quantum Eigensolver

# Run tests
pytest tests/ -v
```

## Usage

### Build and Execute a Quantum Circuit

```python
from cvgen import QuantumCircuit, JobConfig
from cvgen.backends.simulator import StateVectorSimulator

# Create a Bell state circuit
qc = QuantumCircuit(2)
qc.h(0).cx(0, 1).measure_all()

# Execute on the built-in simulator
sim = StateVectorSimulator()
result = sim.execute(qc, JobConfig(shots=1000))
print(result.counts)       # {'00': ~500, '11': ~500}
print(result.most_likely()) # '00' or '11'
```

### Run a Quantum Search Agent

```python
from cvgen.agents.quantum_agent import QuantumAgent, SearchTask
from cvgen.backends.simulator import StateVectorSimulator

sim = StateVectorSimulator()
agent = QuantumAgent(sim, shots=1024)

# Search for x=5 in a 3-qubit space (8 states)
task = SearchTask(
    num_qubits=3,
    oracle_fn=lambda x: x == 5,
    max_solutions=1,
)
solutions = agent.run_search(task)
print(f"Found: {solutions}")  # [5]
```

### Hybrid Quantum-Classical Optimization (VQE)

```python
from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask
from cvgen.backends.simulator import StateVectorSimulator

sim = StateVectorSimulator()
agent = HybridAgent(sim, shots=512)

task = VariationalTask(
    num_qubits=1,
    cost_observable={"0": 0.0, "1": 1.0},  # Minimize P(|1⟩)
    ansatz_depth=1,
    max_iterations=50,
)
result = agent.run(task)
print(f"Optimal cost: {result.value['optimal_cost']:.4f}")
```

### Use with Origin Pilot

```python
from cvgen.backends.origin_pilot import OriginPilotBackend

# Automatically falls back to built-in simulator if QPanda is not installed
backend = OriginPilotBackend()

qc = QuantumCircuit(2)
qc.h(0).cx(0, 1).measure_all()
result = backend.execute(qc)
```

## Architecture

```
┌─────────────────────────────────────────────┐
│                AI Agents                     │
│  QuantumAgent │ HybridAgent │ Custom Agents  │
├─────────────────────────────────────────────┤
│             Orchestrator                     │
│  TaskScheduler │ CircuitOptimizer │ Pipeline │
├─────────────────────────────────────────────┤
│           Quantum Backends                   │
│  Simulator │ Origin Pilot │ Qiskit │ ...     │
├─────────────────────────────────────────────┤
│              Core Engine                     │
│  QuantumCircuit │ Gates │ Types │ Registry   │
└─────────────────────────────────────────────┘
```

## Supported Gates

| Gate | Type | Description |
|------|------|-------------|
| H | Single | Hadamard |
| X, Y, Z | Single | Pauli gates |
| S, T | Single | Phase gates |
| RX, RY, RZ | Parametric | Rotation gates |
| CX (CNOT) | Two-qubit | Controlled-X |
| CZ | Two-qubit | Controlled-Z |
| SWAP | Two-qubit | Swap |
| CCX (Toffoli) | Three-qubit | Controlled-controlled-X |

## Requirements

- Python 3.11+
- NumPy >= 1.24
- SciPy >= 1.10

## License

MIT
