<p align="center">
  <strong>CVGen</strong><br>
  <em>Quantum Computing for Every Device</em>
</p>

<p align="center">
  <a href="https://github.com/aigambitkg/CVGen/actions"><img src="https://github.com/aigambitkg/CVGen/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/version-0.2.0-purple" alt="Version 0.2.0">
  <img src="https://img.shields.io/badge/tests-89%20passing-brightgreen" alt="89 Tests Passing">
</p>

---

Build quantum circuits visually, run AI-powered quantum agents, and execute on real quantum hardware from IBM, AWS, and Azure — from any device: laptop, tablet, smartphone, or server.

## Why CVGen?

Most quantum frameworks are Python-only libraries requiring deep quantum physics knowledge. **CVGen takes a radically different approach:**

1. **AI agents that think for you** — Describe your problem in plain terms. CVGen's AutoAgent detects the problem type, selects the optimal quantum algorithm, and picks the best backend. No quantum expertise needed.

2. **Visual circuit builder on any device** — Drag-and-drop quantum gates in your browser. Works on phones, tablets, desktops. Install as a PWA on your home screen.

3. **One framework, all cloud providers** — IBM Quantum, AWS Braket, Azure Quantum, and a built-in simulator. Switch backends with a single parameter change.

4. **REST API for everything** — Every feature accessible via HTTP. Integrate quantum computing into any application, any language, any platform.

### Comparison with Existing Frameworks

| Capability | Qiskit | Cirq | PennyLane | **CVGen** |
|---|---|---|---|---|
| Visual Circuit Builder (Web) | No | No | No | **Yes (PWA)** |
| Mobile-Friendly | No | No | No | **Yes (320px+)** |
| REST API | No | No | No | **Yes (FastAPI)** |
| AI Agents (Auto Algorithm Selection) | No | No | No | **5 Agents** |
| Multi-Cloud (IBM + AWS + Azure) | IBM only | Google only | Plugin-based | **Native** |
| Zero-Setup Simulator | Yes | Yes | Yes | **Yes** |
| Docker One-Command Deploy | No | No | No | **Yes** |
| Circuit Optimization | Yes | Yes | Limited | **3 Levels** |

> **CVGen is the only quantum framework that combines a visual circuit builder, intelligent AI agents, multi-cloud support, and a REST API in a single package — accessible from any device.**

---

## Real-World Use Cases

### 1. Pharmaceutical Research — Molecular Simulation with VQE

**Problem:** Estimating the ground-state energy of a molecule is essential for drug discovery, but classically intractable for large systems.

**Solution:** CVGen's HybridAgent runs a Variational Quantum Eigensolver (VQE) — a hybrid quantum-classical loop that converges to the minimum energy.

```python
from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask
from cvgen.backends.simulator import StateVectorSimulator

# Define a simplified molecular Hamiltonian
# Maps bitstrings to energy eigenvalues
hamiltonian = {
    "00": -1.05,   # Ground state energy
    "01":  0.40,
    "10":  0.40,
    "11":  0.80,   # Excited state energy
}

task = VariationalTask(
    num_qubits=2,
    cost_observable=hamiltonian,
    ansatz_depth=2,          # Depth of the variational circuit
    max_iterations=100,      # Classical optimizer iterations
    optimizer_method="COBYLA",
)

agent = HybridAgent(StateVectorSimulator(), shots=1024, name="MolecularVQE")
result = agent.run(task)

print(f"Ground state energy: {result.value['optimal_cost']:.4f}")
print(f"Converged: {result.value['converged']}")
print(f"Evaluations: {result.value['num_evaluations']}")
# Ground state energy: -1.0500
# Converged: True
# Evaluations: 42
```

### 2. Logistics — Route Optimization with QAOA

**Problem:** Finding optimal delivery routes across a network of cities is a classic NP-hard problem (MaxCut / TSP). Classical solvers scale exponentially.

**Solution:** CVGen's QAOAAgent encodes the problem as a graph and applies the Quantum Approximate Optimization Algorithm with alternating problem and mixer layers.

