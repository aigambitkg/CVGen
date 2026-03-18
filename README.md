# CVGen — Quantum Computing for Every Device

Quantum Computing accessible from any device — laptop, tablet, smartphone, or server. Build quantum circuits visually, run AI-powered quantum agents, and execute on real quantum hardware from IBM, AWS, and Azure.

## What Makes CVGen Different

| Feature | Qiskit | Cirq | PennyLane | **CVGen** |
|---------|--------|------|-----------|-----------|
| Visual Circuit Builder (Web) | No | No | No | **Yes** |
| Mobile-Ready PWA | No | No | No | **Yes** |
| REST API for Any Client | No | No | No | **Yes** |
| AI Agents (Auto-Routing) | No | No | No | **Yes** |
| Multi-Vendor Cloud (IBM+AWS+Azure) | IBM only | Google only | Limited | **All** |
| Zero-Setup Simulator | Yes | Yes | Yes | **Yes** |

**CVGen is the only framework that makes quantum computing accessible via browser on any device, with intelligent AI agents that automatically choose the best algorithm and backend.**

## Quick Start

```bash
# Install (basic — simulator + API)
pip install -e ".[api]"

# Start the quantum server
uvicorn cvgen.api.app:app --reload

# Open browser → http://localhost:8000
# Build circuits visually, run quantum agents, see results
```

### Docker (One Command)

```bash
docker-compose up
# → http://localhost:8000
```

### Python Library

```python
from cvgen import QuantumCircuit, JobConfig
from cvgen.backends.simulator import StateVectorSimulator

# Bell state
qc = QuantumCircuit(2)
qc.h(0).cx(0, 1).measure_all()

result = StateVectorSimulator().execute(qc, JobConfig(shots=1000))
print(result.counts)  # {'00': ~500, '11': ~500}
```

## Features

### Visual Circuit Builder (Web UI)
- Drag-and-drop gate placement (touch + mouse)
- Live circuit diagram rendering
- Result histograms and probability charts
- Backend selector (simulator / IBM / AWS / Azure)
- Mobile-first responsive design (320px+)
- PWA — installable on home screen

### AI Quantum Agents

| Agent | Algorithm | Use Case |
|-------|-----------|----------|
| **QuantumAgent** | Grover's Search | Find items in unsorted data (quadratic speedup) |
| **HybridAgent** | VQE | Molecular simulation, optimization |
| **QAOAAgent** | QAOA | MaxCut, routing, scheduling |
| **QMLAgent** | Quantum ML | Binary classification with quantum kernels |
| **AutoAgent** | Auto-Select | Analyzes problem → picks best algorithm + backend |

```python
from cvgen.agents.auto_agent import AutoAgent, AutoTask

agent = AutoAgent()
result = agent.run(AutoTask(
    problem_type="search",
    data={"target_states": [5, 12]},
    num_qubits=4,
))
print(result.value)  # {'solutions': [5, 12], 'algorithm': 'grover'}
```

### Multi-Vendor Quantum Backends

| Backend | Provider | Type | Setup |
|---------|----------|------|-------|
| `simulator` | Built-in | NumPy simulation | None (always available) |
| `origin_pilot` | Origin Quantum | QPanda | `pip install pyqpanda` |
| `qiskit` | IBM | Local simulator | `pip install cvgen[qiskit]` |
| `ibm_cloud` | IBM Quantum | Real QPU | `export IBM_QUANTUM_TOKEN=...` |
| `aws_braket` | Amazon | IonQ, Rigetti, OQC | `export AWS_DEFAULT_REGION=...` |
| `azure_quantum` | Microsoft | IonQ, Quantinuum | `export AZURE_QUANTUM_RESOURCE_ID=...` |

### REST API

Every feature is accessible via HTTP:

```bash
# Execute a circuit
curl -X POST http://localhost:8000/api/v1/circuits/execute \
  -H "Content-Type: application/json" \
  -d '{"num_qubits": 2, "gates": [{"gate": "h", "targets": [0]}, {"gate": "cx", "targets": [0, 1]}], "shots": 1000}'

# Run Grover search
curl -X POST http://localhost:8000/api/v1/agents/grover \
  -d '{"num_qubits": 3, "target_states": [5], "shots": 1024}'

# Run VQE optimization
curl -X POST http://localhost:8000/api/v1/agents/vqe \
  -d '{"num_qubits": 1, "cost_observable": {"0": 0.0, "1": 1.0}, "max_iterations": 50}'

# List backends
curl http://localhost:8000/api/v1/backends
```

## Architecture

```
                      Any Device (Browser/Mobile/CLI/API Client)
                                    |
                        +-----------+-----------+
                        |     REST API (FastAPI) |
                        |     + Web UI (PWA)     |
                        +-----------+-----------+
                                    |
                    +---------------+---------------+
                    |           AI Agents            |
                    | Quantum | Hybrid | QAOA | QML  |
                    |         | Auto-Agent           |
                    +---------------+---------------+
                                    |
                    +---------------+---------------+
                    |          Orchestrator           |
                    | Scheduler | Optimizer | Pipeline|
                    +---------------+---------------+
                                    |
          +----------+---------+---------+----------+---------+
          | Simulator| Origin  | Qiskit  | IBM Cloud| AWS     | Azure
          | (NumPy)  | Pilot   |         | (QPU)    | Braket  | Quantum
          +----------+---------+---------+----------+---------+
```

## Installation Options

```bash
# Basic (simulator only)
pip install -e .

# With API server
pip install -e ".[api]"

# With specific cloud backend
pip install -e ".[ibm]"       # IBM Quantum
pip install -e ".[braket]"    # AWS Braket
pip install -e ".[azure]"     # Azure Quantum

# Everything
pip install -e ".[api,all-backends,dev]"
```

## Cloud Backend Setup

### IBM Quantum (Free Tier Available)
```bash
export IBM_QUANTUM_TOKEN=your_token_here
# Get token: https://quantum.ibm.com/
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

## Development

```bash
# Install dev dependencies
pip install -e ".[dev,api]"

# Run tests
pytest tests/ -v

# Run API tests
pytest tests/test_api.py -v

# Lint
ruff check src/ tests/
```

## Requirements

- Python 3.11+
- NumPy >= 1.24
- SciPy >= 1.10
- FastAPI >= 0.110 (for API/Web)

## License

MIT
