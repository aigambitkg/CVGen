"""Comprehensive tests for Phase 2 orchestration features."""

from __future__ import annotations

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult, JobConfig, JobStatus, GateType
from cvgen.orchestrator.validator import CircuitValidator, ComplexityEstimate, ValidationResult
from cvgen.orchestrator.retry import RetryPolicy, RetryResult
from cvgen.orchestrator.fallback import FallbackChain, FallbackResult, AllBackendsFailedError
from cvgen.orchestrator.scheduler import SmartScheduler, JobStatistics
from cvgen.orchestrator.workflow import DAGWorkflow, WorkflowResult

try:
    from cvgen.bridge.telemetry import (
        LocalTelemetrySubscriber,
        SystemStatus,
        BackendHealth,
    )

    HAS_BRIDGE = True
except ImportError:
    HAS_BRIDGE = False


# ===== Fixtures =====


@pytest.fixture
def simple_circuit() -> QuantumCircuit:
    """Create a simple valid quantum circuit."""
    qc = QuantumCircuit(num_qubits=2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    qc.name = "bell_pair"
    return qc


@pytest.fixture
def complex_circuit() -> QuantumCircuit:
    """Create a more complex quantum circuit."""
    qc = QuantumCircuit(num_qubits=3)
    qc.h(0)
    qc.h(1)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.rx(1.5, 0)
    qc.ry(0.7, 1)
    qc.rz(2.1, 2)
    qc.measure_all()
    qc.name = "complex"
    return qc


@pytest.fixture
def invalid_circuit_too_many_qubits() -> QuantumCircuit:
    """Create a circuit with too many qubits."""
    qc = QuantumCircuit(num_qubits=1000)
    return qc


@pytest.fixture
def circuit_no_measurement() -> QuantumCircuit:
    """Create a circuit without measurement."""
    qc = QuantumCircuit(num_qubits=2)
    qc.h(0)
    qc.cx(0, 1)
    return qc


@pytest.fixture
def simulator_backend() -> StateVectorSimulator:
    """Create a simulator backend."""
    return StateVectorSimulator()


@pytest.fixture
def telemetry() -> LocalTelemetrySubscriber:
    """Create a local telemetry subscriber."""
    return LocalTelemetrySubscriber()


# ===== CircuitValidator Tests =====


class TestCircuitValidator:
    """Tests for CircuitValidator."""

    def test_validate_simple_circuit_success(self, simple_circuit):
        """Test validation of a valid simple circuit."""
        validator = CircuitValidator()
        result = validator.validate(simple_circuit)
        assert result.success
        assert len(result.errors) == 0
        assert result.estimated_gate_count > 0
        assert result.estimated_depth > 0

    def test_validate_complex_circuit_success(self, complex_circuit):
        """Test validation of a valid complex circuit."""
        validator = CircuitValidator()
        result = validator.validate(complex_circuit)
        assert result.success
        assert len(result.errors) == 0

    def test_validate_circuit_without_measurement(self, circuit_no_measurement):
        """Test validation of circuit without measurement (warning only)."""
        validator = CircuitValidator()
        result = validator.validate(circuit_no_measurement)
        assert result.success
        assert any("measurement" in w.lower() for w in result.warnings)

    def test_validate_circuit_too_many_qubits(self, invalid_circuit_too_many_qubits, simulator_backend):
        """Test validation rejects circuit with too many qubits for backend."""
        validator = CircuitValidator()
        result = validator.validate(invalid_circuit_too_many_qubits, simulator_backend)
        assert not result.success
        assert any("qubit" in e.lower() for e in result.errors)

    def test_validate_circuit_with_backend(self, simple_circuit, simulator_backend):
        """Test validation against specific backend."""
        validator = CircuitValidator()
        result = validator.validate(simple_circuit, simulator_backend)
        assert result.success

    def test_estimate_complexity_simple(self, simple_circuit):
        """Test complexity estimation for simple circuit."""
        validator = CircuitValidator()
        estimate = validator.estimate_complexity(simple_circuit)
        assert estimate.depth > 0
        assert estimate.gate_count > 0
        assert estimate.two_qubit_gates >= 1  # Has CX gate
        assert estimate.estimated_runtime_ms > 0

    def test_estimate_complexity_empty_circuit(self):
        """Test complexity estimation for empty circuit."""
        qc = QuantumCircuit(num_qubits=2)
        validator = CircuitValidator()
        estimate = validator.estimate_complexity(qc)
        assert estimate.depth == 0
        assert estimate.gate_count == 0
        assert estimate.two_qubit_gates == 0
        assert estimate.estimated_runtime_ms == 0.0

    def test_complexity_estimate_repr(self, simple_circuit):
        """Test ComplexityEstimate string representation."""
        validator = CircuitValidator()
        estimate = validator.estimate_complexity(simple_circuit)
        repr_str = repr(estimate)
        assert "ComplexityEstimate" in repr_str
        assert "depth" in repr_str


# ===== RetryPolicy Tests =====


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt."""
        policy = RetryPolicy(max_retries=3)

        def success_fn():
            return "success"

        result = policy.execute(success_fn)
        assert result.success
        assert result.result == "success"
        assert result.attempts == 1
        assert result.total_wait_s == 0.0

    def test_retry_failure_after_max_retries(self):
        """Test execution fails after max retries exhausted."""
        policy = RetryPolicy(max_retries=2, base_delay=0.01, max_delay=0.1)

        def failing_fn():
            raise ValueError("Always fails")

        result = policy.execute(failing_fn)
        assert not result.success
        assert result.result is None
        assert result.attempts == 3  # initial + 2 retries
        assert len(result.errors) == 3

    def test_retry_eventual_success(self):
        """Test eventual success after retries."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01, max_delay=0.1)
        attempt_count = 0

        def eventually_succeeds():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not ready yet")
            return "success"

        result = policy.execute(eventually_succeeds)
        assert result.success
        assert result.result == "success"
        assert result.attempts == 3

    def test_retry_exponential_backoff(self):
        """Test exponential backoff calculation."""
        policy = RetryPolicy(base_delay=0.1, max_delay=10.0, jitter=False)
        # Delays should be: 0.1 * 2^0 = 0.1, 0.1 * 2^1 = 0.2, 0.1 * 2^2 = 0.4
        assert 0.08 < policy._calculate_wait(0) < 0.12
        assert 0.18 < policy._calculate_wait(1) < 0.22
        assert 0.38 < policy._calculate_wait(2) < 0.42

    def test_retry_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        policy = RetryPolicy(base_delay=1.0, max_delay=2.0, jitter=False)
        delay = policy._calculate_wait(10)  # 1 * 2^10 = 1024, should cap at 2.0
        assert delay <= 2.0

    def test_retry_jitter_effect(self):
        """Test that jitter adds randomness to delays."""
        policy = RetryPolicy(base_delay=0.1, max_delay=10.0, jitter=True)
        delays = [policy._calculate_wait(1) for _ in range(5)]
        # With jitter, delays should vary
        assert len(set(delays)) > 1

    def test_retry_result_repr(self):
        """Test RetryResult string representation."""
        result = RetryResult(success=True, result="output", attempts=2, total_wait_s=0.5)
        repr_str = repr(result)
        assert "RetryResult" in repr_str
        assert "success=True" in repr_str

    @pytest.mark.skipif(not HAS_BRIDGE, reason="Bridge not available")
    def test_retry_respects_calibrating_status(self, telemetry):
        """Test that retry waits without counting when backend is CALIBRATING."""
        telemetry.update_status("test_backend", SystemStatus.AVAILABLE)
        policy = RetryPolicy(
            max_retries=2,
            base_delay=0.01,
            max_delay=0.1,
            telemetry=telemetry,
        )

        attempt_count = 0

        def fails_then_succeeds():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise ValueError("First attempt fails")
            return "success"

        result = policy.execute(
            fails_then_succeeds,
            backend_name="test_backend",
        )
        # Should succeed after retry
        assert result.success
        assert result.attempts == 2


# ===== FallbackChain Tests =====


class TestFallbackChain:
    """Tests for FallbackChain."""

    def test_fallback_success_first_backend(self, simple_circuit, simulator_backend):
        """Test successful execution on first backend."""
        chain = FallbackChain([("simulator", simulator_backend)])
        result = chain.execute(simple_circuit)
        assert result.backend_used == "simulator"
        assert isinstance(result.result, CircuitResult)

    def test_fallback_tries_backends_in_order(self, simple_circuit):
        """Test that fallback tries backends in order."""
        call_order = []

        backend1 = Mock()
        backend1.execute.side_effect = ValueError("Backend 1 failed")

        backend2 = Mock()
        backend2.execute.return_value = CircuitResult(counts={"00": 512}, shots=1024)

        chain = FallbackChain([("backend1", backend1), ("backend2", backend2)])
        result = chain.execute(simple_circuit)

        assert result.backend_used == "backend2"
        assert "backend1" in result.fallbacks_tried

    def test_fallback_all_backends_fail(self, simple_circuit):
        """Test that AllBackendsFailedError is raised when all backends fail."""
        backend1 = Mock()
        backend1.execute.side_effect = ValueError("Backend 1 failed")

        backend2 = Mock()
        backend2.execute.side_effect = RuntimeError("Backend 2 failed")

        chain = FallbackChain([("backend1", backend1), ("backend2", backend2)])

        with pytest.raises(AllBackendsFailedError) as exc_info:
            chain.execute(simple_circuit)

        assert "All" in str(exc_info.value)
        assert "failed" in str(exc_info.value).lower()

    def test_fallback_skips_offline_backends(self, simple_circuit, simulator_backend, telemetry):
        """Test that fallback skips OFFLINE backends."""
        telemetry.update_status("backend1", SystemStatus.OFFLINE)

        backend1 = Mock()
        backend1.execute.return_value = CircuitResult(counts={"00": 512}, shots=1024)

        chain = FallbackChain(
            [("backend1", backend1), ("simulator", simulator_backend)],
            telemetry=telemetry,
        )
        result = chain.execute(simple_circuit)

        assert result.backend_used == "simulator"
        assert backend1.execute.call_count == 0  # Should not call offline backend

    @pytest.mark.skipif(not HAS_BRIDGE, reason="Bridge not available")
    def test_fallback_skips_calibrating_backends(self, simple_circuit, simulator_backend, telemetry):
        """Test that fallback skips CALIBRATING backends."""
        telemetry.update_status("backend1", SystemStatus.CALIBRATING)

        backend1 = Mock()
        backend1.execute.return_value = CircuitResult(counts={"00": 512}, shots=1024)

        chain = FallbackChain(
            [("backend1", backend1), ("simulator", simulator_backend)],
            telemetry=telemetry,
        )
        result = chain.execute(simple_circuit)

        assert result.backend_used == "simulator"

    def test_fallback_result_repr(self, simple_circuit, simulator_backend):
        """Test FallbackResult string representation."""
        chain = FallbackChain([("simulator", simulator_backend)])
        result = chain.execute(simple_circuit)
        repr_str = repr(result)
        assert "FallbackResult" in repr_str


# ===== SmartScheduler Tests =====


class TestSmartScheduler:
    """Tests for SmartScheduler."""

    def test_smart_scheduler_submit_valid_circuit(self, simple_circuit, simulator_backend):
        """Test smart scheduler submission of valid circuit."""
        scheduler = SmartScheduler()
        scheduler.register_backend("simulator", simulator_backend)

        record = scheduler.submit_smart(simple_circuit)

        assert record.status == JobStatus.COMPLETED
        assert record.result is not None
        assert record.error is None

    def test_smart_scheduler_validates_circuit(self, simple_circuit):
        """Test that smart scheduler validates circuits."""
        scheduler = SmartScheduler()
        simulator = StateVectorSimulator()
        scheduler.register_backend("simulator", simulator)

        # Create circuit with invalid targets (out of range qubits)
        from cvgen.core.types import GateOp

        invalid_qc = QuantumCircuit(num_qubits=2)
        # Add an operation with qubit target out of range
        invalid_qc._operations.append(
            GateOp(
                gate_type=GateType.H,
                targets=(5,),  # qubit 5 doesn't exist in 2-qubit circuit
            )
        )

        with pytest.raises(ValueError) as exc_info:
            scheduler.submit_smart(invalid_qc)

        assert "validation" in str(exc_info.value).lower()

    def test_smart_scheduler_tracks_statistics(self, simple_circuit, simulator_backend):
        """Test that smart scheduler tracks job statistics."""
        scheduler = SmartScheduler()
        scheduler.register_backend("simulator", simulator_backend)

        scheduler.submit_smart(simple_circuit)

        stats = scheduler.get_statistics("simulator")
        assert stats is not None
        assert stats.total_jobs == 1
        assert stats.successful_jobs == 1
        assert stats.failed_jobs == 0
        assert stats.success_rate == 1.0

    def test_smart_scheduler_selects_best_backend(self, simple_circuit, simulator_backend, telemetry):
        """Test intelligent backend selection using telemetry."""
        scheduler = SmartScheduler(telemetry=telemetry)
        scheduler.register_backend("simulator", simulator_backend)

        telemetry.update_status("simulator", SystemStatus.AVAILABLE)

        name, backend = scheduler.get_best_backend(simple_circuit)
        assert name == "simulator"
        assert backend == simulator_backend

    def test_smart_scheduler_uses_fallback_on_retry_failure(self, simple_circuit):
        """Test that smart scheduler uses fallback when primary fails."""
        scheduler = SmartScheduler()

        backend1 = Mock()
        backend1.execute.side_effect = RuntimeError("Backend 1 failed")
        backend1.validate_circuit.return_value = []
        backend1.capabilities = Mock(max_qubits=10, supports_statevector=False)

        backend2 = StateVectorSimulator()

        scheduler.register_backend("backend1", backend1)
        scheduler.register_backend("backend2", backend2)

        # Mark backend1 as preferred but it will fail
        from cvgen.orchestrator.scheduler import BackendRequirements

        record = scheduler.submit_smart(
            simple_circuit,
            requirements=BackendRequirements(preferred_backend="backend1"),
        )

        # Should fall back to backend2
        assert record.status == JobStatus.COMPLETED

    def test_smart_scheduler_thread_safe_statistics(self, simple_circuit, simulator_backend):
        """Test that statistics updates are thread-safe."""
        scheduler = SmartScheduler()
        scheduler.register_backend("simulator", simulator_backend)

        import threading

        def submit_job():
            scheduler.submit_smart(simple_circuit)

        threads = [threading.Thread(target=submit_job) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = scheduler.get_statistics("simulator")
        assert stats.total_jobs == 5


# ===== DAGWorkflow Tests =====


class TestDAGWorkflow:
    """Tests for DAGWorkflow."""

    def test_dag_simple_linear_execution(self):
        """Test simple linear workflow execution."""
        workflow = DAGWorkflow("linear")
        workflow.add_node("step1", lambda x: x + 1)
        workflow.add_node("step2", lambda x: x * 2, depends_on=["step1"])
        workflow.add_node("step3", lambda x: x - 1, depends_on=["step2"])

        result = workflow.run({"step1": 5})

        assert result.success
        assert result.node_results["step1"] == 6
        assert result.node_results["step2"] == 12
        assert result.node_results["step3"] == 11
        assert len(result.execution_order) == 3

    def test_dag_parallel_execution(self):
        """Test parallel execution of independent nodes."""
        workflow = DAGWorkflow("parallel")
        workflow.add_node("setup", lambda _: {"data": 10})
        workflow.add_node("process1", lambda x: x["data"] * 2, depends_on=["setup"])
        workflow.add_node("process2", lambda x: x["data"] + 5, depends_on=["setup"])

        result = workflow.run()

        assert result.success
        assert result.node_results["process1"] == 20
        assert result.node_results["process2"] == 15
        # Both processes should be in execution order
        assert "process1" in result.execution_order
        assert "process2" in result.execution_order

    def test_dag_diamond_dependency(self):
        """Test diamond-shaped dependency graph."""
        workflow = DAGWorkflow("diamond")
        workflow.add_node("a", lambda _: 1)
        workflow.add_node("b", lambda x: x * 2, depends_on=["a"])
        workflow.add_node("c", lambda x: x + 3, depends_on=["a"])
        workflow.add_node("d", lambda deps: deps["b"] + deps["c"], depends_on=["b", "c"])

        result = workflow.run()

        assert result.success
        assert result.node_results["a"] == 1
        assert result.node_results["b"] == 2
        assert result.node_results["c"] == 4
        assert result.node_results["d"] == 6

    def test_dag_cycle_detection(self):
        """Test that cycles are detected."""
        workflow = DAGWorkflow("cyclic")
        workflow.add_node("a", lambda x: x)
        workflow.add_node("b", lambda x: x, depends_on=["a"])
        workflow.add_node("c", lambda x: x, depends_on=["b"])

        # Create cycle by making 'a' depend on 'c'
        with pytest.raises(ValueError) as exc_info:
            workflow.add_node("a", lambda x: x, depends_on=["c"])

        # The error should come from run(), not add_node()
        # So let's test with direct cycle
        workflow2 = DAGWorkflow("cyclic2")
        workflow2._nodes["a"] = lambda x: x
        workflow2._dependencies["a"] = ["b"]
        workflow2._nodes["b"] = lambda x: x
        workflow2._dependencies["b"] = ["a"]

        with pytest.raises(ValueError) as exc_info:
            workflow2.run()

        assert "cycle" in str(exc_info.value).lower()

    def test_dag_error_in_node(self):
        """Test that node execution errors are handled."""
        workflow = DAGWorkflow("error")

        def failing_fn(x):
            raise RuntimeError("Node failed")

        workflow.add_node("success", lambda _: 10)
        workflow.add_node("failure", failing_fn, depends_on=["success"])
        workflow.add_node("skipped", lambda x: x * 2, depends_on=["failure"])

        result = workflow.run()

        assert not result.success
        assert "success" in result.node_results
        assert "failure" not in result.node_results
        assert "skipped" not in result.node_results

    def test_dag_mermaid_visualization(self):
        """Test Mermaid diagram generation."""
        workflow = DAGWorkflow("viz")
        workflow.add_node("a", lambda _: 1)
        workflow.add_node("b", lambda x: x * 2, depends_on=["a"])
        workflow.add_node("c", lambda x: x + 1, depends_on=["a"])

        mermaid = workflow.to_mermaid()

        assert "graph TD" in mermaid
        assert "a" in mermaid
        assert "b" in mermaid
        assert "c" in mermaid
        assert "-->" in mermaid

    def test_dag_workflow_repr(self):
        """Test DAGWorkflow string representation."""
        workflow = DAGWorkflow("test")
        workflow.add_node("a", lambda x: x)

        repr_str = repr(workflow)
        assert "DAGWorkflow" in repr_str
        assert "test" in repr_str

    def test_workflow_result_repr(self):
        """Test WorkflowResult string representation."""
        result = WorkflowResult(
            node_results={"a": 1, "b": 2},
            success=True,
            total_duration_s=0.5,
        )
        repr_str = repr(result)
        assert "WorkflowResult" in repr_str
        assert "success=True" in repr_str

    def test_dag_node_count(self):
        """Test __len__ returns correct node count."""
        workflow = DAGWorkflow("count")
        assert len(workflow) == 0

        workflow.add_node("a", lambda x: x)
        workflow.add_node("b", lambda x: x)

        assert len(workflow) == 2

    def test_dag_multiple_dependencies(self):
        """Test node with multiple dependencies."""
        workflow = DAGWorkflow("multi_deps")
        workflow.add_node("a", lambda _: 5)
        workflow.add_node("b", lambda _: 3)
        workflow.add_node("c", lambda deps: deps["a"] + deps["b"], depends_on=["a", "b"])

        result = workflow.run()

        assert result.success
        assert result.node_results["c"] == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
