"""Fallback chain for executing circuits on alternative backends."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult, JobConfig

try:
    from cvgen.bridge.telemetry import SystemStatus, TelemetrySubscriber

    HAS_BRIDGE = True
except ImportError:
    HAS_BRIDGE = False
    SystemStatus = None  # type: ignore
    TelemetrySubscriber = None  # type: ignore

logger = logging.getLogger(__name__)


class AllBackendsFailedError(Exception):
    """Raised when all backends in the fallback chain fail."""

    pass


@dataclass
class FallbackResult:
    """Result of fallback chain execution."""

    result: CircuitResult
    backend_used: str
    fallbacks_tried: list[str] = field(default_factory=list)
    reason: str = ""

    def __repr__(self) -> str:
        return (
            f"FallbackResult(backend={self.backend_used}, "
            f"tried={len(self.fallbacks_tried)}, reason='{self.reason}')"
        )


class FallbackChain:
    """Manages fallback execution across multiple backends.

    Tries backends in order, skipping unavailable ones, and falls back to
    the next if execution fails. Integrates with telemetry for intelligent
    backend selection.
    """

    def __init__(
        self,
        backends: list[tuple[str, QuantumBackend]],
        telemetry: Optional[TelemetrySubscriber] = None,
    ) -> None:
        """Initialize the fallback chain.

        Args:
            backends: List of (name, backend) tuples in priority order.
            telemetry: Optional TelemetrySubscriber for health checks.
        """
        self.backends = backends
        self.telemetry = telemetry

    def execute(
        self,
        circuit: QuantumCircuit,
        config: JobConfig | None = None,
    ) -> FallbackResult:
        """Execute circuit with fallback to alternative backends.

        Tries backends in order, skipping those that are CALIBRATING or OFFLINE,
        and falls back to the next if execution fails.

        Args:
            circuit: The quantum circuit to execute.
            config: Execution configuration.

        Returns:
            FallbackResult with the execution result and which backend was used.

        Raises:
            AllBackendsFailedError: If all backends fail or are unavailable.
        """
        config = config or JobConfig()
        fallbacks_tried: list[str] = []
        last_error: Optional[str] = None

        for backend_name, backend in self.backends:
            # Check backend health status
            if not self._is_backend_available(backend_name):
                status = self._get_backend_status(backend_name)
                logger.debug(
                    f"Skipping backend {backend_name}: status={status}"
                )
                fallbacks_tried.append(backend_name)
                continue

            # Try to execute on this backend
            try:
                logger.info(f"Attempting execution on backend: {backend_name}")
                result = backend.execute(circuit, config)

                reason = ""
                if fallbacks_tried:
                    reason = f"primary backends failed, used {backend_name}"
                else:
                    reason = f"used {backend_name}"

                logger.info(f"Successfully executed on {backend_name}")
                return FallbackResult(
                    result=result,
                    backend_used=backend_name,
                    fallbacks_tried=fallbacks_tried,
                    reason=reason,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Backend {backend_name} failed: {last_error}"
                )
                fallbacks_tried.append(backend_name)
                continue

        # All backends failed or unavailable
        error_summary = (
            f"All {len(self.backends)} backends failed or unavailable. "
            f"Tried: {', '.join(fallbacks_tried)}"
        )
        if last_error:
            error_summary += f". Last error: {last_error}"

        logger.error(error_summary)
        raise AllBackendsFailedError(error_summary)

    def _is_backend_available(self, backend_name: str) -> bool:
        """Check if a backend is available for execution.

        Args:
            backend_name: Name of the backend.

        Returns:
            True if backend is available, False if CALIBRATING or OFFLINE.
        """
        if not self.telemetry or not HAS_BRIDGE:
            return True

        try:
            status = self.telemetry.get_status(backend_name)
            if status == SystemStatus.OFFLINE:
                return False
            if status == SystemStatus.CALIBRATING:
                return False
            return True
        except Exception as e:
            logger.debug(f"Could not check backend status for {backend_name}: {e}")
            return True

    def _get_backend_status(self, backend_name: str) -> str:
        """Get the status string of a backend.

        Args:
            backend_name: Name of the backend.

        Returns:
            Status string.
        """
        if not self.telemetry or not HAS_BRIDGE:
            return "unknown"

        try:
            status = self.telemetry.get_status(backend_name)
            return status.value if status else "unknown"
        except Exception:
            return "unknown"

    def add_backend(self, name: str, backend: QuantumBackend) -> None:
        """Add a backend to the fallback chain.

        Args:
            name: Backend name.
            backend: Backend instance.
        """
        self.backends.append((name, backend))
        logger.debug(f"Added backend {name} to fallback chain")

    def remove_backend(self, name: str) -> None:
        """Remove a backend from the fallback chain.

        Args:
            name: Name of the backend to remove.
        """
        self.backends = [(n, b) for n, b in self.backends if n != name]
        logger.debug(f"Removed backend {name} from fallback chain")

    def __len__(self) -> int:
        """Get the number of backends in the chain."""
        return len(self.backends)

    def __repr__(self) -> str:
        names = [name for name, _ in self.backends]
        return f"FallbackChain(backends={names})"
