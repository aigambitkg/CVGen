"""Structured logging for quantum operations."""

from __future__ import annotations

import logging
import sys
from typing import Any


def setup_quantum_logger(
    name: str = "cvgen",
    level: int = logging.INFO,
    fmt: str = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
) -> logging.Logger:
    """Set up a structured logger for quantum operations.

    Args:
        name: Logger name.
        level: Logging level.
        fmt: Log format string.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


class QuantumLogger:
    """High-level logging wrapper for quantum-specific events."""

    def __init__(self, name: str = "cvgen") -> None:
        self._logger = setup_quantum_logger(name)

    def circuit_submitted(
        self, circuit_name: str, num_qubits: int, backend: str
    ) -> None:
        self._logger.info(
            f"Circuit '{circuit_name}' ({num_qubits}q) submitted to {backend}"
        )

    def circuit_completed(
        self, circuit_name: str, shots: int, unique_outcomes: int, duration_s: float
    ) -> None:
        self._logger.info(
            f"Circuit '{circuit_name}' completed: {shots} shots, "
            f"{unique_outcomes} unique outcomes, {duration_s:.4f}s"
        )

    def agent_started(self, agent_name: str, task_type: str) -> None:
        self._logger.info(f"Agent '{agent_name}' started task: {task_type}")

    def agent_step(self, agent_name: str, step: int, action: str) -> None:
        self._logger.debug(f"Agent '{agent_name}' step {step}: {action}")

    def agent_completed(
        self, agent_name: str, steps: int, success: bool
    ) -> None:
        status = "succeeded" if success else "failed"
        self._logger.info(
            f"Agent '{agent_name}' {status} after {steps} steps"
        )

    def optimization_progress(
        self, iteration: int, cost: float, **kwargs: Any
    ) -> None:
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self._logger.info(
            f"Optimization iter {iteration}: cost={cost:.6f} {extra}"
        )

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)
