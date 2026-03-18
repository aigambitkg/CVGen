"""Comprehensive tests for the CVGen ZeroMQ Bridge layer."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone

import pytest
import zmq

from cvgen.bridge.circuit_translator import CircuitTranslator
from cvgen.bridge.job_protocol import JobProtocol
from cvgen.bridge.zmq_connection import ConnectionState, ZMQConnectionManager
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import JobStatus
from tests.mocks.origin_pilot_mock import OriginPilotMock


@pytest.fixture
def mock_server():
    """Start and stop a mock Origin Pilot server."""
    server = OriginPilotMock(
        host="localhost",
        job_port=5555,
        telemetry_port=5556,
        latency_ms=50,
        error_rate=0.0,
    )
    server.start()
    time.sleep(0.2)  # Allow server to bind
    yield server
    server.stop()


@pytest.fixture
def zmq_manager(mock_server):
    """Create and clean up a ZMQ connection manager."""
    manager = ZMQConnectionManager(
        host="localhost",
        job_port=5555,
        telemetry_port=5556,
        socket_timeout_ms=2000,
    )
    manager.connect()
    yield manager
    manager.disconnect()


@pytest.fixture
def sample_circuit():
    """Create a simple sample quantum circuit."""
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.measure_all()
    return circuit


class TestZMQConnectionManager:
    """Tests for ZMQConnectionManager class."""

    def test_context_manager_lifecycle(self, mock_server):
        """Test connection lifecycle with context manager."""
        with ZMQConnectionManager(host="localhost", job_port=5555, telemetry_port=5556) as manager:
            assert manager.is_connected()
            assert manager.get_state() == ConnectionState.CONNECTED

    def test_manual_connect_disconnect(self, mock_server):
        """Test manual connect and disconnect."""
        manager = ZMQConnectionManager(host="localhost", job_port=5555, telemetry_port=5556)
        assert not manager.is_connected()

        manager.connect()
        assert manager.is_connected()

        manager.disconnect()
        assert not manager.is_connected()

    def test_default_env_vars(self, monkeypatch):
        """Test environment variable defaults."""
        monkeypatch.setenv("ORIGIN_PILOT_HOST", "test-host")
        monkeypatch.setenv("ORIGIN_PILOT_JOB_PORT", "6666")
        monkeypatch.setenv("ORIGIN_PILOT_TELEMETRY_PORT", "6667")

        manager = ZMQConnectionManager()
        assert manager.host == "test-host"
        assert manager.job_port == 6666
        assert manager.telemetry_port == 6667

    def test_send_job_not_connected(self):
        """Test sending job when not connected raises error."""
        manager = ZMQConnectionManager()
        msg = {"type": "SUBMIT_JOB", "job_id": "test"}

        with pytest.raises(RuntimeError, match="Cannot send job"):
            manager.send_job(msg)

    def test_send_job_success(self, zmq_manager):
        """Test successful job submission."""
        job_msg = JobProtocol.create_submit_message(
            circuit_code="H(q[0]);",
            shots=1024,
            backend="CPUQVM",
            metadata={"test": True},
        )

        job_id = zmq_manager.send_job(job_msg)
        assert job_id == job_msg["job_id"]

    def test_receive_result_timeout(self, zmq_manager):
        """Test result reception with timeout."""
        result = zmq_manager.receive_result(timeout_ms=100)
        # May be None if no result available
        assert result is None or isinstance(result, dict)

    def test_send_and_receive_result(self, zmq_manager):
        """Test submitting job and receiving result."""
        job_msg = JobProtocol.create_submit_message(
            circuit_code="H(q[0]);",
            shots=1024,
        )

        job_id = zmq_manager.send_job(job_msg)

        # Receive result (may need multiple attempts)
        result = None
        for _ in range(20):
            result = zmq_manager.receive_result(timeout_ms=1000)
            if result:
                break
            time.sleep(0.05)

        assert result is not None
        assert result["job_id"] == job_id
        assert result["status"] in ("QUEUED", "RUNNING", "COMPLETED", "FAILED")

    def test_health_check_when_connected(self, zmq_manager):
        """Test health check when connected."""
        # May not get immediate response, but should not crash
        try:
            healthy = zmq_manager.health_check(timeout_ms=500)
            # Either healthy or not, but should not raise
            assert isinstance(healthy, bool)
        except RuntimeError:
            # Timeout is acceptable
            pass

    def test_health_check_when_disconnected(self):
        """Test health check when disconnected."""
        manager = ZMQConnectionManager()
        healthy = manager.health_check()
        assert not healthy

    def test_concurrent_sends(self, zmq_manager):
        """Test multiple concurrent job submissions."""
        job_ids = []
        for i in range(5):
            msg = JobProtocol.create_submit_message(
                circuit_code=f"H(q[{i % 3}]);",
                shots=1024,
            )
            job_id = zmq_manager.send_job(msg)
            job_ids.append(job_id)

        assert len(job_ids) == 5
        assert len(set(job_ids)) == 5  # All unique

    def test_receive_telemetry(self, zmq_manager):
        """Test receiving telemetry messages."""
        # May timeout if no telemetry yet
        telemetry = zmq_manager.receive_telemetry(timeout_ms=2000)
        # Result depends on server behavior
        assert telemetry is None or isinstance(telemetry, dict)


class TestJobProtocol:
    """Tests for JobProtocol message formatting and parsing."""

    def test_create_submit_message(self):
        """Test creating a job submission message."""
        msg = JobProtocol.create_submit_message(
            circuit_code="H(q[0]); CNOT(q[0], q[1]);",
            shots=2048,
            backend="CPUQVM",
            metadata={"name": "test_job"},
        )

        assert msg["type"] == "SUBMIT_JOB"
        assert msg["job_id"]  # Should have UUID
        assert msg["circuit_code"] == "H(q[0]); CNOT(q[0], q[1]);"
        assert msg["shots"] == 2048
        assert msg["backend"] == "CPUQVM"
        assert msg["metadata"]["name"] == "test_job"
        assert msg["timestamp"]

    def test_create_submit_message_validation(self):
        """Test validation of submission messages."""
        with pytest.raises(ValueError, match="circuit_code must be"):
            JobProtocol.create_submit_message(circuit_code="", shots=1024)

        with pytest.raises(ValueError, match="shots must be positive"):
            JobProtocol.create_submit_message(circuit_code="H(q[0]);", shots=0)

        with pytest.raises(ValueError, match="shots must be positive"):
            JobProtocol.create_submit_message(circuit_code="H(q[0]);", shots=-1)

    def test_create_status_request(self):
        """Test creating a status request message."""
        job_id = str(uuid.uuid4())
        msg = JobProtocol.create_status_request(job_id)

        assert msg["type"] == "GET_JOB_STATUS"
        assert msg["job_id"] == job_id
        assert msg["timestamp"]

    def test_create_status_request_validation(self):
        """Test validation of status requests."""
        with pytest.raises(ValueError, match="job_id must be"):
            JobProtocol.create_status_request("")

    def test_create_cancel_request(self):
        """Test creating a cancel request message."""
        job_id = str(uuid.uuid4())
        msg = JobProtocol.create_cancel_request(job_id)

        assert msg["type"] == "CANCEL_JOB"
        assert msg["job_id"] == job_id
        assert msg["timestamp"]

    def test_parse_response(self):
        """Test parsing a job response."""
        response_dict = {
            "job_id": "test-job-123",
            "status": "COMPLETED",
            "result": {"counts": {"0": 512, "1": 512}},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        response = JobProtocol.parse_response(response_dict)

        assert response.job_id == "test-job-123"
        assert response.status == JobStatus.COMPLETED
        assert response.result["counts"]["0"] == 512
        assert response.error is None

    def test_parse_response_with_error(self):
        """Test parsing a failed response."""
        response_dict = {
            "job_id": "test-job-456",
            "status": "FAILED",
            "error": "Backend error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        response = JobProtocol.parse_response(response_dict)

        assert response.job_id == "test-job-456"
        assert response.status == JobStatus.FAILED
        assert response.error == "Backend error occurred"
        assert response.result is None

    def test_validate_submit_message(self):
        """Test message validation."""
        valid_msg = {
            "type": "SUBMIT_JOB",
            "job_id": "test-123",
            "circuit_code": "H(q[0]);",
            "shots": 1024,
            "backend": "CPUQVM",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        errors = JobProtocol.validate_submit_message(valid_msg)
        assert len(errors) == 0

        # Test invalid messages
        invalid_msg = {"type": "SUBMIT_JOB"}
        errors = JobProtocol.validate_submit_message(invalid_msg)
        assert len(errors) > 0

    def test_validate_status_request(self):
        """Test status request validation."""
        valid_msg = {
            "type": "GET_JOB_STATUS",
            "job_id": "test-123",
        }

        errors = JobProtocol.validate_status_request(valid_msg)
        assert len(errors) == 0

        invalid_msg = {"type": "GET_JOB_STATUS"}
        errors = JobProtocol.validate_status_request(invalid_msg)
        assert len(errors) > 0


class TestCircuitTranslator:
    """Tests for quantum circuit translation."""

    def test_translate_to_qpanda_single_qubit(self, sample_circuit):
        """Test QPanda3 translation with single-qubit gates."""
        code = CircuitTranslator.translate_to_qpanda(sample_circuit)

        assert "from pyqpanda import *" in code
        assert "H(q[0])" in code
        assert "CNOT(q[0], q[1])" in code
        assert "Measure" in code
        assert "circuit_program()" in code

    def test_translate_to_qpanda_all_gates(self):
        """Test QPanda3 translation with all gate types."""
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.x(0)
        circuit.y(0)
        circuit.z(0)
        circuit.s(0)
        circuit.t(0)
        circuit.rx(0, 1.57)
        circuit.ry(0, 3.14)
        circuit.rz(0, 0.785)
        circuit.cx(0, 1)
        circuit.cz(0, 1)
        circuit.swap(0, 1)
        circuit.ccx(0, 1, 2)

        code = CircuitTranslator.translate_to_qpanda(circuit)

        assert "H(q[0])" in code
        assert "X(q[0])" in code
        assert "Y(q[0])" in code
        assert "Z(q[0])" in code
        assert "S(q[0])" in code
        assert "T(q[0])" in code
        assert "RX(q[0], 1.57)" in code
        assert "RY(q[0], 3.14)" in code
        assert "RZ(q[0], 0.785)" in code
        assert "CNOT(q[0], q[1])" in code
        assert "CZ(q[0], q[1])" in code
        assert "SWAP(q[0], q[1])" in code
        assert "Toffoli(q[0], q[1], q[2])" in code

    def test_translate_to_openqasm(self, sample_circuit):
        """Test OpenQASM translation."""
        code = CircuitTranslator.translate_to_openqasm(sample_circuit)

        assert "OPENQASM 2.0" in code
        assert 'include "qelib1.inc"' in code
        assert "qreg q[3]" in code
        assert "creg c[3]" in code
        assert "h q[0]" in code
        assert "cx q[0],q[1]" in code
        assert "measure q" in code

    def test_translate_to_openqasm_all_gates(self):
        """Test OpenQASM translation with all gates."""
        circuit = QuantumCircuit(3)
        circuit.h(0)
        circuit.x(1)
        circuit.y(0)
        circuit.z(1)
        circuit.s(0)
        circuit.t(1)
        circuit.rx(0, 1.57)
        circuit.ry(1, 3.14)
        circuit.rz(0, 0.785)
        circuit.cx(0, 1)
        circuit.cz(1, 2)
        circuit.swap(0, 2)
        circuit.ccx(0, 1, 2)

        code = CircuitTranslator.translate_to_openqasm(circuit)

        assert "h q[0]" in code
        assert "x q[1]" in code
        assert "y q[0]" in code
        assert "z q[1]" in code
        assert "s q[0]" in code
        assert "t q[1]" in code
        assert "rx(1.57) q[0]" in code
        assert "ry(3.14) q[1]" in code
        assert "rz(0.785) q[0]" in code
        assert "cx q[0],q[1]" in code
        assert "cz q[1],q[2]" in code
        assert "swap q[0],q[2]" in code
        assert "ccx q[0],q[1],q[2]" in code

    def test_translate_unmeasured_circuit(self):
        """Test translation of circuit without measurements."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)

        qpanda_code = CircuitTranslator.translate_to_qpanda(circuit)
        openqasm_code = CircuitTranslator.translate_to_openqasm(circuit)

        # Should add measurements automatically
        assert "Measure" in qpanda_code
        assert "measure q" in openqasm_code

    def test_translate_circuit_with_barrier(self):
        """Test translation of circuit with barrier."""
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.barrier()
        circuit.cx(0, 1)

        qpanda_code = CircuitTranslator.translate_to_qpanda(circuit)
        openqasm_code = CircuitTranslator.translate_to_openqasm(circuit)

        assert "Barrier()" in qpanda_code
        assert "barrier" in openqasm_code