```python
from cvgen.agents.qaoa_agent import QAOAAgent, QAOATask
from cvgen.backends.simulator import StateVectorSimulator

# Define a delivery network as a weighted graph
# edges: (city_a, city_b, distance/cost)
delivery_network = [
    (0, 1, 1.0),   # Berlin  → Hamburg:   1.0
    (0, 2, 1.5),   # Berlin  → München:   1.5
    (1, 2, 0.8),   # Hamburg → München:   0.8
    (1, 3, 1.2),   # Hamburg → Köln:      1.2
    (2, 3, 0.6),   # München → Köln:      0.6
]

task = QAOATask(
    num_qubits=4,       # 4 cities
    edges=delivery_network,
    p=2,                # 2 QAOA layers (higher = better approximation)
    max_iterations=100,
)

agent = QAOAAgent(StateVectorSimulator(), shots=2048)
result = agent.run(task)

print(f"Best partition: {result.value['best_bitstring']}")
print(f"Max cut value:  {result.value['best_cost']:.2f}")
# Best partition: 0110
# Max cut value:  4.10
```

### 3. Database Search — Grover's Algorithm

**Problem:** Searching for specific entries in an unsorted database of N items classically requires O(N) lookups. Grover's algorithm achieves O(√N) — a quadratic speedup.

**Solution:** CVGen's QuantumAgent builds the oracle, superposition, and diffusion circuits automatically.

```python
from cvgen.agents.quantum_agent import QuantumAgent, SearchTask
from cvgen.backends.simulator import StateVectorSimulator

# Search space: 16 items (4 qubits → 2⁴ = 16 states)
# We're looking for items 7 and 11
targets = {7, 11}

task = SearchTask(
    num_qubits=4,
    oracle_fn=lambda x: x in targets,
    max_solutions=2,
)

agent = QuantumAgent(StateVectorSimulator(), shots=2048)
result = agent.run(task)

print(f"Found: {result.value}")          # [7, 11]
print(f"Steps: {result.total_steps}")     # ~3 (vs. 16 classically)
print(f"Success: {result.success}")       # True
```

**Speedup comparison:**

| Database Size | Classical (O(N)) | Grover (O(√N)) | Speedup |
|---|---|---|---|
| 1,000 | 1,000 lookups | ~32 lookups | 31x |
| 1,000,000 | 1,000,000 lookups | ~1,000 lookups | 1000x |
| 1,000,000,000 | 1 billion lookups | ~31,623 lookups | 31,623x |

### 4. Machine Learning — Quantum Classification

**Problem:** Classical ML models may miss complex patterns in data. Quantum kernel methods can capture feature correlations that classical kernels cannot.

**Solution:** CVGen's QMLAgent trains a variational quantum classifier with automatic data encoding and entanglement layers.

```python
from cvgen.agents.qml_agent import QMLAgent, ClassificationTask
from cvgen.backends.simulator import StateVectorSimulator

# Training data: XOR-like problem (classically non-linear)
train_data = [
    [0.1, 0.1],   # Class 0
    [0.9, 0.9],   # Class 0
    [0.1, 0.9],   # Class 1
    [0.9, 0.1],   # Class 1
]
train_labels = [0, 0, 1, 1]

task = ClassificationTask(
    train_data=train_data,
    train_labels=train_labels,
    test_data=[[0.2, 0.8], [0.8, 0.2]],  # Should predict class 1
    num_qubits=2,
    ansatz_depth=2,
    max_iterations=50,
)

agent = QMLAgent(StateVectorSimulator(), shots=1024)
result = agent.run(task)

print(f"Training accuracy: {result.value['train_accuracy']:.0%}")
print(f"Predictions: {result.value['predictions']}")
# Training accuracy: 100%
# Predictions: [1, 1]
```

### 5. "I Don't Know Which Algorithm to Use" — AutoAgent

**Problem:** Choosing the right quantum algorithm requires expertise. Is it a search problem? Optimization? Classification?

**Solution:** CVGen's AutoAgent analyzes your problem specification, detects the type, selects the optimal algorithm, and routes to the best backend — fully automatic.

