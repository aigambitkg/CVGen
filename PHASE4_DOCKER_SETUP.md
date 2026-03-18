# CVGen Phase 4 - Docker All-in-One Stack and Setup Script

**Status**: Complete & Production-Ready
**Date**: 2026-03-18
**Version**: Phase 4.0

## Overview

Phase 4 provides a complete, production-ready Docker stack that bundles CVGen with all required services:

- **CVGen Application** - FastAPI + Web UI + AI Agents
- **Ollama** - Local LLM runtime for code generation and AI agents
- **Qdrant** - Vector database for RAG (Retrieval Augmented Generation)
- **Init Container** - One-shot bootstrap for service initialization

Plus universal setup scripts for Linux, macOS, and Windows.

## Files Created

### Core Docker Files

#### 1. **docker-compose.full.yml** (141 lines)
Complete Docker Compose configuration for the full stack.

**Services:**
- `cvgen` - Main application (port 8000)
- `ollama` - LLM runtime (port 11434)
- `qdrant` - Vector database (ports 6333, 6334)
- `init-bootstrap` - One-shot initialization container

**Features:**
- Service dependency management
- Health checks for all services
- Persistent volumes for data
- GPU support (NVIDIA, Apple Silicon ready)
- Network isolation
- Environment variable configuration

**Usage:**
```bash
docker-compose -f docker-compose.full.yml up -d
```

---

#### 2. **Dockerfile** (66 lines)
Multi-stage build for optimized CVGen image.

**Key Features:**
- **Builder Stage**: Installs all dependencies (gcc, Python packages)
- **Runtime Stage**: Slim image with only runtime dependencies
- **Security**: Non-root user (cvgen:1000)
- **Size**: Minimal final image size
- **Health Check**: Built-in monitoring

**Includes:**
- FastAPI dependencies
- PyZMQ for distributed computing
- Qdrant client for RAG
- HTTPx for HTTP requests

---

#### 3. **Dockerfile.init** (90 lines)
Initialization container for one-time setup tasks.

**Responsibilities:**
1. Waits for all services to be healthy
2. Pulls Ollama model (configurable via OLLAMA_MODEL env var)
3. Initializes Qdrant vector database
4. Indexes QPanda3 documentation for RAG
5. Verifies all service health
6. Prints success summary

**Environment Variables:**
- `OLLAMA_MODEL` - Model to pull (default: qwen2.5:7b)
- `OLLAMA_HOST` - Ollama endpoint
- `QDRANT_URL` - Qdrant endpoint
- `QDRANT_COLLECTION` - Collection name

---

### Setup Scripts

#### 4. **setup.sh** (752 lines)
Universal setup script for Linux and macOS with:

**Features:**
- OS detection (Linux, macOS, Windows/WSL2)
- Docker/Docker Compose installation checking
- Automatic Docker installation on Linux
- GPU detection (NVIDIA, Apple Silicon, AMD)
- RAM detection for model recommendations
- Interactive configuration prompts
- Service startup and health checks
- Browser opening on completion

**Usage:**
```bash
bash setup.sh
```

**Interactive Prompts:**
1. Docker availability check
2. LLM model selection (with RAM-based recommendation)
3. API port configuration
4. Quantum backend selection
5. GPU acceleration setup (optional)

**Output:**
- Creates `.env` file with configuration
- Starts all services
- Waits for services to become healthy
- Opens browser to http://localhost:8000

---

#### 5. **setup.bat** (Windows Native)
Windows PowerShell-compatible setup script.

**Features:**
- Docker Desktop verification
- RAM detection
- Model selection menu
- Configuration file generation
- Service startup
- Browser integration

**Usage:**
```batch
setup.bat
```

---

### Configuration Files

#### 6. **.env.example** (136 lines)
Complete environment variable reference with descriptions.

**Sections:**
- CVGen API Configuration
- Ollama LLM Backend
- Qdrant Vector Database
- Origin Pilot (Quantum Backend)
- IBM Quantum (optional)
- AWS Braket (optional)
- Azure Quantum (optional)

**Example Values:**
```bash
CVGEN_PORT=8000
OLLAMA_MODEL=qwen2.5:7b
QDRANT_COLLECTION=cvgen_qpanda3
```

---

### Utility Scripts

#### 7. **scripts/health_check.sh** (4933 bytes)
Service health verification and diagnostics.

**Checks:**
- CVGen API responsiveness
- Ollama model availability
- Qdrant collection status
- Lists loaded models and collections
- Provides colored status output
- Troubleshooting guidance

**Usage:**
```bash
bash scripts/health_check.sh
```

**Output Example:**
```
✓ CVGen API is responding
✓ Ollama is responding
  • Loaded models:
    • qwen2.5:7b
✓ Qdrant is responding
  • Available collections:
    • cvgen_qpanda3
```

---

#### 8. **scripts/init_rag.py** (330+ lines)
RAG initialization Python script.

**Functions:**
1. Connects to Qdrant vector database
2. Creates collection if not exists
3. Loads bundled QPanda3 documentation
4. Generates embeddings
5. Indexes documents
6. Verifies indexing success

