"""Tests for CVGen configuration management."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from cvgen.config import (
    CVGenConfig,
    CloudConfig,
    OllamaConfig,
    OriginPilotConfig,
    QdrantConfig,
    ServerConfig,
    SimulatorConfig,
)


class TestServerConfig:
    """Tests for ServerConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False
        assert config.log_level == "INFO"

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ServerConfig(
            host="127.0.0.1",
            port=9000,
            debug=True,
            log_level="DEBUG",
        )
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.debug is True
        assert config.log_level == "DEBUG"

    def test_from_env(self) -> None:
        """Test loading from environment variables."""
        env_vars = {
            "CVGEN_SERVER_HOST": "192.168.1.1",
            "CVGEN_SERVER_PORT": "8080",
            "CVGEN_DEBUG": "true",
            "CVGEN_LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars):
            config = ServerConfig.from_env()
            assert config.host == "192.168.1.1"
            assert config.port == 8080
            assert config.debug is True
            assert config.log_level == "DEBUG"

    def test_from_env_defaults(self) -> None:
        """Test default values when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ServerConfig.from_env()
            assert config.host == "0.0.0.0"
            assert config.port == 8000
            assert config.debug is False
            assert config.log_level == "INFO"


class TestSimulatorConfig:
    """Tests for SimulatorConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = SimulatorConfig()
        assert config.enabled is True
        assert config.max_qubits == 20

    def test_from_env(self) -> None:
        """Test loading from environment variables."""
        env_vars = {
            "CVGEN_SIMULATOR_ENABLED": "false",
            "CVGEN_SIMULATOR_MAX_QUBITS": "15",
        }

        with patch.dict(os.environ, env_vars):
            config = SimulatorConfig.from_env()
            assert config.enabled is False
            assert config.max_qubits == 15


class TestOriginPilotConfig:
    """Tests for OriginPilotConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = OriginPilotConfig()
        assert config.enabled is False
        assert config.host == "localhost"
        assert config.job_port == 5555
        assert config.telemetry_port == 5556

    def test_from_env(self) -> None:
        """Test loading from environment variables."""
        env_vars = {
            "CVGEN_ORIGIN_ENABLED": "true",
            "CVGEN_ORIGIN_HOST": "quantum.example.com",
            "CVGEN_ORIGIN_JOB_PORT": "6000",
            "CVGEN_ORIGIN_TELEMETRY_PORT": "6001",
        }

        with patch.dict(os.environ, env_vars):
            config = OriginPilotConfig.from_env()
            assert config.enabled is True
            assert config.host == "quantum.example.com"
            assert config.job_port == 6000
            assert config.telemetry_port == 6001


class TestOllamaConfig:
    """Tests for OllamaConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = OllamaConfig()
        assert config.provider == "ollama"
        assert config.url == "http://localhost:11434"
        assert config.model == "qwen2.5:7b"
        assert config.embedding_model == "nomic-embed-text"

    def test_from_env(self) -> None:
        """Test loading from environment variables."""
        env_vars = {
            "CVGEN_LLM_PROVIDER": "openai",
            "CVGEN_OLLAMA_URL": "http://ollama.local:11434",
            "CVGEN_OLLAMA_MODEL": "mistral:7b",
            "CVGEN_OLLAMA_EMBEDDING_MODEL": "bge-small",
        }

        with patch.dict(os.environ, env_vars):
            config = OllamaConfig.from_env()
            assert config.provider == "openai"
            assert config.url == "http://ollama.local:11434"
            assert config.model == "mistral:7b"
            assert config.embedding_model == "bge-small"


class TestQdrantConfig:
    """Tests for QdrantConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = QdrantConfig()
        assert config.enabled is True
        assert config.url == "http://localhost:6333"
        assert config.collection == "cvgen_qpanda3"

    def test_from_env(self) -> None:
        """Test loading from environment variables."""
        env_vars = {
            "CVGEN_QDRANT_ENABLED": "true",
            "CVGEN_QDRANT_URL": "http://qdrant.example.com:6333",
            "CVGEN_QDRANT_COLLECTION": "quantum_circuits",
        }

        with patch.dict(os.environ, env_vars):
            config = QdrantConfig.from_env()
            assert config.enabled is True
            assert config.url == "http://qdrant.example.com:6333"
            assert config.collection == "quantum_circuits"


class TestCloudConfig:
    """Tests for CloudConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CloudConfig()
        assert config.ibm_token is None
        assert config.ibm_instance == "ibm-q/open/main"
        assert config.ibm_backend == "ibm_brisbane"
        assert config.aws_region == "us-east-1"
        assert config.azure_target == "ionq.simulator"

    def test_from_env(self) -> None:
        """Test loading from environment variables."""
        env_vars = {
            "IBM_QUANTUM_TOKEN": "test-token-123",
            "IBM_QUANTUM_BACKEND": "ibm_osaka",
            "AWS_DEFAULT_REGION": "us-west-2",
            "CVGEN_BRAKET_S3_BUCKET": "my-bucket",
            "AZURE_QUANTUM_RESOURCE_ID": "my-resource-id",
        }

        with patch.dict(os.environ, env_vars):
            config = CloudConfig.from_env()
            assert config.ibm_token == "test-token-123"
            assert config.ibm_backend == "ibm_osaka"
            assert config.aws_region == "us-west-2"
            assert config.aws_s3_bucket == "my-bucket"
            assert config.azure_resource_id == "my-resource-id"


class TestCVGenConfig:
    """Tests for CVGenConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = CVGenConfig()
        assert config.version == "1.0.0"
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.simulator, SimulatorConfig)
        assert isinstance(config.origin_pilot, OriginPilotConfig)
        assert isinstance(config.ollama, OllamaConfig)
        assert isinstance(config.qdrant, QdrantConfig)
        assert isinstance(config.cloud, CloudConfig)

    def test_from_env(self) -> None:
        """Test loading from environment variables."""
        env_vars = {
            "CVGEN_VERSION": "1.0.0",
            "CVGEN_SERVER_HOST": "0.0.0.0",
            "CVGEN_SERVER_PORT": "8000",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = CVGenConfig.from_env()
            assert config.version == "1.0.0"
            assert config.server.host == "0.0.0.0"
            assert config.server.port == 8000

    def test_from_yaml_missing_file(self) -> None:
        """Test loading from non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            CVGenConfig.from_yaml("/nonexistent/path/.cvgen.yaml")

    def test_from_yaml_with_file(self, tmp_path: Path) -> None:
        """Test loading from YAML file."""
        yaml_content = """
cvgen:
  version: "1.0.0"
  log_level: DEBUG

server:
  host: "127.0.0.1"
  port: 9000
  debug: true

backends:
  simulator:
    enabled: true
    max_qubits: 15
  origin_pilot:
    enabled: true
    host: "quantum.local"
    job_port: 6000

llm:
  provider: "ollama"
  url: "http://localhost:11434"
  model: "mistral:7b"

rag:
  enabled: true
  qdrant_url: "http://localhost:6333"
  collection: "my_collection"
"""
        config_file = tmp_path / ".cvgen.yaml"
        config_file.write_text(yaml_content)

        # Test with environment variables cleared
        with patch.dict(os.environ, {}, clear=True):
            config = CVGenConfig.from_yaml(config_file)

        assert config.version == "1.0.0"
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
        assert config.server.log_level == "DEBUG"
        assert config.server.debug is True
        assert config.simulator.enabled is True
        assert config.simulator.max_qubits == 15
        assert config.origin_pilot.enabled is True
        assert config.origin_pilot.host == "quantum.local"
        assert config.origin_pilot.job_port == 6000
        assert config.ollama.model == "mistral:7b"
        assert config.qdrant.collection == "my_collection"

    def test_from_yaml_env_precedence(self, tmp_path: Path) -> None:
        """Test that YAML values take precedence over environment variables."""
        yaml_content = """
server:
  host: "127.0.0.1"
  port: 9000
"""
        config_file = tmp_path / ".cvgen.yaml"
        config_file.write_text(yaml_content)

        env_vars = {"CVGEN_SERVER_PORT": "8080"}

        with patch.dict(os.environ, env_vars, clear=True):
            config = CVGenConfig.from_yaml(config_file)

        # YAML value takes precedence over env var when both are present
        assert config.server.port == 9000

    def test_from_yaml_empty_file(self, tmp_path: Path) -> None:
        """Test loading from empty YAML file."""
        config_file = tmp_path / ".cvgen.yaml"
        config_file.write_text("")

        with patch.dict(os.environ, {}, clear=True):
            config = CVGenConfig.from_yaml(config_file)

        # Should use all defaults
        assert config.version == "1.0.0"
        assert config.server.host == "0.0.0.0"
        assert config.simulator.enabled is True

    def test_merge_behavior(self, tmp_path: Path) -> None:
        """Test merge behavior of YAML and environment variables."""
        yaml_content = """
backends:
  simulator:
    enabled: true
    max_qubits: 15
  origin_pilot:
    enabled: true
    host: "quantum.local"

llm:
  url: "http://ollama.local:11434"
  model: "yaml-model"
"""
        config_file = tmp_path / ".cvgen.yaml"
        config_file.write_text(yaml_content)

        env_vars = {
            "CVGEN_SIMULATOR_MAX_QUBITS": "25",
            "CVGEN_OLLAMA_MODEL": "custom-model",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = CVGenConfig.from_yaml(config_file)

        # YAML values take precedence when specified
        assert config.simulator.max_qubits == 15
        # YAML model value takes precedence over env var
        assert config.ollama.model == "yaml-model"
        # Non-overridden YAML values should remain
        assert config.origin_pilot.host == "quantum.local"