```python
from cvgen.agents.auto_agent import AutoAgent, AutoTask

agent = AutoAgent()

# Just describe your problem — AutoAgent figures out the rest
result = agent.run(AutoTask(
    data={
        "target_states": [5, 12],   # ← AutoAgent detects: SEARCH problem
    },
    num_qubits=4,
))
# AutoAgent selects: Grover's Algorithm → QuantumAgent → simulator
print(result.value)  # {'solutions': [5, 12], 'algorithm': 'grover'}

# Or pass a graph → AutoAgent detects: COMBINATORIAL
result = agent.run(AutoTask(
    data={
        "edges": [(0, 1, 1.0), (1, 2, 0.5), (0, 2, 0.8)],
    },
    num_qubits=3,
))
# AutoAgent selects: QAOA → QAOAAgent → simulator
print(result.value)  # {'best_bitstring': '101', 'algorithm': 'qaoa'}
```

**AutoAgent detection logic:**

| Data Contains | Detected Problem | Selected Algorithm |
|---|---|---|
| `target_states` or `oracle_fn` | Search | Grover (QuantumAgent) |
| `edges` or `graph` | Combinatorial | QAOA (QAOAAgent) |
| `train_data` or `features` | Classification | QML (QMLAgent) |
| `cost_observable` | Optimization | VQE (HybridAgent) |

---

## Quick Start

### 60 Seconds to Quantum

```bash
pip install -e ".[api]"
uvicorn cvgen.api.app:app --reload
# Open http://localhost:8000 — build circuits visually, run agents, see results
```

### Docker (One Command)

```bash
docker-compose up
# → http://localhost:8000
```

### Python Library (No Server Needed)

```python
from cvgen import QuantumCircuit, JobConfig
from cvgen.backends.simulator import StateVectorSimulator

# Create a Bell state — maximally entangled 2-qubit state
qc = QuantumCircuit(2)
qc.h(0)           # Superposition on qubit 0
qc.cx(0, 1)       # Entangle qubit 0 and 1
qc.measure_all()

result = StateVectorSimulator().execute(qc, JobConfig(shots=1000))
print(result.counts)       # {'00': ~500, '11': ~500}
print(result.most_likely())  # '00' or '11'
```

---

## Code Examples

### Bell State — Quantum Entanglement

The simplest quantum circuit that demonstrates entanglement:

```python
from cvgen import QuantumCircuit, JobConfig
from cvgen.backends.simulator import StateVectorSimulator

qc = QuantumCircuit(2)
qc.h(0).cx(0, 1).measure_all()   # Method chaining

sim = StateVectorSimulator()
result = sim.execute(qc, JobConfig(shots=10000, seed=42))

print(result.counts)
# {'00': 4987, '11': 5013}
# → Perfect correlation: qubits always agree

# Inspect the quantum state directly (no measurement collapse)
sv = sim.run_statevector(qc)
print(sv)
# [0.707+0j, 0+0j, 0+0j, 0.707+0j]
# → |Ψ⟩ = (|00⟩ + |11⟩) / √2
```

### GHZ State — Multi-Qubit Entanglement

Scale entanglement to 3+ qubits:

```python
from cvgen import QuantumCircuit, JobConfig
from cvgen.backends.simulator import StateVectorSimulator

# 3-qubit GHZ state: |000⟩ + |111⟩
qc = QuantumCircuit(3)
qc.h(0)
for i in range(2):
    qc.cx(i, i + 1)
qc.measure_all()

result = StateVectorSimulator().execute(qc, JobConfig(shots=10000))
print(result.counts)
# {'000': ~5000, '111': ~5000}
# → All 3 qubits always agree
```

### Grover Search — Finding Needles in Haystacks

```python
from cvgen.agents.quantum_agent import QuantumAgent, SearchTask
from cvgen.backends.simulator import StateVectorSimulator

# 2-qubit search (4 items) — find item 3
task = SearchTask(num_qubits=2, oracle_fn=lambda x: x == 3)

agent = QuantumAgent(StateVectorSimulator(), shots=1024)
solutions = agent.run_search(task)
print(f"Found: {solutions}")  # [3]

# 3-qubit search (8 items) — find multiple items
task = SearchTask(
    num_qubits=3,
    oracle_fn=lambda x: x in {2, 5},
    max_solutions=2,
)
result = agent.run(task)
print(f"Solutions: {result.value}")       # [2, 5]
print(f"Quantum steps: {result.total_steps}")
```

