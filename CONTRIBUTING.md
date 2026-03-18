# Contributing to CVGen

Thank you for your interest in contributing to CVGen! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions with the community.

## Getting Started

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/aigambitkg/CVGen.git
cd CVGen
```

2. Create a virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in editable mode with all extras:
```bash
pip install -e ".[dev,api,rag,llm,zmq,all-backends]"
```

4. Install pre-commit hooks (optional but recommended):
```bash
pip install pre-commit
pre-commit install
```

### Development Environment

Required:
- Python 3.11+ (tested on 3.11, 3.12, 3.13)
- pip and venv
- Git

Recommended:
- Docker and docker-compose
- VSCode or PyCharm
- PostgreSQL or MySQL (for future features)

### Optional Services for Local Development

Start optional services with docker-compose:
```bash
docker-compose -f docker-compose.full.yml up -d
```

This starts:
- Ollama (LLM service)
- Qdrant (Vector database)
- Origin Pilot mock server

## Code Style

### Formatting and Linting

We use **ruff** for code linting and formatting.

Check code:
```bash
ruff check src/ tests/
ruff format --check src/ tests/
```

Auto-fix issues:
```bash
ruff check --fix src/ tests/
ruff format src/ tests/
```

Configuration is in `pyproject.toml`:
- Target version: Python 3.11
- Line length: 100 characters
- Per-file ignores: See `pyproject.toml` for exceptions

### Type Hints

We enforce type hints for better code quality:

```python
from __future__ import annotations

def process_circuit(circuit: QuantumCircuit, shots: int) -> CircuitResult:
    """Process a quantum circuit.

    Args:
        circuit: The quantum circuit to process
        shots: Number of measurement shots

    Returns:
        The execution result
    """
    pass
```

Type checking (optional):
```bash
mypy src/ --ignore-missing-imports
```

### Docstring Style

Use Google-style docstrings:

```python
def run_circuit(
    circuit: QuantumCircuit,
    backend: str = "simulator",
) -> CircuitResult:
    """Execute a quantum circuit on specified backend.

    Args:
        circuit: The quantum circuit to execute
        backend: Backend name (simulator, ibm, braket, azure)

    Returns:
        CircuitResult containing measurements and metadata

    Raises:
        ValueError: If backend is not supported
        RuntimeError: If execution fails

    Example:
        >>> qc = QuantumCircuit(2)
        >>> qc.h(0)
        >>> qc.cx(0, 1)
        >>> result = run_circuit(qc)
        >>> print(result)
    """
    pass
```

### Naming Conventions

- Classes: `PascalCase` (e.g., `QuantumCircuit`)
- Functions/methods: `snake_case` (e.g., `run_circuit`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_QUBITS`)
- Private: prefix with `_` (e.g., `_internal_method`)
- Protected: prefix with `_` (e.g., `_protected_field`)

### Import Organization

```python
from __future__ import annotations

# Standard library
import os
from pathlib import Path
from typing import Any

# Third-party
import numpy as np
from fastapi import FastAPI

# Local
from cvgen.core.circuit import QuantumCircuit
from cvgen.backends.simulator import StateVectorSimulator
```

## Testing

### Running Tests

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_circuit.py -v
```

Run with coverage:
```bash
pytest tests/ --cov=cvgen --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Test Requirements

- Minimum 80% code coverage for new code
- All public APIs must have tests
- Integration tests for multi-backend features
- Tests should be isolated and deterministic

### Writing Tests

Use pytest fixtures for reusable test components:

```python
import pytest
from cvgen.core.circuit import QuantumCircuit
from cvgen.backends.simulator import StateVectorSimulator

@pytest.fixture
def simulator():
    """Create a fresh simulator instance."""
    return StateVectorSimulator(max_qubits=10)

def test_bell_state(simulator):
    """Test Bell state creation and measurement."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    result = simulator.run(qc, shots=1000)

    assert "00" in result.counts or "11" in result.counts
    assert len(result.counts) <= 2
```

### Test Organization

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_circuit.py          # Core circuit tests
├── test_simulator.py        # Simulator tests
├── test_api.py              # API tests
├── test_config.py           # Configuration tests
├── test_cli.py              # CLI tests
└── mocks/                   # Mock services
    ├── __init__.py
    └── origin_pilot_mock.py
