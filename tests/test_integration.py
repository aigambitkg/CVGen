"""End-to-end integration tests."""

import pytest

from cvgen.agents.quantum_agent import QuantumAgent, SearchTask
from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask
from cvgen.agents.tools import build_bell_pair, build_ghz_state, build_superposition_circuit
from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import JobConfig
from cvgen.monitoring.metrics import MetricsCollector
from cvgen.orchestrator.optimizer import CircuitOptimizer
from cvgen.orchestrator.pipeline import Pipeline
from cvgen.orchestrator.scheduler import TaskScheduler


class TestEndToEnd:
    def test_full_workflow_bell_state(self):
        """Complete workflow: build → optimize → schedule → execute → analyze."""
        sim = StateVectorSimulator()
        scheduler = TaskScheduler()
        scheduler.register_backend("sim", sim)
        optimizer = CircuitOptimizer()
        metrics = MetricsCollector()

        # Build circuit
        qc = build_bell_pair()

        # Optimize
        optimized = optimizer.optimize(qc, level=1)

        # Execute via scheduler
        import time
        start = time.time()
        record = scheduler.submit(optimized, JobConfig(shots=1000, seed=42))
        duration = time.time() - start

        # Collect metrics
        metrics.record_execution(optimized, record.result, duration)

        # Verify results
        assert record.result is not None
        counts = record.result.counts
        assert set(counts.keys()).issubset({"00", "11"})
        assert metrics.total_executions == 1

    def test_full_workflow_ghz(self):
        """GHZ state: should produce only |000⟩ and |111⟩."""
        sim = StateVectorSimulator()
        qc = build_ghz_state(3)
        result = sim.execute(qc, JobConfig(shots=5000, seed=42))
        assert set(result.counts.keys()).issubset({"000", "111"})

    def test_pipeline_with_optimizer(self):
        """Pipeline: build → optimize → execute."""
        sim = StateVectorSimulator()
        optimizer = CircuitOptimizer()

        pipeline = Pipeline("optimized_execution")
        pipeline.add_step("build", lambda _: build_superposition_circuit(3))
        pipeline.add_step("optimize", lambda qc: optimizer.optimize(qc, level=1))
        pipeline.add_step("execute", lambda qc: sim.execute(qc, JobConfig(shots=1000, seed=42)))

        result = pipeline.run(None)
        assert result.success
        cr = result.final_output
        assert cr.shots == 1000
        assert len(cr.counts) > 1  # Multiple outcomes from superposition

    def test_quantum_agent_full_run(self):
        """QuantumAgent end-to-end: Grover search."""
        sim = StateVectorSimulator()
        target = 2  # |10⟩

        task = SearchTask(
            num_qubits=2,
            oracle_fn=lambda x: x == target,
            max_solutions=1,
        )
        agent = QuantumAgent(sim, shots=1024)
        result = agent.run(task)

        assert result.success
        assert result.total_steps > 0
        assert len(result.quantum_results) > 0

    def test_hybrid_agent_full_run(self):
        """HybridAgent end-to-end: VQE optimization."""
        sim = StateVectorSimulator()

        # Cost: minimize probability of measuring |1⟩
        task = VariationalTask(
            num_qubits=1,
            cost_observable={"0": 0.0, "1": 1.0},
            ansatz_depth=1,
            max_iterations=30,
        )
        agent = HybridAgent(sim, shots=256)
        result = agent.run(task)

        assert result.success
        assert result.value["optimal_cost"] < 0.5

    def test_origin_pilot_fallback(self):
        """OriginPilotBackend should work in fallback mode."""
        from cvgen.backends.origin_pilot import OriginPilotBackend

        backend = OriginPilotBackend()
        assert "fallback" in backend.name

        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1).measure_all()
        result = backend.execute(qc, JobConfig(shots=100, seed=42))
        assert result.shots == 100
        assert set(result.counts.keys()).issubset({"00", "11"})

    def test_metrics_across_multiple_executions(self):
        """Metrics should accumulate across multiple executions."""
        sim = StateVectorSimulator()
        metrics = MetricsCollector()

        import time
        for i in range(5):
            qc = QuantumCircuit(2)
            qc.h(0).cx(0, 1).measure_all()
            start = time.time()
            result = sim.execute(qc, JobConfig(shots=100, seed=i))
            metrics.record_execution(qc, result, time.time() - start)

        summary = metrics.summary()
        assert summary["total_executions"] == 5
        assert summary["total_shots"] == 500
        assert summary["avg_qubits"] == 2.0
