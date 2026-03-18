"""Tests for orchestrator components."""

import pytest

from cvgen.backends.simulator import StateVectorSimulator
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import GateType, JobConfig, JobStatus
from cvgen.orchestrator.optimizer import CircuitOptimizer
from cvgen.orchestrator.pipeline import Pipeline
from cvgen.orchestrator.scheduler import BackendRequirements, TaskScheduler


class TestTaskScheduler:
    def test_register_and_submit(self):
        scheduler = TaskScheduler()
        sim = StateVectorSimulator()
        scheduler.register_backend("sim", sim)

        qc = QuantumCircuit(2)
        qc.h(0).cx(0, 1).measure_all()

        record = scheduler.submit(qc)
        assert record.status == JobStatus.COMPLETED
        assert record.result is not None
        assert record.backend_name == "sim"

    def test_no_backend_raises(self):
        scheduler = TaskScheduler()
        qc = QuantumCircuit(1)
        qc.h(0).measure_all()
        with pytest.raises(RuntimeError, match="No backends"):
            scheduler.submit(qc)

    def test_select_preferred_backend(self):
        scheduler = TaskScheduler()
        sim1 = StateVectorSimulator(max_qubits=5)
        sim2 = StateVectorSimulator(max_qubits=10)
        scheduler.register_backend("small", sim1)
        scheduler.register_backend("large", sim2)

        name, _ = scheduler.select_backend(
            BackendRequirements(preferred_backend="small")
        )
        assert name == "small"

    def test_select_by_qubit_requirement(self):
        scheduler = TaskScheduler()
        sim1 = StateVectorSimulator(max_qubits=3)
        sim2 = StateVectorSimulator(max_qubits=10)
        scheduler.register_backend("small", sim1)
        scheduler.register_backend("large", sim2)

        name, _ = scheduler.select_backend(
            BackendRequirements(min_qubits=5)
        )
        assert name == "large"

    def test_job_history(self):
        scheduler = TaskScheduler()
        scheduler.register_backend("sim", StateVectorSimulator())

        qc = QuantumCircuit(1)
        qc.h(0).measure_all()
        scheduler.submit(qc)
        scheduler.submit(qc)

        assert len(scheduler.job_history) == 2

    def test_remove_backend(self):
        scheduler = TaskScheduler()
        scheduler.register_backend("sim", StateVectorSimulator())
        scheduler.remove_backend("sim")
        assert len(scheduler.backends) == 0


class TestCircuitOptimizer:
    def test_level_0_passthrough(self):
        opt = CircuitOptimizer()
        qc = QuantumCircuit(1)
        qc.h(0).h(0)
        result = opt.optimize(qc, level=0)
        assert result.gate_count == 2

    def test_level_1_cancel_xx(self):
        opt = CircuitOptimizer()
        qc = QuantumCircuit(1)
        qc.x(0).x(0)
        result = opt.optimize(qc, level=1)
        assert result.gate_count == 0

    def test_level_1_cancel_hh(self):
        opt = CircuitOptimizer()
        qc = QuantumCircuit(1)
        qc.h(0).h(0)
        result = opt.optimize(qc, level=1)
        assert result.gate_count == 0

    def test_level_1_no_cancel_different_gates(self):
        opt = CircuitOptimizer()
        qc = QuantumCircuit(1)
        qc.h(0).x(0)
        result = opt.optimize(qc, level=1)
        assert result.gate_count == 2

    def test_level_1_cancel_swap(self):
        opt = CircuitOptimizer()
        qc = QuantumCircuit(2)
        qc.swap(0, 1).swap(0, 1)
        result = opt.optimize(qc, level=1)
        assert result.gate_count == 0

    def test_level_2_merge_rotations(self):
        import math
        opt = CircuitOptimizer()
        qc = QuantumCircuit(1)
        qc.rx(0, math.pi / 4).rx(0, math.pi / 4)
        result = opt.optimize(qc, level=2)
        assert result.gate_count == 1
        assert abs(result.operations[0].params[0] - math.pi / 2) < 1e-10

    def test_level_2_cancel_full_rotation(self):
        import math
        opt = CircuitOptimizer()
        qc = QuantumCircuit(1)
        qc.ry(0, math.pi).ry(0, math.pi)
        result = opt.optimize(qc, level=2)
        # 2π rotation should cancel
        assert result.gate_count == 0

    def test_preserves_circuit_metadata(self):
        opt = CircuitOptimizer()
        qc = QuantumCircuit(2)
        qc.name = "test_circuit"
        qc.h(0)
        result = opt.optimize(qc, level=1)
        assert result.name == "test_circuit"
        assert result.num_qubits == 2


class TestPipeline:
    def test_basic_pipeline(self):
        pipeline = Pipeline("test")
        pipeline.add_step("double", lambda x: x * 2)
        pipeline.add_step("add_one", lambda x: x + 1)
        result = pipeline.run(5)
        assert result.final_output == 11
        assert result.success
        assert len(result.steps) == 2

    def test_pipeline_with_circuit(self):
        sim = StateVectorSimulator()

        def build(n_qubits):
            qc = QuantumCircuit(n_qubits)
            qc.h(0).cx(0, 1) if n_qubits >= 2 else qc.h(0)
            qc.measure_all()
            return qc

        pipeline = Pipeline("quantum_workflow")
        pipeline.add_step("build", build)
        pipeline.add_step("execute", lambda qc: sim.execute(qc, JobConfig(shots=100, seed=42)))
        pipeline.add_step("analyze", lambda r: r.most_likely())

        result = pipeline.run(2)
        assert result.success
        assert result.final_output in ("00", "11")

    def test_pipeline_error_handling(self):
        pipeline = Pipeline("failing")
        pipeline.add_step("good", lambda x: x + 1)
        pipeline.add_step("bad", lambda x: 1 / 0)
        pipeline.add_step("never", lambda x: x)
        result = pipeline.run(1)
        assert not result.success
        assert len(result.steps) == 2  # stopped at bad
        assert result.steps[1].error is not None

    def test_pipeline_chaining(self):
        p = Pipeline("chain")
        result = p.add_step("a", lambda x: x).add_step("b", lambda x: x)
        assert result is p

    def test_pipeline_repr(self):
        p = Pipeline("test")
        p.add_step("a", lambda x: x)
        assert "test" in repr(p)
        assert "a" in repr(p)