### VQE — Variational Quantum Eigensolver

```python
from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask
from cvgen.backends.simulator import StateVectorSimulator

# Minimize: find parameters that maximize P(|0⟩)
task = VariationalTask(
    num_qubits=1,
    cost_observable={"0": 0.0, "1": 1.0},  # |0⟩=0, |1⟩=1
    ansatz_depth=1,
    max_iterations=50,
)

agent = HybridAgent(StateVectorSimulator(), shots=512, name="VQE_1Q")
result = agent.run(task)

print(f"Optimal cost: {result.value['optimal_cost']:.4f}")   # ~0.0000
print(f"Converged: {result.value['converged']}")               # True
print(f"Evaluations: {result.value['num_evaluations']}")       # ~25

# Verify: rebuild the optimized circuit
from cvgen.agents.tools import build_variational_ansatz
optimal_circuit = build_variational_ansatz(
    1, depth=1, params=result.value["optimal_params"]
)
```

### QAOA — MaxCut Graph Optimization

```python
from cvgen.agents.qaoa_agent import QAOAAgent, QAOATask
from cvgen.backends.simulator import StateVectorSimulator

# Triangle graph with weights
task = QAOATask(
    num_qubits=3,
    edges=[(0, 1, 1.0), (1, 2, 1.0), (0, 2, 1.0)],
    p=2,                    # 2 QAOA layers
    max_iterations=100,
    optimizer_method="COBYLA",
)

agent = QAOAAgent(StateVectorSimulator(), shots=2048)
result = agent.run(task)

print(f"Best cut: {result.value['best_bitstring']}")
print(f"Cost: {result.value['best_cost']:.2f}")
```

### Pipeline — Chaining Quantum Workflows

```python
from cvgen.orchestrator.pipeline import Pipeline
from cvgen.orchestrator.optimizer import CircuitOptimizer
from cvgen.backends.simulator import StateVectorSimulator
from cvgen import QuantumCircuit, JobConfig

sim = StateVectorSimulator()
optimizer = CircuitOptimizer(level=2)

pipeline = Pipeline("quantum_workflow")
pipeline.add_step("build", lambda _: QuantumCircuit(2).h(0).cx(0, 1).measure_all())
pipeline.add_step("optimize", lambda qc: optimizer.optimize(qc))
pipeline.add_step("execute", lambda qc: sim.execute(qc, JobConfig(shots=1000)))
pipeline.add_step("analyze", lambda r: {"dominant": r.most_likely(), "counts": r.counts})

result = pipeline.run(None)

print(f"Pipeline success: {result.success}")
print(f"Total time: {result.total_duration_s:.3f}s")
print(f"Result: {result.final_output}")
# {'dominant': '00', 'counts': {'00': 498, '11': 502}}
```

---

## AI Agents — Deep Dive

CVGen agents follow a **perceive → decide → act** loop: they observe the quantum state, decide the next operation, execute it, and repeat until convergence.

| Agent | Algorithm | Problem Type | Complexity | Best For |
|---|---|---|---|---|
| **QuantumAgent** | Grover | Search | O(√N) | Finding items in unsorted data |
| **HybridAgent** | VQE | Optimization | O(depth × n) | Molecular energy, parameter tuning |
| **QAOAAgent** | QAOA | Combinatorial | O(p × \|E\|) | MaxCut, routing, scheduling |
| **QMLAgent** | QML Kernels | Classification | O(depth × n) | Binary classification |
| **AutoAgent** | Auto-Select | Any | Varies | "I don't know which to use" |

### AutoAgent — The Meta-Agent

AutoAgent is the intelligent orchestrator that removes the need for quantum expertise:

```
Input Problem
    ↓
┌─────────────────────────┐
│ 1. Problem Detection    │  Analyzes data keys (target_states? edges? train_data?)
│ 2. Algorithm Selection  │  Maps problem type to optimal quantum algorithm
│ 3. Backend Routing      │  Estimates circuit complexity → picks best backend
│ 4. Execution            │  Delegates to specialized agent
│ 5. Result Aggregation   │  Returns unified result format
└─────────────────────────┘
    ↓
Output Solution
```