```

## Git Workflow

### Branching Strategy

- `main`: Stable, production-ready code
- `develop`: Integration branch for features
- `feature/...`: New features
- `fix/...`: Bug fixes
- `docs/...`: Documentation only

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring without feature changes
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Dependency updates, tooling changes

Examples:
```bash
git commit -m "feat(cli): add health check command"
git commit -m "fix(simulator): correct state vector normalization"
git commit -m "docs(readme): update installation instructions"
git commit -m "test(circuit): add Bell state tests"
```

### Pull Request Process

1. Create a feature branch:
```bash
git checkout -b feature/my-feature
```

2. Make changes and commit:
```bash
git add .
git commit -m "feat: description of changes"
```

3. Push to your fork:
```bash
git push origin feature/my-feature
```

4. Create a Pull Request on GitHub with:
   - Clear title following Conventional Commits
   - Description of changes
   - Reference to related issues (Fixes #123)
   - Screenshots for UI changes

5. Ensure CI passes:
   - All tests pass
   - Code coverage maintained
   - Linting passes
   - Docker builds successfully

6. Request review from maintainers

7. Address feedback and push updates

8. Merge when approved

## Architecture Overview

### Project Structure

```
cvgen/
├── core/                 # Core quantum circuit logic
│   ├── circuit.py       # QuantumCircuit class
│   ├── gates.py         # Gate definitions
│   └── types.py         # Type definitions
├── backends/            # Backend implementations
│   ├── simulator.py     # State vector simulator
│   ├── ibm.py           # IBM Quantum backend
│   ├── braket.py        # AWS Braket backend
│   ├── azure.py         # Azure Quantum backend
│   └── origin.py        # Origin Pilot backend
├── bridge/              # Cross-service communication
│   ├── zmq_connection.py # ZeroMQ integration
│   ├── job_protocol.py   # Job management
│   └── telemetry.py      # Metrics collection
├── agents/              # LLM-powered agents
│   ├── generator.py      # Circuit generation
│   ├── rag.py           # Vector DB integration
│   └── ollama.py        # Ollama integration
├── web/                 # Web API
│   ├── app.py           # FastAPI application
│   ├── routes/          # API routes
│   └── models.py        # Pydantic models
├── config.py            # Configuration management
├── cli.py               # Command-line interface
└── __init__.py          # Package exports
```

### Key Design Patterns

1. **Factory Pattern**: Backend selection
2. **Strategy Pattern**: Different execution strategies
3. **Observer Pattern**: Event telemetry
4. **Singleton Pattern**: Configuration instances
5. **Dependency Injection**: Service initialization

### Module Responsibilities

- `core`: Pure quantum computing logic
- `backends`: Hardware/simulator abstractions
- `bridge`: Inter-service communication
- `agents`: AI/ML logic
- `web`: HTTP API layer
- `config`: Configuration handling
- `cli`: User-facing commands

## Performance Guidelines

### Optimization Tips

1. **Circuit Compilation**: Minimize gate count
2. **State Vector**: Limit to <20 qubits for simulation
3. **Transpilation**: Cache transpiled circuits
4. **Batching**: Group jobs for cloud backends
5. **Caching**: Use Redis for frequent operations

### Profiling

Profile performance with:
```bash
python -m cProfile -o stats.prof script.py
python -m pstats stats.prof
```

## Documentation

### Code Documentation

- Docstrings for all public functions/classes
- Comments for complex algorithms
- Type hints for all parameters and returns
- Examples in docstrings

### User Documentation

- Update README.md for major changes
- Add/update docs/ for new features
- Update CHANGELOG.md
- Add CLI help text

## Security Guidelines

### Secrets Management

- Never commit secrets to git
- Use environment variables for sensitive data
- Use `.cvgen.yaml` with proper permissions (600)
- Store tokens in secure vaults in production

### Dependency Security

- Keep dependencies up to date
- Review CVE advisories
- Use pinned versions for security fixes
- Run `pip audit` regularly

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create commit: `chore: bump version to X.Y.Z`
4. Create annotated tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. Push tag: `git push origin vX.Y.Z`
6. GitHub Actions automatically builds and publishes

## Getting Help

- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and discuss ideas
- Documentation: See docs/ and README.md
- Examples: Check examples/ directory

## Recognition

Contributors will be recognized in:
- CHANGELOG.md (for feature contributions)
- GitHub contributors page
- Project README.md (for significant contributions)

Thank you for contributing to CVGen!
