"""Retry policy with exponential backoff for resilient execution."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

try:
    from cvgen.bridge.telemetry import SystemStatus, TelemetrySubscriber

    HAS_BRIDGE = True
except ImportError:
    HAS_BRIDGE = False
    SystemStatus = None  # type: ignore
    TelemetrySubscriber = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class RetryResult:
    """Result of a retry-wrapped execution."""

    success: bool
    result: Any = None
    attempts: int = 0
    total_wait_s: float = 0.0
    errors: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"RetryResult(success={self.success}, attempts={self.attempts}, "
            f"wait_s={self.total_wait_s:.2f}, errors={len(self.errors)})"
        )


class RetryPolicy:
    """Implements exponential backoff retry policy for resilient execution.

    Features:
    - Exponential backoff with jitter
    - Configurable retry limits and delays
    - Integration with backend health telemetry
    - Respects CALIBRATING status without counting retries
    - Comprehensive error tracking and logging
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        retry_on_calibrating: bool = True,
        telemetry: Optional[TelemetrySubscriber] = None,
    ) -> None:
        """Initialize the retry policy.

        Args:
            max_retries: Maximum number of retries after initial attempt (default: 3).
            base_delay: Initial delay in seconds for exponential backoff (default: 1.0).
            max_delay: Maximum delay between retries in seconds (default: 60.0).
            jitter: If True, add random jitter to delays (default: True).
            retry_on_calibrating: If True, wait without counting retries when
                backend is CALIBRATING (default: True).
            telemetry: Optional TelemetrySubscriber for checking backend status.
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.retry_on_calibrating = retry_on_calibrating
        self.telemetry = telemetry

    def execute(
        self,
        fn: Callable[..., Any],
        *args: Any,
        backend_name: Optional[str] = None,
        **kwargs: Any,
    ) -> RetryResult:
        """Execute a function with retry logic and exponential backoff.

        Args:
            fn: Callable to execute.
            *args: Positional arguments to pass to fn.
            backend_name: Name of the backend (optional, for telemetry checks).
            **kwargs: Keyword arguments to pass to fn.

        Returns:
            RetryResult with execution outcome and metrics.
        """
        errors: list[str] = []
        total_wait = 0.0
        attempt = 0

        while attempt <= self.max_retries:
            try:
                logger.debug(f"Executing attempt {attempt + 1} of {self.max_retries + 1}")
                result = fn(*args, **kwargs)
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                    total_wait_s=total_wait,
                    errors=errors,
                )
            except Exception as e:
                error_msg = str(e)
                errors.append(error_msg)
                logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

                # Check if we should give up
                if attempt >= self.max_retries:
                    logger.error(
                        f"All {self.max_retries + 1} attempts exhausted. Last error: {error_msg}"
                    )
                    return RetryResult(
                        success=False,
                        result=None,
                        attempts=attempt + 1,
                        total_wait_s=total_wait,
                        errors=errors,
                    )

                # Wait before retrying
                wait_time = self._calculate_wait(attempt)

                # Check if backend is calibrating
                if self.retry_on_calibrating and backend_name and HAS_BRIDGE and self.telemetry:
                    status = self._check_backend_status(backend_name)
                    if status == SystemStatus.CALIBRATING:
                        wait_time = self._wait_for_calibration_complete(
                            backend_name, max_wait=300.0
                        )
                        logger.info(
                            f"Backend {backend_name} is calibrating. "
                            f"Waited {wait_time:.1f}s without counting as retry."
                        )
                        total_wait += wait_time
                        continue

                logger.info(f"Waiting {wait_time:.2f}s before retry {attempt + 2}...")
                time.sleep(wait_time)
                total_wait += wait_time
                attempt += 1

        # Should not reach here
        return RetryResult(
            success=False,
            result=None,
            attempts=attempt + 1,
            total_wait_s=total_wait,
            errors=errors,
        )

    def _calculate_wait(self, attempt: int) -> float:
        """Calculate wait time for exponential backoff.

        Args:
            attempt: The attempt number (0-indexed).

        Returns:
            Wait time in seconds.
        """
        # Exponential backoff: delay = base_delay * 2^attempt
        delay = self.base_delay * (2**attempt)

        # Add jitter if enabled
        if self.jitter:
            jitter_amount = random.random()
            delay += jitter_amount

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        return delay

    def _check_backend_status(self, backend_name: str) -> Optional[Any]:
        """Check the status of a backend via telemetry.

        Args:
            backend_name: Name of the backend.

        Returns:
            SystemStatus enum value or None if telemetry unavailable.
        """
        if not self.telemetry or not HAS_BRIDGE:
            return None

        try:
            return self.telemetry.get_status(backend_name)
        except Exception as e:
            logger.warning(f"Could not check backend status: {e}")
            return None

    def _wait_for_calibration_complete(
        self,
        backend_name: str,
        max_wait: float = 300.0,
        check_interval: float = 5.0,
    ) -> float:
        """Wait for a backend to complete calibration.

        Args:
            backend_name: Name of the backend.
            max_wait: Maximum time to wait in seconds (default: 300s).
            check_interval: Interval between status checks in seconds (default: 5s).

        Returns:
            Total time waited in seconds.
        """
        if not self.telemetry or not HAS_BRIDGE:
            return 0.0

        start_time = time.time()
        last_log_time = start_time

        while time.time() - start_time < max_wait:
            status = self._check_backend_status(backend_name)
            if status != SystemStatus.CALIBRATING:
                total_wait = time.time() - start_time
                logger.info(f"Backend {backend_name} calibration complete after {total_wait:.1f}s")
                return total_wait

            # Log every 30 seconds
            current_time = time.time()
            if current_time - last_log_time >= 30:
                elapsed = current_time - start_time
                logger.debug(f"Still waiting for {backend_name} calibration ({elapsed:.1f}s)")
                last_log_time = current_time

            time.sleep(check_interval)

        total_wait = time.time() - start_time
        logger.warning(f"Timeout waiting for {backend_name} calibration after {total_wait:.1f}s")
        return total_wait