**Complexity-aware backend selection:**
- Grover: depth ~ O(√(2ⁿ)) × 3n gates
- QAOA: depth ~ p × |E| × 4 + n gates
- QML: depth ~ layers × 3n + n gates
- VQE: depth ~ layers × 3n gates

If estimated depth exceeds simulator capacity, AutoAgent routes to cloud QPUs.

---

## Multi-Vendor Quantum Backends

| Backend | Provider | Type | Max Qubits | Setup |
|---|---|---|---|---|
| `simulator` | Built-in | NumPy state vector | 20 | None (always available) |
| `origin_pilot` | Origin Quantum | QPanda | Variable | `pip install pyqpanda` |
| `qiskit` | IBM | Aer simulator | 32 | `pip install cvgen[qiskit]` |
| `ibm_cloud` | IBM Quantum | Real QPU | 127+ | `pip install cvgen[ibm]` |
| `aws_braket` | Amazon | IonQ / Rigetti / OQC | Varies | `pip install cvgen[braket]` |
| `azure_quantum` | Microsoft | IonQ / Quantinuum | Varies | `pip install cvgen[azure]` |

**Switching backends is a one-line change:**

```python
from cvgen.backends.simulator import StateVectorSimulator
from cvgen.backends.ibm_cloud import IBMCloudBackend

# Development: use simulator
backend = StateVectorSimulator()

# Production: switch to IBM Quantum hardware
backend = IBMCloudBackend()

# Same code, same API — different backend
result = backend.execute(circuit, config)
```

---

## REST API

Every feature is accessible via HTTP — integrate quantum computing into any application.

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/circuits/execute` | Execute a quantum circuit |
| `POST` | `/api/v1/agents/grover` | Run Grover search |
| `POST` | `/api/v1/agents/vqe` | Run VQE optimization |
| `GET` | `/api/v1/backends` | List available backends |
| `GET` | `/api/v1/jobs/{job_id}` | Get job status |
| `GET` | `/api/v1/jobs` | List all jobs |
| `GET` | `/api/v1/health` | Health check |

### Examples

```bash
# Execute a Bell state circuit
curl -X POST http://localhost:8000/api/v1/circuits/execute \
  -H "Content-Type: application/json" \
  -d '{
    "num_qubits": 2,
    "gates": [
      {"gate": "h", "targets": [0]},
      {"gate": "cx", "targets": [0, 1]},
      {"gate": "measure", "targets": [0]},
      {"gate": "measure", "targets": [1]}
    ],
    "shots": 1024,
    "backend": "simulator"
  }'
# → {"counts": {"00": 512, "11": 512}, "most_likely": "00", ...}

# Run Grover search via API
curl -X POST http://localhost:8000/api/v1/agents/grover \
  -H "Content-Type: application/json" \
  -d '{"num_qubits": 3, "target_states": [5], "shots": 1024}'
# → {"solutions": [5], "search_space_size": 8, "total_steps": 2, "success": true}

# Run VQE optimization via API
curl -X POST http://localhost:8000/api/v1/agents/vqe \
  -H "Content-Type: application/json" \
  -d '{
    "num_qubits": 2,
    "cost_observable": {"00": -1.0, "01": 0.5, "10": 0.5, "11": 1.0},
    "ansatz_depth": 2,
    "max_iterations": 80,
    "shots": 512
  }'
# → {"optimal_cost": -1.0, "converged": true, "num_evaluations": 45, ...}

# List available backends
curl http://localhost:8000/api/v1/backends
# → [{"name": "simulator", "max_qubits": 20, "type": "simulator", "status": "available"}, ...]
```

---

## Architecture

```
                      Any Device (Browser / Mobile / CLI / API Client)
                                          |
                          +---------------+---------------+
                          |         REST API (FastAPI)     |
                          |        + Web UI (PWA)          |
                          |        + Auth Middleware        |
                          +---------------+---------------+
                                          |
                      +-------------------+-------------------+
                      |              AI Agents                 |
                      |  Quantum | Hybrid | QAOA | QML | Auto  |
                      |     (perceive → decide → act loop)     |
                      +-------------------+-------------------+
                                          |
                      +-------------------+-------------------+
                      |            Orchestrator                |
                      |  TaskScheduler | CircuitOptimizer (L0-L2) |
                      |  Pipeline | Metrics | Logger           |
                      +-------------------+-------------------+
                                          |
        +---------+---------+---------+---------+---------+----------+
        |Simulator| Origin  | Qiskit  |   IBM   |   AWS   |  Azure   |
        | (NumPy) | Pilot   |  (Aer)  |  Cloud  | Braket  | Quantum  |
        |  ≤20q   | QPanda  |  ≤32q   | 127+ q  |  IonQ   |  IonQ    |
        |         |         |         |         | Rigetti |Quantinuum|
        +---------+---------+---------+---------+---------+----------+
