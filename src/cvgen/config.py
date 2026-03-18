"""Centralized configuration for CVGen backends and services."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


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
