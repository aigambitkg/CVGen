"""Centralized configuration for CVGen backends and services."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


@dataclass
class OriginPilotConfig:
    """Configuration for Origin Pilot quantum backend."""

    enabled: bool = False
    host: str = "localhost"
    job_port: int = 5555
    telemetry_port: int = 5556

    @classmethod
    def from_env(cls) -> OriginPilotConfig:
        """Create configuration from environment variables."""
        return cls(
            enabled=os.environ.get("CVGEN_ORIGIN_ENABLED", "false").lower() == "true",
            host=os.environ.get("CVGEN_ORIGIN_HOST", "localhost"),
            job_port=int(os.environ.get("CVGEN_ORIGIN_JOB_PORT", "5555")),
            telemetry_port=int(os.environ.get("CVGEN_ORIGIN_TELEMETRY_PORT", "5556")),
        )


@dataclass
class OllamaConfig:
    """Configuration for Ollama LLM backend."""

    provider: str = "ollama"
    url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    embedding_model: str = "nomic-embed-text"

    @classmethod
    def from_env(cls) -> OllamaConfig:
        """Create configuration from environment variables."""
        return cls(
            provider=os.environ.get("CVGEN_LLM_PROVIDER", "ollama"),
            url=os.environ.get("CVGEN_OLLAMA_URL", "http://localhost:11434"),
            model=os.environ.get("CVGEN_OLLAMA_MODEL", "qwen2.5:7b"),
            embedding_model=os.environ.get(
                "CVGEN_OLLAMA_EMBEDDING_MODEL",
                "nomic-embed-text",
            ),
        )


@dataclass
class QdrantConfig:
    """Configuration for Qdrant vector database."""

    enabled: bool = True
    url: str = "http://localhost:6333"
    collection: str = "cvgen_qpanda3"

    @classmethod
    def from_env(cls) -> QdrantConfig:
        """Create configuration from environment variables."""
        return cls(
            enabled=os.environ.get("CVGEN_QDRANT_ENABLED", "true").lower() == "true",
            url=os.environ.get("CVGEN_QDRANT_URL", "http://localhost:6333"),
            collection=os.environ.get("CVGEN_QDRANT_COLLECTION", "cvgen_qpanda3"),
        )


@dataclass
class SimulatorConfig:
    """Configuration for quantum simulator."""

    enabled: bool = True
    max_qubits: int = 20

    @classmethod
    def from_env(cls) -> SimulatorConfig:
        """Create configuration from environment variables."""
        return cls(
            enabled=os.environ.get("CVGEN_SIMULATOR_ENABLED", "true").lower() == "true",
            max_qubits=int(os.environ.get("CVGEN_SIMULATOR_MAX_QUBITS", "20")),
        )


@dataclass
class CloudConfig:
    """Configuration for cloud quantum backends."""

    # IBM Quantum
    ibm_token: str | None = None
    ibm_instance: str = "ibm-q/open/main"
    ibm_backend: str = "ibm_brisbane"

    # AWS Braket
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = ""
    aws_s3_prefix: str = "cvgen-results"
    aws_device_arn: str = "arn:aws:braket:::device/qpu/ionq/Harmony"

    # Azure Quantum
    azure_resource_id: str = ""
    azure_location: str = "eastus"
    azure_target: str = "ionq.simulator"

    @classmethod
    def from_env(cls) -> CloudConfig:
        """Create configuration from environment variables."""
        return cls(
            ibm_token=os.environ.get("IBM_QUANTUM_TOKEN"),
            ibm_instance=os.environ.get("IBM_QUANTUM_INSTANCE", "ibm-q/open/main"),
            ibm_backend=os.environ.get("IBM_QUANTUM_BACKEND", "ibm_brisbane"),
            aws_region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            aws_s3_bucket=os.environ.get("CVGEN_BRAKET_S3_BUCKET", ""),
            aws_s3_prefix=os.environ.get("CVGEN_BRAKET_S3_PREFIX", "cvgen-results"),
            aws_device_arn=os.environ.get(
                "CVGEN_BRAKET_DEVICE_ARN",
                "arn:aws:braket:::device/qpu/ionq/Harmony",
            ),
            azure_resource_id=os.environ.get("AZURE_QUANTUM_RESOURCE_ID", ""),
            azure_location=os.environ.get("AZURE_QUANTUM_LOCATION", "eastus"),
            azure_target=os.environ.get("AZURE_QUANTUM_TARGET", "ionq.simulator"),
        )


@dataclass
class ServerConfig:
    """Configuration for CVGen API server."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> ServerConfig:
        """Create configuration from environment variables."""
        return cls(
            host=os.environ.get("CVGEN_SERVER_HOST", "0.0.0.0"),
            port=int(os.environ.get("CVGEN_SERVER_PORT", "8000")),
            debug=os.environ.get("CVGEN_DEBUG", "false").lower() == "true",
            log_level=os.environ.get("CVGEN_LOG_LEVEL", "INFO"),
        )