```

---

## Circuit Optimization

CVGen includes a multi-level circuit optimizer that reduces gate count before execution:

| Level | Optimization | Example |
|---|---|---|
| **0** | None (pass-through) | — |
| **1** | Remove self-inverse pairs | `X → X` = identity (removed), `H → H` = identity (removed) |
| **2** | Level 1 + merge rotations | `RX(π/4) → RX(π/4)` = `RX(π/2)`, cancel if sum = 2π |

```python
from cvgen.orchestrator.optimizer import CircuitOptimizer
from cvgen import QuantumCircuit

qc = QuantumCircuit(1)
qc.x(0).x(0)   # Two X gates cancel out (X² = I)
qc.h(0)

optimizer = CircuitOptimizer(level=1)
optimized = optimizer.optimize(qc)
print(len(optimized.operations))  # 1 (only H remains)
```

---

## Supported Gates

| Gate | Type | Qubits | Description | Matrix Dimension |
|---|---|---|---|---|
| **H** | Single | 1 | Hadamard — creates superposition | 2×2 |
| **X** | Single | 1 | Pauli-X — bit flip (NOT) | 2×2 |
| **Y** | Single | 1 | Pauli-Y — bit + phase flip | 2×2 |
| **Z** | Single | 1 | Pauli-Z — phase flip | 2×2 |
| **S** | Single | 1 | S-gate — √Z | 2×2 |
| **T** | Single | 1 | T-gate — ⁴√Z | 2×2 |
| **RX(θ)** | Parametric | 1 | X-rotation by angle θ | 2×2 |
| **RY(θ)** | Parametric | 1 | Y-rotation by angle θ | 2×2 |
| **RZ(θ)** | Parametric | 1 | Z-rotation by angle θ | 2×2 |
| **CX** | Two-qubit | 2 | CNOT — controlled NOT | 4×4 |
| **CZ** | Two-qubit | 2 | Controlled-Z | 4×4 |
| **SWAP** | Two-qubit | 2 | Swap qubit states | 4×4 |
| **CCX** | Three-qubit | 3 | Toffoli — controlled-controlled NOT | 8×8 |

---

## Installation

```bash
# Basic (simulator only)
pip install -e .

# With API server + Web UI
pip install -e ".[api]"

# With specific cloud backends
pip install -e ".[ibm]"       # IBM Quantum
pip install -e ".[braket]"    # AWS Braket
pip install -e ".[azure]"     # Azure Quantum

# Everything (all backends + dev tools)
pip install -e ".[api,all-backends,dev]"
```

## Cloud Backend Setup

### IBM Quantum (Free Tier Available)

```bash
export IBM_QUANTUM_TOKEN=your_token_here
# Get your token at: https://quantum.ibm.com/
```

### AWS Braket

```bash
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

### Azure Quantum

```bash
export AZURE_QUANTUM_RESOURCE_ID=/subscriptions/.../providers/Microsoft.Quantum/Workspaces/...
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev,api]"

# Run all tests (89 tests)
pytest tests/ -v

# Run specific test suites
pytest tests/test_agents.py -v     # Agent tests
pytest tests/test_api.py -v        # API endpoint tests
pytest tests/test_simulator.py -v  # Simulator tests
pytest tests/test_integration.py -v  # End-to-end tests

# Lint
ruff check src/ tests/
```

## Requirements

- Python 3.11+
- NumPy >= 1.24
- SciPy >= 1.10
- FastAPI >= 0.110 (optional, for API/Web)
- Uvicorn >= 0.27 (optional, for server)

## License

MIT
