"""Mock Origin Pilot server for testing."""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from typing import Any, Optional

import zmq

logger = logging.getLogger(__name__)


class OriginPilotMock:
    """Mock Origin Pilot ZMQ server for testing.

    Simulates job submission (Router socket) and telemetry publishing (Publisher socket).
    Supports configurable latency, error rates, and system states.
    """

    def __init__(
        self,
        host: str = "localhost",
        job_port: int = 5555,
        telemetry_port: int = 5556,
        latency_ms: float = 10.0,
        error_rate: float = 0.0,
        calibration_interval_sec: float = 60.0,
    ) -> None:
        """Initialize mock Origin Pilot.

        Args:
            host: Bind address
            job_port: Job submission port (Router)
            telemetry_port: Telemetry publishing port (Publisher)
            latency_ms: Simulated response latency in milliseconds
            error_rate: Probability of job failure (0.0-1.0)
            calibration_interval_sec: Seconds between simulated calibrations
        """
        self.host = host
        self.job_port = job_port
        self.telemetry_port = telemetry_port
        self.latency_ms = latency_ms
        self.error_rate = error_rate
        self.calibration_interval_sec = calibration_interval_sec

        self._context: Optional[zmq.Context] = None
        self._router_socket: Optional[zmq.Socket] = None
        self._publisher_socket: Optional[zmq.Socket] = None

        self._job_threads: list[threading.Thread] = []
        self._router_thread: Optional[threading.Thread] = None
        self._telemetry_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Job tracking
        self._jobs: dict[str, dict[str, Any]] = {}
        self._next_calibration_time = time.time() + calibration_interval_sec
        self._is_calibrating = False

    def start(self) -> None:
        """Start the mock server.

        Creates Router and Publisher sockets and starts background threads
        for job processing and telemetry publishing.

        Raises:
            zmq.error.ZMQError: If socket creation fails
        """
        with self._lock:
            if self._router_thread is not None:
                logger.warning("Mock server already running")
                return

            try:
                self._context = zmq.Context()

                # Create Router socket for job submission
                self._router_socket = self._context.socket(zmq.ROUTER)
                self._router_socket.bind(f"tcp://{self.host}:{self.job_port}")

                # Create Publisher socket for telemetry
                self._publisher_socket = self._context.socket(zmq.PUB)
                self._publisher_socket.bind(f"tcp://{self.host}:{self.telemetry_port}")

                self._stop_event.clear()

                # Start router thread
                self._router_thread = threading.Thread(target=self._run_router, daemon=True)
                self._router_thread.start()

                # Start telemetry thread
                self._telemetry_thread = threading.Thread(
                    target=self._run_telemetry, daemon=True
                )
                self._telemetry_thread.start()

                logger.info(
                    f"Mock Origin Pilot started on {self.host}:"
                    f"{self.job_port}/{self.telemetry_port}"
                )
            except zmq.error.ZMQError as e:
                logger.error(f"Failed to start mock server: {e}")
                raise

    def stop(self) -> None:
        """Stop the mock server.

        Signals all threads to stop and cleans up ZMQ resources.
        """
        with self._lock:
            self._stop_event.set()

            # Wait for threads
            if self._router_thread:
                self._router_thread.join(timeout=5.0)
                self._router_thread = None

            if self._telemetry_thread:
                self._telemetry_thread.join(timeout=5.0)
                self._telemetry_thread = None

            # Wait for job threads
            for thread in self._job_threads:
                thread.join(timeout=5.0)
            self._job_threads.clear()

            # Clean up sockets
            if self._router_socket:
                try:
                    self._router_socket.close()
                except zmq.error.ZMQError as e:
                    logger.warning(f"Error closing router socket: {e}")
                self._router_socket = None

            if self._publisher_socket:
                try:
                    self._publisher_socket.close()
                except zmq.error.ZMQError as e:
                    logger.warning(f"Error closing publisher socket: {e}")
                self._publisher_socket = None

            if self._context:
                try:
                    self._context.term()
                except zmq.error.ZMQError as e:
                    logger.warning(f"Error terminating context: {e}")
                self._context = None

            logger.info("Mock server stopped")

    def _run_router(self) -> None:
        """Router loop for handling job submissions."""
        while not self._stop_event.is_set():
            try:
                if not self._router_socket:
                    time.sleep(0.1)
                    continue

                try:
                    identity, msg_bytes = self._router_socket.recv_multipart(zmq.NOBLOCK)
                except zmq.error.Again:
                    time.sleep(0.01)
                    continue

                # Parse message
                try:
                    msg = json.loads(msg_bytes.decode("utf-8"))
                    msg_type = msg.get("type")

                    if msg_type == "SUBMIT_JOB":
                        self._handle_job_submission(identity, msg)
                    elif msg_type == "GET_JOB_STATUS":
                        self._handle_status_request(identity, msg)
                    elif msg_type == "CANCEL_JOB":
                        self._handle_cancel_request(identity, msg)
                    elif msg_type == "HEARTBEAT":
                        self._handle_heartbeat(identity)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse message: {e}")

            except Exception as e:
                logger.error(f"Error in router: {e}")
                time.sleep(0.1)

    def _handle_job_submission(self, identity: bytes, msg: dict[str, Any]) -> None:
        """Handle job submission.

        Args:
            identity: Router identity
            msg: Submission message
        """
        job_id = msg.get("job_id", "unknown")

        with self._lock:
            self._jobs[job_id] = {
                "status": "QUEUED",
                "submitted_at": time.time(),
                "result": None,
                "error": None,
            }

        # Simulate job processing in background thread
        thread = threading.Thread(
            target=self._process_job, args=(identity, job_id), daemon=True
        )
        thread.start()
        self._job_threads.append(thread)

    def _process_job(self, identity: bytes, job_id: str) -> None:
        """Process a job with simulated latency and possible failure.

        Args:
            identity: Router identity for response
            job_id: Job identifier
        """
        # Simulate latency
        time.sleep(self.latency_ms / 1000.0)

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return

            # Update to RUNNING
            job["status"] = "RUNNING"
            job["started_at"] = time.time()

        # Simulate more processing
        time.sleep(self.latency_ms / 1000.0)

        # Check if should fail
        should_fail = random.random() < self.error_rate

        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return

            if should_fail:
                job["status"] = "FAILED"
                job["error"] = "Simulated backend error"
                job["result"] = None
            else:
                job["status"] = "COMPLETED"
                # Generate simulated result
                job["result"] = {
                    "counts": {"00": 512, "01": 256, "10": 128, "11": 128},
                    "shots": 1024,
                }

        # Send result back
        result_msg = {
            "job_id": job_id,
            "status": job["status"],
            "result": job.get("result"),
            "error": job.get("error"),
            "timestamp": time.time(),
        }

        if self._router_socket:
            try:
                msg_bytes = json.dumps(result_msg).encode("utf-8")
                self._router_socket.send_multipart([identity, msg_bytes])
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to send result: {e}")

    def _handle_status_request(self, identity: bytes, msg: dict[str, Any]) -> None:
        """Handle job status request.

        Args:
            identity: Router identity
            msg: Status request message
        """
        job_id = msg.get("job_id")

        with self._lock:
            job = self._jobs.get(job_id, {})
            status = job.get("status", "UNKNOWN")
            result = job.get("result")
            error = job.get("error")

        response = {
            "job_id": job_id,
            "status": status,
            "result": result,
            "error": error,
            "timestamp": time.time(),
        }

        if self._router_socket:
            try:
                msg_bytes = json.dumps(response).encode("utf-8")
                self._router_socket.send_multipart([identity, msg_bytes])
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to send status: {e}")

    def _handle_cancel_request(self, identity: bytes, msg: dict[str, Any]) -> None:
        """Handle job cancellation request.

        Args:
            identity: Router identity
            msg: Cancel request message
        """
        job_id = msg.get("job_id")

        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "CANCELLED"

        response = {
            "job_id": job_id,
            "status": "CANCELLED",
            "timestamp": time.time(),
        }

        if self._router_socket:
            try:
                msg_bytes = json.dumps(response).encode("utf-8")
                self._router_socket.send_multipart([identity, msg_bytes])
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to send cancel response: {e}")

    def _handle_heartbeat(self, identity: bytes) -> None:
        """Handle heartbeat (ping).

        Args:
            identity: Router identity
        """
        response = {"type": "HEARTBEAT_ACK", "timestamp": time.time()}

        if self._router_socket:
            try:
                msg_bytes = json.dumps(response).encode("utf-8")
                self._router_socket.send_multipart([identity, msg_bytes])
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to send heartbeat response: {e}")

    def _run_telemetry(self) -> None:
        """Telemetry publishing loop."""
        while not self._stop_event.is_set():
            try:
                # Check if calibration should be triggered
                with self._lock:
                    current_time = time.time()
                    if current_time >= self._next_calibration_time and not self._is_calibrating:
                        self._is_calibrating = True
                        self._publish_calibration_started()
                        threading.Thread(
                            target=self._simulate_calibration, daemon=True
                        ).start()

                # Publish system status every second
                self._publish_system_status()
                time.sleep(1.0)

            except Exception as e:
                logger.error(f"Error in telemetry: {e}")
                time.sleep(1.0)

    def _publish_system_status(self) -> None:
        """Publish system status telemetry."""
        with self._lock:
            active_jobs = sum(
                1 for j in self._jobs.values()
                if j["status"] in ("QUEUED", "RUNNING")
            )
            queue_depth = sum(
                1 for j in self._jobs.values()
                if j["status"] == "QUEUED"
            )

        status_msg = {
            "channel": "system_status",
            "payload": {
                "state": "CALIBRATING" if self._is_calibrating else "IDLE",
                "queue_depth": queue_depth,
                "active_jobs": active_jobs,
                "qubit_count": 20,
                "error_rate": 0.01,
                "uptime_seconds": time.time(),
            },
        }

        if self._publisher_socket:
            try:
                msg_bytes = json.dumps(status_msg).encode("utf-8")
                self._publisher_socket.send(msg_bytes)
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to publish status: {e}")

    def _publish_calibration_started(self) -> None:
        """Publish calibration started event."""
        msg = {
            "channel": "calibration",
            "payload": {
                "type": "started",
                "timestamp": time.time(),
            },
        }

        if self._publisher_socket:
            try:
                msg_bytes = json.dumps(msg).encode("utf-8")
                self._publisher_socket.send(msg_bytes)
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to publish calibration started: {e}")

    def _simulate_calibration(self) -> None:
        """Simulate calibration process."""
        time.sleep(0.5)  # Simulate calibration duration

        with self._lock:
            self._is_calibrating = False
            self._next_calibration_time = (
                time.time() + self.calibration_interval_sec
            )

        # Publish calibration completed
        msg = {
            "channel": "calibration",
            "payload": {
                "type": "completed",
                "timestamp": time.time(),
                "next_scheduled": self._next_calibration_time,
            },
        }

        if self._publisher_socket:
            try:
                msg_bytes = json.dumps(msg).encode("utf-8")
                self._publisher_socket.send(msg_bytes)
            except zmq.error.ZMQError as e:
                logger.warning(f"Failed to publish calibration completed: {e}")
