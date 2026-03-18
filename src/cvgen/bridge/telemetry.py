"""Telemetry and system status monitoring for quantum backends."""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    """System status enumeration."""

    AVAILABLE = "available"
    CALIBRATING = "calibrating"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class BackendHealth:
    """Health metrics for a backend."""

    name: str
    status: SystemStatus = SystemStatus.UNKNOWN
    queue_depth: int = 0
    error_rate: float = 0.0
    avg_execution_time_ms: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)
    last_error: Optional[str] = None


class TelemetrySubscriber(ABC):
    """Abstract base class for telemetry subscribers that monitor backend health."""

    @abstractmethod
    def get_status(self, backend_name: str) -> SystemStatus:
        """Get the current status of a backend.

        Args:
            backend_name: Name of the backend to check.

        Returns:
            SystemStatus enum value.
        """

    @abstractmethod
    def get_health(self, backend_name: str) -> BackendHealth:
        """Get detailed health metrics for a backend.

        Args:
            backend_name: Name of the backend.

        Returns:
            BackendHealth object with current metrics.
        """

    @abstractmethod
    def register_callback(
        self,
        backend_name: str,
        callback: Callable[[BackendHealth], None],
    ) -> None:
        """Register a callback to be notified of status changes.

        Args:
            backend_name: Name of the backend to monitor.
            callback: Function called with BackendHealth when status changes.
        """

    @abstractmethod
    def unregister_callback(self, backend_name: str) -> None:
        """Unregister a previously registered callback.

        Args:
            backend_name: Name of the backend.
        """


class LocalTelemetrySubscriber(TelemetrySubscriber):
    """Simple local telemetry subscriber for testing and fallback.

    This subscriber doesn't connect to external systems, just maintains
    local health state that can be updated manually or by backend adapters.
    """

    def __init__(self) -> None:
        """Initialize the local telemetry subscriber."""
        self._health: dict[str, BackendHealth] = {}
        self._callbacks: dict[str, list[Callable[[BackendHealth], None]]] = {}
        self._lock = threading.Lock()

    def get_status(self, backend_name: str) -> SystemStatus:
        """Get the current status of a backend."""
        with self._lock:
            health = self._health.get(backend_name)
            if health is None:
                health = BackendHealth(name=backend_name)
                self._health[backend_name] = health
            return health.status

    def get_health(self, backend_name: str) -> BackendHealth:
        """Get detailed health metrics for a backend."""
        with self._lock:
            if backend_name not in self._health:
                self._health[backend_name] = BackendHealth(name=backend_name)
            return self._health[backend_name]

    def register_callback(
        self,
        backend_name: str,
        callback: Callable[[BackendHealth], None],
    ) -> None:
        """Register a callback to be notified of status changes."""
        with self._lock:
            if backend_name not in self._callbacks:
                self._callbacks[backend_name] = []
            self._callbacks[backend_name].append(callback)

    def unregister_callback(self, backend_name: str) -> None:
        """Unregister a previously registered callback."""
        with self._lock:
            self._callbacks.pop(backend_name, None)

    def update_health(self, health: BackendHealth) -> None:
        """Update health metrics for a backend.

        Args:
            health: BackendHealth object with new metrics.
        """
        with self._lock:
            self._health[health.name] = health
            callbacks = self._callbacks.get(health.name, [])

        # Call callbacks outside the lock to prevent deadlocks
        for callback in callbacks:
            try:
                callback(health)
            except Exception as e:
                logger.warning(f"Error in telemetry callback for {health.name}: {e}")

    def update_status(
        self,
        backend_name: str,
        status: SystemStatus,
        queue_depth: int = 0,
        error_rate: float = 0.0,
        last_error: Optional[str] = None,
    ) -> None:
        """Update the status of a backend.

        Args:
            backend_name: Name of the backend.
            status: New SystemStatus.
            queue_depth: Current queue depth (optional).
            error_rate: Current error rate (optional).
            last_error: Description of last error (optional).
        """
        with self._lock:
            health = self._health.get(backend_name)
            if health is None:
                health = BackendHealth(name=backend_name)
            health.status = status
            health.queue_depth = queue_depth
            health.error_rate = error_rate
            health.last_heartbeat = time.time()
            if last_error:
                health.last_error = last_error
            self._health[backend_name] = health
            callbacks = self._callbacks.get(backend_name, [])

        # Call callbacks outside the lock
        for callback in callbacks:
            try:
                callback(health)
            except Exception as e:
                logger.warning(f"Error in telemetry callback for {backend_name}: {e}")

    def all_backends(self) -> dict[str, BackendHealth]:
        """Get health metrics for all monitored backends."""
        with self._lock:
            return dict(self._health)
