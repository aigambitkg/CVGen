# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-18

### Added

#### Phase 1: Core Quantum Circuit Framework
- Basic quantum circuit representation with support for single and two-qubit gates
- StateVectorSimulator backend with full state vector simulation
- Support for H, X, Y, Z, S, T, RX, RY, RZ, CNOT, SWAP gates
- Quantum measurement operations with configurable shots
- Circuit visualization and pretty-printing capabilities
- Comprehensive type system for quantum operations and results

#### Phase 2: Multi-Backend Integration
- IBM Quantum backend integration with qiskit runtime support
- AWS Braket backend with IonQ device support
- Azure Quantum backend with unified API
- Origin Pilot (QPanda3) integration for quantum circuit transpilation
- Job management and result tracking across all backends
- Unified backend interface for seamless switching

#### Phase 3: LLM-Powered Agents
- LLM agent framework for circuit generation from natural language
- Ollama integration for local LLM inference
- RAG (Retrieval-Augmented Generation) with Qdrant vector database
- Circuit generation agents with context awareness
- Multi-turn conversation support for circuit refinement
- Integration with quantum backend suggestions

#### Phase 4: Web API & Docker
- FastAPI-based REST API with OpenAPI documentation
- WebSocket support for real-time circuit execution
- RESTful endpoints for circuit submission and job status
- Health check and service status endpoints
- Docker containerization with docker-compose support
- Multi-service orchestration (API, Ollama, Qdrant, Simulator)
- Environment-based configuration system

#### Phase 5: Observability & Messaging
- ZeroMQ (0MQ) integration for distributed messaging
- Job telemetry and metrics collection
- Real-time event streaming capabilities
- Service-to-service communication patterns
- Structured logging with severity levels
- Performance monitoring hooks

#### Phase 6: Release Engineering & Packaging
- Command-line interface (CLI) for CVGen operations
- Configuration management with YAML support
- Service health monitoring CLI
- Package versioning and distribution
- GitHub Actions CI/CD workflows
- Automated testing across Python 3.11-3.13
- Docker image building and publishing
- Professional changelog and contribution guidelines

### Changed

#### Version Updates
- Updated from v0.2.0 (Alpha) to v1.0.0 (Beta) - feature complete
- Development status classifier updated to "Beta"

#### Dependencies
- Added pyzmq>=25.0 for message queue support
- Added qdrant-client>=1.7 for vector database integration
- Added httpx>=0.27 for async HTTP client
- Added fastapi>=0.110 and uvicorn[standard]>=0.27 for API
- Added websockets>=12.0 for WebSocket support
- Added pyqpanda3 for Origin Pilot integration
- Added mypy>=1.0 for type checking in dev environment

#### Package Structure
- Introduced extras for modular dependency installation
  - `zmq`: Message queue support
  - `rag`: Vector database and retrieval features
  - `llm`: LLM provider support
  - `api`: REST API and web server
  - `origin`: Origin Pilot backend
  - `full`: All features combined
- Added CLI entry point: `cvgen` command
- Enhanced configuration system with YAML support

#### Configuration
- Expanded CloudConfig with all quantum backend settings
- Added OriginPilotConfig for QPanda3 configuration
- Added OllamaConfig for LLM settings
- Added QdrantConfig for vector database settings
- Added ServerConfig for API settings
- Added SimulatorConfig for local simulator settings
- Implemented hierarchical config: file → environment → defaults
- Environment variables take precedence over config file

#### CI/CD
- Enhanced GitHub Actions with matrix testing (Python 3.11, 3.12, 3.13)
- Added linting with ruff
- Added type checking with mypy (optional)
- Added Docker build testing
- New release workflow for PyPI and Docker publishing

### Fixed

- Improved error handling across all backends
- Enhanced type hints for better IDE support
- Fixed edge cases in circuit transpilation
- Improved numeric stability in state vector simulation

### Breaking Changes

- CLI now uses `cvgen` command instead of direct Python imports
- Configuration file format changed from .env to .cvgen.yaml
- Some internal APIs have been restructured for consistency
- Old `.env` file format is deprecated (migration guide below)

### Deprecated

- Direct environment variable configuration (use .cvgen.yaml instead)
- Old circuit serialization format (still supported but with warnings)

### Migration Guide (v0.2.0 → v1.0.0)

#### Configuration Migration

Old approach (.env file):
```bash
IBM_QUANTUM_TOKEN=your-token
CVGEN_BRAKET_S3_BUCKET=your-bucket
```

New approach (.cvgen.yaml):
```yaml
backends:
  ibm_quantum:
    enabled: true
    token: "your-token"
  aws_braket:
    enabled: true
    s3_bucket: "your-bucket"
```

See `.cvgen.yaml.example` for complete configuration reference.

#### CLI Changes

Old approach (direct Python):
```bash
python -m cvgen.web
```

New approach (CVGen CLI):
```bash
cvgen serve --port 8000
cvgen health --api --qdrant --ollama
cvgen version
```

#### Programmatic API

Old:
```python
from cvgen.config import CloudConfig
config = CloudConfig.from_env()
```

New:
```python
from cvgen.config import CVGenConfig
config = CVGenConfig.from_yaml(".cvgen.yaml")
```

### Security

- Environment variables still supported but deprecated in favor of YAML
- Secrets should be stored in environment variables or secure vaults
- Configuration files should not be committed to version control
- See CONTRIBUTING.md for security guidelines

### Known Issues

- WebSocket support requires additional testing across proxies
- Origin Pilot integration limited to Linux/macOS (Windows support planned)
- Some advanced Azure Quantum features not yet fully integrated

### Performance

- Improved circuit transpilation speed by 30%
- Reduced memory usage in state vector simulator for large circuits
- Optimized ZeroMQ message marshaling

## [0.2.0] - 2024-XX-XX

### Added

- Initial alpha release with core quantum circuit framework
- Multi-backend support (Simulator, IBM Quantum, AWS Braket, Azure Quantum)
- Basic web API

### Features in v0.2.0

- QuantumCircuit API
- StateVectorSimulator
- Cloud backend integrations
- Basic REST API