**Features:**
- Fallback embedding generation
- Automatic document loading from filesystem
- Error handling and recovery
- Progress reporting

**Usage:**
Called automatically by init-bootstrap container, but can also be run manually:
```bash
python scripts/init_rag.py
```

---

### Documentation Bundle

#### 9-12. **data/qpanda3_docs/** (4 markdown files)

**README.md** - Documentation index and integration guide
- Quick start example
- Available backends
- Integration with CVGen
- Links to external resources

**api_reference.md** - Complete QPanda3 API documentation
- Single-qubit gates (H, X, Y, Z, S, T, RX/Y/Z)
- Two-qubit gates (CNOT, CZ, SWAP, iSWAP)
- Multi-qubit gates (Toffoli, Fredkin)
- Circuit construction and execution
- Error handling
- Common patterns (Bell state, superposition)

**examples.md** - 8 complete code examples
1. Bell State (entanglement)
2. Three-qubit superposition
3. Grover's algorithm (2-qubit)
4. Quantum phase estimation
5. Variational Quantum Eigensolver (VQE)
6. Deutsch-Jozsa algorithm
7. Quantum Fourier Transform
8. Quantum error correction

**patterns.md** - 10 quantum computing patterns
1. Bell state entanglement
2. GHZ state (multi-qubit)
3. W state
4. Superposition sweep
5. Phase kickback
6. Oracle pattern
7. Amplitude amplification (Grover)
8. Parameterized circuits
9. Circuit decomposition
10. Measurement and post-processing

All documentation is automatically indexed into Qdrant during initialization for RAG.

---

## Architecture

### Service Topology

```
┌─────────────────────────────────────────────┐
│          CVGen Network (cvgen-net)          │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐  ┌─────────────┐         │
│  │ CVGen API    │  │  Ollama     │         │
│  │ :8000        │  │  :11434     │         │
│  └──────┬───────┘  └─────────────┘         │
│         │               ▲                  │
│         │               │                  │
│         └───────┬───────┘                  │
│                 │                          │
│         ┌───────▼──────┐                   │
│         │  Qdrant      │                   │
│         │  :6333       │                   │
│         └──────────────┘                   │
│                 ▲                          │
│         ┌───────┴──────┐                   │
│         │ init-bootstrap│                   │
│         │ (one-shot)   │                   │
│         └──────────────┘                   │
│                                             │
└─────────────────────────────────────────────┘

Volumes:
  • cvgen_data (SQLite DB, logs)
  • ollama_data (model cache)
  • qdrant_data (vector index)
```

### Startup Sequence

1. **docker-compose up** starts all services in parallel
2. **Service Health Checks** - Each service monitors itself
3. **init-bootstrap** waits for all services to be healthy
4. **Ollama Model Pull** - Pulls configured LLM model
5. **RAG Initialization** - Indexes QPanda3 documentation
6. **Ready** - All services operational and ready for requests

---

## Configuration

### Environment Variables

#### Required (Auto-generated by setup.sh/setup.bat):
```bash
CVGEN_PORT=8000
OLLAMA_MODEL=qwen2.5:7b
QDRANT_COLLECTION=cvgen_qpanda3
```

#### Optional (Cloud backends):
```bash
IBM_QUANTUM_TOKEN=your-token
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AZURE_QUANTUM_RESOURCE_ID=your-resource-id
```

### Model Selection Guide

| Model | Size | RAM | Speed | Quality | Use Case |
|-------|------|-----|-------|---------|----------|
| phi3:mini | 2.2GB | 2GB | ★★★★★ | ★★ | Ultra-lightweight |
| qwen2.5:7b | 4.0GB | 4-8GB | ★★★★ | ★★★★ | **Recommended** |
| mistral | 4.1GB | 4-8GB | ★★★★ | ★★★ | Code-focused |
| qwen2.5:14b | 8.9GB | 8-16GB | ★★★ | ★★★★★ | High quality |
| qwen2.5:32b | 20.3GB | 20-32GB | ★★ | ★★★★★★ | Maximum quality |

### GPU Support