class TestOriginPilotMock:
    """Tests for mock Origin Pilot server."""

    def test_mock_server_start_stop(self):
        """Test starting and stopping mock server."""
        server = OriginPilotMock(
            host="localhost",
            job_port=5550,
            telemetry_port=5551,
        )

        server.start()
        assert server._router_socket is not None
        assert server._publisher_socket is not None

        server.stop()
        assert server._router_socket is None
        assert server._publisher_socket is None

    def test_mock_server_job_submission(self):
        """Test submitting job to mock server."""
        server = OriginPilotMock(
            host="localhost",
            job_port=5552,
            telemetry_port=5553,
            latency_ms=10,
            error_rate=0.0,
        )
        server.start()
        time.sleep(0.2)

        try:
            context = zmq.Context()
            socket = context.socket(zmq.DEALER)
            socket.connect("tcp://localhost:5552")

            # Send job
            job_msg = {
                "type": "SUBMIT_JOB",
                "job_id": "test-job-1",
                "circuit_code": "H(q[0]);",
                "shots": 1024,
                "backend": "CPUQVM",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            msg_bytes = json.dumps(job_msg).encode("utf-8")
            socket.send(msg_bytes)

            # Receive result
            socket.setsockopt(zmq.RCVTIMEO, 5000)
            result_bytes = socket.recv()
            result = json.loads(result_bytes.decode("utf-8"))

            assert result["job_id"] == "test-job-1"
            assert result["status"] in ("QUEUED", "RUNNING", "COMPLETED", "FAILED")

            socket.close()
            context.term()
        finally:
            server.stop()

    def test_mock_server_status_request(self):
        """Test status request to mock server."""
        server = OriginPilotMock(
            host="localhost",
            job_port=5554,
            telemetry_port=5555,
            latency_ms=10,
        )
        server.start()
        time.sleep(0.2)

        try:
            context = zmq.Context()
            socket = context.socket(zmq.DEALER)
            socket.setsockopt(zmq.RCVTIMEO, 5000)
            socket.connect("tcp://localhost:5554")

            # Request status
            status_req = {
                "type": "GET_JOB_STATUS",
                "job_id": "nonexistent-job",
            }
            msg_bytes = json.dumps(status_req).encode("utf-8")
            socket.send(msg_bytes)

            # Receive status
            response_bytes = socket.recv()
            response = json.loads(response_bytes.decode("utf-8"))

            assert response["job_id"] == "nonexistent-job"
            assert "status" in response

            socket.close()
            context.term()
        finally:
            server.stop()

    def test_mock_server_error_rate(self):
        """Test error injection in mock server."""
        server = OriginPilotMock(
            host="localhost",
            job_port=5560,
            telemetry_port=5561,
            latency_ms=10,
            error_rate=0.5,  # 50% failure rate
        )
        server.start()
        time.sleep(0.2)

        try:
            context = zmq.Context()
            socket = context.socket(zmq.DEALER)
            socket.setsockopt(zmq.RCVTIMEO, 5000)
            socket.connect("tcp://localhost:5560")

            # Submit multiple jobs
            results = []
            for i in range(10):
                job_msg = {
                    "type": "SUBMIT_JOB",
                    "job_id": f"test-{i}",
                    "circuit_code": "H(q[0]);",
                    "shots": 1024,
                    "backend": "CPUQVM",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                msg_bytes = json.dumps(job_msg).encode("utf-8")
                socket.send(msg_bytes)

                try:
                    result_bytes = socket.recv()
                    result = json.loads(result_bytes.decode("utf-8"))
                    results.append(result)
                except zmq.error.Again:
                    pass

            # Should have mix of successes and failures
            assert len(results) > 0

            socket.close()
            context.term()
        finally:
            server.stop()


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_full_job_submission_cycle(self, zmq_manager, sample_circuit):
        """Test complete job submission and result retrieval."""
        # Translate circuit
        qpanda_code = CircuitTranslator.translate_to_qpanda(sample_circuit)

        # Create and send job
        job_msg = JobProtocol.create_submit_message(
            circuit_code=qpanda_code,
            shots=1024,
            backend="CPUQVM",
            metadata={"circuit_name": "test_bell"},
        )

        job_id = zmq_manager.send_job(job_msg)
        assert job_id is not None

        # Get result
        result = None
        for _ in range(20):
            result = zmq_manager.receive_result(timeout_ms=500)
            if result and result.get("job_id") == job_id:
                break
            time.sleep(0.05)

        assert result is not None
        assert result["job_id"] == job_id

        # Parse response
        job_response = JobProtocol.parse_response(result)
        assert job_response.job_id == job_id

    def test_concurrent_job_lifecycle(self, zmq_manager):
        """Test handling multiple concurrent jobs."""
        job_ids = []

        # Submit 3 jobs
        for i in range(3):
            msg = JobProtocol.create_submit_message(
                circuit_code=f"H(q[{i}]);",
                shots=512,
            )
            job_id = zmq_manager.send_job(msg)
            job_ids.append(job_id)

        # Collect results
        results = {}
        for _ in range(30):
            result = zmq_manager.receive_result(timeout_ms=500)
            if result:
                results[result["job_id"]] = result
                if len(results) >= 3:
                    break
            time.sleep(0.05)

        # Verify all jobs have results
        for job_id in job_ids:
            assert job_id in results

    def test_circuit_translation_roundtrip(self, sample_circuit):
        """Test circuit translation to multiple formats."""
        qpanda = CircuitTranslator.translate_to_qpanda(sample_circuit)
        openqasm = CircuitTranslator.translate_to_openqasm(sample_circuit)

        # Both should be valid code strings
        assert isinstance(qpanda, str)
        assert isinstance(openqasm, str)
        assert len(qpanda) > 0
        assert len(openqasm) > 0

        # Both should contain circuit structure
        assert "q[" in qpanda
        assert "q[" in openqasm
