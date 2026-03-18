"""Protocol for job submission and result handling."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from cvgen.core.types import JobStatus


@dataclass
class JobResponse:
    """Response from a job status query or result retrieval.

    Attributes:
        job_id: Unique identifier for the job
        status: Current job status
        result: Result data if job is completed
        error: Error message if job failed
        timestamp: Time of the response
    """

    job_id: str
    status: JobStatus
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    @staticmethod
    def from_dict(data: dict[str, Any]) -> JobResponse:
        """Parse a JobResponse from a dictionary.

        Args:
            data: Dictionary with response fields

        Returns:
            Parsed JobResponse

        Raises:
            ValueError: If required fields are missing or invalid
        """
        job_id = data.get("job_id")
        if not job_id:
            raise ValueError("job_id is required")

        status_str = data.get("status", "QUEUED").upper()
        try:
            status = JobStatus[status_str]
        except KeyError:
            raise ValueError(f"Invalid status: {status_str}")

        timestamp_str = data.get("timestamp")
        timestamp = None
        if timestamp_str:
            try:
                timestamp = datetime.fromisoformat(timestamp_str)
            except (ValueError, TypeError):
                pass

        return JobResponse(
            job_id=job_id,
            status=status,
            result=data.get("result"),
            error=data.get("error"),
            timestamp=timestamp,
        )


class JobProtocol:
    """Protocol for formatting job messages and parsing responses."""

    @staticmethod
    def create_submit_message(
        circuit_code: str,
        shots: int,
        backend: str = "CPUQVM",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a job submission message.

        Args:
            circuit_code: Quantum circuit code (QPanda3 format)
            shots: Number of measurement shots
            backend: Backend name (default "CPUQVM")
            metadata: Additional metadata to attach

        Returns:
            Message dictionary for submission

        Raises:
            ValueError: If arguments are invalid
        """
        if not circuit_code or not isinstance(circuit_code, str):
            raise ValueError("circuit_code must be a non-empty string")
        if shots <= 0:
            raise ValueError("shots must be positive")
        if not isinstance(backend, str):
            raise ValueError("backend must be a string")

        job_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return {
            "type": "SUBMIT_JOB",
            "job_id": job_id,
            "circuit_code": circuit_code,
            "shots": shots,
            "backend": backend,
            "timestamp": timestamp,
            "metadata": metadata or {},
        }

    @staticmethod
    def create_status_request(job_id: str) -> dict[str, Any]:
        """Create a job status request message.

        Args:
            job_id: Job identifier

        Returns:
            Message dictionary

        Raises:
            ValueError: If job_id is invalid
        """
        if not job_id or not isinstance(job_id, str):
            raise ValueError("job_id must be a non-empty string")

        return {
            "type": "GET_JOB_STATUS",
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    @staticmethod
    def create_cancel_request(job_id: str) -> dict[str, Any]:
        """Create a job cancellation request message.

        Args:
            job_id: Job identifier

        Returns:
            Message dictionary

        Raises:
            ValueError: If job_id is invalid
        """
        if not job_id or not isinstance(job_id, str):
            raise ValueError("job_id must be a non-empty string")

        return {
            "type": "CANCEL_JOB",
            "job_id": job_id,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    @staticmethod
    def parse_response(msg: dict[str, Any]) -> JobResponse:
        """Parse a response message.

        Args:
            msg: Response message dictionary

        Returns:
            Parsed JobResponse

        Raises:
            ValueError: If message format is invalid
        """
        if not isinstance(msg, dict):
            raise ValueError("Message must be a dictionary")

        return JobResponse.from_dict(msg)

    @staticmethod
    def validate_submit_message(msg: dict[str, Any]) -> list[str]:
        """Validate a job submission message.

        Args:
            msg: Message to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not isinstance(msg, dict):
            return ["Message must be a dictionary"]

        if msg.get("type") != "SUBMIT_JOB":
            errors.append("type must be 'SUBMIT_JOB'")

        if not msg.get("job_id"):
            errors.append("job_id is required")

        if not msg.get("circuit_code"):
            errors.append("circuit_code is required")

        shots = msg.get("shots")
        if not isinstance(shots, int) or shots <= 0:
            errors.append("shots must be a positive integer")

        if not msg.get("backend"):
            errors.append("backend is required")

        if not msg.get("timestamp"):
            errors.append("timestamp is required")

        return errors

    @staticmethod
    def validate_status_request(msg: dict[str, Any]) -> list[str]:
        """Validate a status request message.

        Args:
            msg: Message to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not isinstance(msg, dict):
            return ["Message must be a dictionary"]

        if msg.get("type") != "GET_JOB_STATUS":
            errors.append("type must be 'GET_JOB_STATUS'")

        if not msg.get("job_id"):
            errors.append("job_id is required")

        return errors
