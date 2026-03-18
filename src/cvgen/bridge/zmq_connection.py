"""ZeroMQ connection manager for Origin Pilot communication."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from enum import Enum
from typing import Optional

import zmq

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ZMQConnectionManager:
    """Manages ZeroMQ connections to Origin Pilot.

    Handles job submission via Dealer socket and telemetry reception via Subscriber socket.
    Provides auto-reconnection, health checks, and thread-safe operations.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        job_port: Optional[int] = None,
        telemetry_port: Optional[int] = None,
        reconnect_timeout: float = 5.0,
        socket_timeout_ms: int = 5000,
    ) -> None:
        """Initialize ZMQ connection manager.

        Args:
            host: Origin Pilot host (default from ORIGIN_PILOT_HOST env var or "localhost")
            job_port: Job submission port (default from ORIGIN_PILOT_JOB_PORT or 5555)
            telemetry_port: Telemetry port (default from ORIGIN_PILOT_TELEMETRY_PORT or 5556)
            reconnect_timeout: Timeout between reconnection attempts in seconds
            socket_timeout_ms: Socket send/receive timeout in milliseconds
        """
        self.host = host or os.getenv("ORIGIN_PILOT_HOST", "localhost")
        self.job_port = job_port or int(os.getenv("ORIGIN_PILOT_JOB_PORT", "5555"))
        self.telemetry_port = telemetry_port or int(
            os.getenv("ORIGIN_PILOT_TELEMETRY_PORT", "5556")
        )
        self.reconnect_timeout = reconnect_timeout
        self.socket_timeout_ms = socket_timeout_ms

        self._context: Optional[zmq.Context] = None
        self._dealer_socket: Optional[zmq.Socket] = None
        self._subscriber_socket: Optional[zmq.Socket] = None

        self._state = ConnectionState.DISCONNECTED
        self._lock = threading.Lock()
        self._reconnect_thread: Optional[threading.Thread] = None
        self._reconnect_event = threading.Event()
        self._stop_event = threading.Event()

    def __enter__(self) -> ZMQConnectionManager:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()

    def connect(self) -> None:
        """Establish connections to Origin Pilot.

        Raises:
            zmq.error.ZMQError: If context initialization fails.
        """
        with self._lock:
            if self._state == ConnectionState.CONNECTED:
                return

            try:
                self._context = zmq.Context()

                # Create and configure Dealer socket for job submission
                self._dealer_socket = self._context.socket(zmq.DEALER)
                self._dealer_socket.setsockopt(zmq.LINGER, 0)
                self._dealer_socket.setsockopt(zmq.RCVTIMEO, self.socket_timeout_ms)
                self._dealer_socket.setsockopt(zmq.SNDTIMEO, self.socket_timeout_ms)
                dealer_addr = f"tcp://{self.host}:{self.job_port}"
                self._dealer_socket.connect(dealer_addr)

                # Create and configure Subscriber socket for telemetry
                self._subscriber_socket = self._context.socket(zmq.SUB)
                self._subscriber_socket.setsockopt(zmq.LINGER, 0)
                self._subscriber_socket.setsockopt(zmq.RCVTIMEO, self.socket_timeout_ms)
                self._subscriber_socket.subscribe(b"")
                subscriber_addr = f"tcp://{self.host}:{self.telemetry_port}"
                self._subscriber_socket.connect(subscriber_addr)

                self._state = ConnectionState.CONNECTED
                self._reconnect_event.clear()
                logger.info(
                    f"Connected to Origin Pilot at {self.host}:"
                    f"{self.job_port}/{self.telemetry_port}"
                )
            except zmq.error.ZMQError as e:
                self._state = ConnectionState.ERROR
                logger.error(f"Failed to connect to Origin Pilot: {e}")
                raise

    def disconnect(self) -> None:
        """Cleanly disconnect from Origin Pilot."""
        with self._lock:
            self._stop_event.set()

            if self._dealer_socket:
                try:
                    self._dealer_socket.close()
                except zmq.error.ZMQError as e:
                    logger.warning(f"Error closing dealer socket: {e}")
                self._dealer_socket = None

            if self._subscriber_socket:
                try:
                    self._subscriber_socket.close()
                except zmq.error.ZMQError as e:
                    logger.warning(f"Error closing subscriber socket: {e}")
                self._subscriber_socket = None

            if self._context:
                try:
                    self._context.term()
                except zmq.error.ZMQError as e:
                    logger.warning(f"Error terminating context: {e}")
                self._context = None

            self._state = ConnectionState.DISCONNECTED
            logger.info("Disconnected from Origin Pilot")

    def send_job(self, job_msg: dict) -> str:
        """Send a job submission message to Origin Pilot.

        Args:
            job_msg: Job message dictionary with required fields

        Returns:
            Job ID from the message

        Raises:
            RuntimeError: If not connected
            zmq.error.ZMQError: If send fails
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED or not self._dealer_socket:
                raise RuntimeError(
                    f"Cannot send job: connection state is {self._state.value}"
                )

            try:
                msg_bytes = json.dumps(job_msg).encode("utf-8")
                self._dealer_socket.send(msg_bytes)
                job_id = job_msg.get("job_id", "unknown")
                logger.debug(f"Sent job {job_id}")
                return job_id
            except zmq.error.Again:
                logger.error("Send timeout: Origin Pilot not responding")
                self._trigger_reconnect()
                raise RuntimeError("Send timeout: Origin Pilot not responding")
            except zmq.error.ZMQError as e:
                logger.error(f"Failed to send job: {e}")
                self._trigger_reconnect()
                raise

    def receive_result(self, timeout_ms: Optional[int] = None) -> Optional[dict]:
        """Receive a job result from Origin Pilot.

        Args:
            timeout_ms: Receive timeout in milliseconds (uses socket default if None)

        Returns:
            Parsed result dictionary or None if timeout

        Raises:
            RuntimeError: If not connected
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED or not self._dealer_socket:
                raise RuntimeError(
                    f"Cannot receive result: connection state is {self._state.value}"
                )

            try:
                original_timeout = self._dealer_socket.getsockopt(zmq.RCVTIMEO)
                if timeout_ms is not None:
                    self._dealer_socket.setsockopt(zmq.RCVTIMEO, timeout_ms)

                # DEALER sockets may receive multipart messages; get all parts
                msg_parts = self._dealer_socket.recv_multipart(flags=zmq.NOBLOCK if timeout_ms == 0 else 0)

                if timeout_ms is not None:
                    self._dealer_socket.setsockopt(zmq.RCVTIMEO, original_timeout)

                # The last part is usually the actual message content
                if msg_parts:
                    msg_bytes = msg_parts[-1]
                else:
                    return None

                result = json.loads(msg_bytes.decode("utf-8"))
                logger.debug(f"Received result: {result.get('job_id', 'unknown')}")
                return result
            except zmq.error.Again:
                return None
            except zmq.error.ZMQError as e:
                logger.error(f"Failed to receive result: {e}")
                self._trigger_reconnect()
                raise
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode message: {e}")
                return None

    def receive_telemetry(self, timeout_ms: Optional[int] = None) -> Optional[dict]:
        """Receive a telemetry message.

        Args:
            timeout_ms: Receive timeout in milliseconds (uses socket default if None)

        Returns:
            Parsed telemetry dictionary or None if timeout

        Raises:
            RuntimeError: If not connected
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED or not self._subscriber_socket:
                raise RuntimeError(
                    f"Cannot receive telemetry: connection state is {self._state.value}"
                )

            try:
                original_timeout = self._subscriber_socket.getsockopt(zmq.RCVTIMEO)
                if timeout_ms is not None:
                    self._subscriber_socket.setsockopt(zmq.RCVTIMEO, timeout_ms)

                msg_bytes = self._subscriber_socket.recv(
                    flags=zmq.NOBLOCK if timeout_ms == 0 else 0
                )

                if timeout_ms is not None:
                    self._subscriber_socket.setsockopt(zmq.RCVTIMEO, original_timeout)

                telemetry = json.loads(msg_bytes.decode("utf-8"))
                return telemetry
            except zmq.error.Again:
                return None
            except zmq.error.ZMQError as e:
                logger.error(f"Failed to receive telemetry: {e}")
                return None
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Failed to decode telemetry: {e}")
                return None

    def health_check(self, timeout_ms: int = 2000) -> bool:
        """Check if Origin Pilot is responding.

        Sends a simple ping-style message and expects a response.

        Args:
            timeout_ms: Health check timeout in milliseconds

        Returns:
            True if healthy, False otherwise
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED:
                return False

            try:
                heartbeat_msg = {"type": "HEARTBEAT", "timestamp": time.time()}
                msg_bytes = json.dumps(heartbeat_msg).encode("utf-8")

                original_send_timeout = self._dealer_socket.getsockopt(zmq.SNDTIMEO)
                original_recv_timeout = self._dealer_socket.getsockopt(zmq.RCVTIMEO)

                self._dealer_socket.setsockopt(zmq.SNDTIMEO, timeout_ms // 2)
                self._dealer_socket.setsockopt(zmq.RCVTIMEO, timeout_ms // 2)

                self._dealer_socket.send(msg_bytes)
                response = self._dealer_socket.recv(zmq.NOBLOCK)

                self._dealer_socket.setsockopt(zmq.SNDTIMEO, original_send_timeout)
                self._dealer_socket.setsockopt(zmq.RCVTIMEO, original_recv_timeout)

                logger.debug("Health check passed")
                return response is not None
            except (zmq.error.Again, zmq.error.ZMQError):
                logger.warning("Health check failed")
                return False

    def _trigger_reconnect(self) -> None:
        """Trigger automatic reconnection."""
        if self._state == ConnectionState.CONNECTED:
            self._state = ConnectionState.RECONNECTING
            self._reconnect_event.set()

    def get_state(self) -> ConnectionState:
        """Get current connection state."""
        with self._lock:
            return self._state

    def is_connected(self) -> bool:
        """Check if currently connected."""
        with self._lock:
            return self._state == ConnectionState.CONNECTED