@dataclass
class CVGenConfig:
    """Complete CVGen configuration."""

    version: str = "1.0.0"
    server: ServerConfig = field(default_factory=ServerConfig)
    simulator: SimulatorConfig = field(default_factory=SimulatorConfig)
    origin_pilot: OriginPilotConfig = field(default_factory=OriginPilotConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)

    @classmethod
    def from_env(cls) -> CVGenConfig:
        """Create configuration from environment variables."""
        return cls(
            version=os.environ.get("CVGEN_VERSION", "1.0.0"),
            server=ServerConfig.from_env(),
            simulator=SimulatorConfig.from_env(),
            origin_pilot=OriginPilotConfig.from_env(),
            ollama=OllamaConfig.from_env(),
            qdrant=QdrantConfig.from_env(),
            cloud=CloudConfig.from_env(),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> CVGenConfig:
        """Load configuration from YAML file."""
        if yaml is None:
            raise ImportError(
                "PyYAML is required to load configuration from YAML. "
                "Install with: pip install pyyaml"
            )

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Merge with environment variables (env takes precedence)
        env_config = cls.from_env()

        cvgen_data = data.get("cvgen", {})
        server_data = data.get("server", {})
        backends_data = data.get("backends", {})
        llm_data = data.get("llm", {})
        rag_data = data.get("rag", {})

        # Build ServerConfig
        server = ServerConfig(
            host=server_data.get("host", env_config.server.host),
            port=server_data.get("port", env_config.server.port),
            debug=server_data.get("debug", env_config.server.debug),
            log_level=cvgen_data.get("log_level", env_config.server.log_level),
        )

        # Build SimulatorConfig
        sim_data = backends_data.get("simulator", {})
        simulator = SimulatorConfig(
            enabled=sim_data.get("enabled", env_config.simulator.enabled),
            max_qubits=sim_data.get("max_qubits", env_config.simulator.max_qubits),
        )

        # Build OriginPilotConfig
        origin_data = backends_data.get("origin_pilot", {})
        origin_pilot = OriginPilotConfig(
            enabled=origin_data.get("enabled", env_config.origin_pilot.enabled),
            host=origin_data.get("host", env_config.origin_pilot.host),
            job_port=origin_data.get("job_port", env_config.origin_pilot.job_port),
            telemetry_port=origin_data.get(
                "telemetry_port",
                env_config.origin_pilot.telemetry_port,
            ),
        )

        # Build OllamaConfig
        ollama = OllamaConfig(
            provider=llm_data.get("provider", env_config.ollama.provider),
            url=llm_data.get("url", env_config.ollama.url),
            model=llm_data.get("model", env_config.ollama.model),
            embedding_model=llm_data.get(
                "embedding_model",
                env_config.ollama.embedding_model,
            ),
        )

        # Build QdrantConfig
        qdrant = QdrantConfig(
            enabled=rag_data.get("enabled", env_config.qdrant.enabled),
            url=rag_data.get("qdrant_url", env_config.qdrant.url),
            collection=rag_data.get("collection", env_config.qdrant.collection),
        )

        # Cloud backends (from YAML or env)
        ibm_data = backends_data.get("ibm_quantum", {})
        cloud = CloudConfig(
            ibm_token=ibm_data.get("token", env_config.cloud.ibm_token),
            ibm_instance=ibm_data.get("instance", env_config.cloud.ibm_instance),
            ibm_backend=ibm_data.get("backend", env_config.cloud.ibm_backend),
            aws_region=env_config.cloud.aws_region,
            aws_s3_bucket=env_config.cloud.aws_s3_bucket,
            aws_s3_prefix=env_config.cloud.aws_s3_prefix,
            aws_device_arn=env_config.cloud.aws_device_arn,
            azure_resource_id=env_config.cloud.azure_resource_id,
            azure_location=env_config.cloud.azure_location,
            azure_target=env_config.cloud.azure_target,
        )

        return cls(
            version=cvgen_data.get("version", env_config.version),
            server=server,
            simulator=simulator,
            origin_pilot=origin_pilot,
            ollama=ollama,
            qdrant=qdrant,
            cloud=cloud,
        )