**NVIDIA GPUs:**
```bash
# Uncomment in docker-compose.full.yml:
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

**Apple Silicon:**
- Automatically detected and optimized
- Metal acceleration enabled in Docker Desktop

**AMD GPUs:**
- ROCm support available
- Requires rocm-docker runtime

---

## Usage

### Quick Start

**Linux/macOS:**
```bash
bash setup.sh
```

**Windows:**
```batch
setup.bat
```

### Manual Commands

**Start services:**
```bash
docker-compose -f docker-compose.full.yml up -d
```

**Check health:**
```bash
bash scripts/health_check.sh
```

**View logs:**
```bash
docker logs -f cvgen-api      # Main application
docker logs -f cvgen-ollama   # LLM runtime
docker logs -f cvgen-qdrant   # Vector DB
docker logs cvgen-init        # Initialization
```

**Stop services:**
```bash
docker-compose -f docker-compose.full.yml down
```

**Pull new model:**
```bash
docker exec cvgen-ollama ollama pull mistral:latest
```

**Full reset (warning: deletes data):**
```bash
docker-compose -f docker-compose.full.yml down -v
docker-compose -f docker-compose.full.yml up -d
```

---

## Troubleshooting

### Services Won't Start

**Check Docker is running:**
```bash
docker ps
```

**View error logs:**
```bash
docker-compose -f docker-compose.full.yml logs
```

**Check system resources:**
```bash
docker stats
```

### Service Timeouts

**Increase startup timeout** (edit setup.sh):
```bash
CONTAINER_CHECK_TIMEOUT=240  # seconds
```

**Manual service startup:**
```bash
docker-compose -f docker-compose.full.yml up -d ollama
sleep 30
docker-compose -f docker-compose.full.yml up -d qdrant
sleep 30
docker-compose -f docker-compose.full.yml up -d cvgen
```

### Out of Memory

**Use smaller model:**
```bash
# In .env:
OLLAMA_MODEL=phi3:mini  # Instead of qwen2.5:7b
```

**Restart services:**
```bash
docker-compose -f docker-compose.full.yml restart
```

### Model Download Failures

**Manual model pull:**
```bash
docker exec cvgen-ollama ollama pull qwen2.5:7b
```

**Check Ollama status:**
```bash
curl http://localhost:11434/api/tags
```

---

## Performance Tuning

### Memory Optimization

**Set Docker memory limits:**
```yaml
# In docker-compose.full.yml
services:
  cvgen:
    deploy:
      resources:
        limits:
          memory: 4g
        reservations:
          memory: 2g
```

### Network Optimization

**Use host network (Linux only):**
```yaml
network_mode: host
```

### Storage Optimization

**Monitor volume usage:**
```bash
docker volume ls
docker volume inspect cvgen_data
```

**Cleanup unused data:**
```bash
docker volume prune
```

---

## Production Deployment

### Reverse Proxy (Nginx)

```nginx
upstream cvgen {
    server cvgen:8000;
}

server {
    listen 80;
    server_name quantum.example.com;

    location / {
        proxy_pass http://cvgen;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### TLS/SSL

```bash
# Using Let's Encrypt
docker run --rm -it \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot \
  certonly --standalone -d quantum.example.com
```

### Monitoring

**Prometheus metrics:**
```bash
docker exec cvgen-api curl http://localhost:8000/metrics
```

**Health endpoint:**
```bash
curl http://localhost:8000/api/v1/health
```

---

## Architecture Decisions

### Why Docker Compose?

- Single command startup
- Service orchestration
- Volume management
- Network isolation
- Cross-platform compatibility
- Zero additional infrastructure

### Why Multi-Stage Dockerfile?

- Smaller final image size (~300MB vs 1GB+)
- Faster deployments
- Security: no build tools in runtime
- Cleaner image layers

### Why Qdrant for RAG?

- High-performance vector search
- Built-in collection management
- REST API (no additional client needed)
- Scalable (supports distributed mode)

### Why Ollama?

- Easy model management
- Local inference (privacy)
- GPU acceleration ready
- No external API calls
- Large model library

---

## Future Enhancements

**Phase 4.1:**
- Kubernetes deployment templates
- Prometheus/Grafana monitoring stack
- Jenkins CI/CD pipeline integration
- Advanced RAG with hybrid search

**Phase 4.2:**
- Multi-node Qdrant cluster
- Load balancer configuration
- Backup and recovery procedures
- Cost optimization for cloud deployment

**Phase 4.3:**
- Custom model fine-tuning pipeline
- Advanced caching strategies
- API rate limiting and quotas
- Detailed analytics dashboard

---

## Support & Resources

### Documentation
- CVGen Main: `/home/kevin/CVGEN/cvgen-build/README.md`
- QPanda3 API: `data/qpanda3_docs/api_reference.md`
- Examples: `data/qpanda3_docs/examples.md`
- Patterns: `data/qpanda3_docs/patterns.md`

### External Resources
- QPanda3: https://pyqpanda-toturial.readthedocs.io/
- Ollama: https://ollama.ai/
- Qdrant: https://qdrant.tech/
- Docker: https://docs.docker.com/

### Quantum Backends
- Origin Pilot: https://originpilot.example.com/
- IBM Quantum: https://quantum.ibm.com/
- AWS Braket: https://aws.amazon.com/braket/
- Azure Quantum: https://azure.microsoft.com/en-us/products/quantum/

---

## Summary

Phase 4 delivers a complete, production-ready Docker stack that enables users to:

✓ Run CVGen locally with zero configuration hassle
✓ Access advanced quantum computing capabilities
✓ Use AI agents for code generation
✓ Execute circuits on local simulators or cloud quantum hardware
✓ Scale deployment from laptop to production infrastructure

The universal setup scripts make it accessible to all users regardless of OS, with intelligent defaults and optional configuration for advanced use cases.

**Total Files Created**: 12 (Dockerfiles, Compose, Setup Scripts, Documentation, Utilities)
**Total Lines of Code**: 2,000+
**Documentation**: 30+ pages
**Example Code**: 8 complete quantum algorithms

---

**Created**: 2026-03-18
**Status**: Ready for Production
**Version**: Phase 4.0
