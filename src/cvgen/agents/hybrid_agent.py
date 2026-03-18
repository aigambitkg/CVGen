"""Hybrid quantum-classical agent for variational algorithms."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import minimize

from cvgen.agents.base import (
    Action,
    ActionType,
    AgentResult,
    AgentState,
    BaseAgent,
    Observation,
)
from cvgen.agents.tools import build_variational_ansatz
from cvgen.backends.base import QuantumBackend
from cvgen.core.types import JobConfig

logger = logging.getLogger(__name__)


@dataclass
class VariationalTask:
    """A variational quantum optimization task.

    Args:
        num_qubits: Number of qubits in the ansatz.
        cost_observable: Observable to minimize, as {bitstring: eigenvalue}.
        ansatz_depth: Number of variational layers.
        initial_params: Starting parameters. Random if None.
        optimizer_method: Classical optimizer (scipy method name).
        max_iterations: Maximum optimization iterations.
    """

    num_qubits: int
    cost_observable: dict[str, float]
    ansatz_depth: int = 2
    initial_params: list[float] | None = None
    optimizer_method: str = "COBYLA"
    max_iterations: int = 100


@dataclass
class OptimizationHistory:
    """Tracks the optimization progress."""

    costs: list[float] = field(default_factory=list)
    params: list[list[float]] = field(default_factory=list)
    num_circuit_evals: int = 0


class HybridAgent(BaseAgent):
    """Agent for hybrid quantum-classical variational algorithms.

    Implements the variational quantum eigensolver (VQE) pattern:
    1. Prepare a parameterized quantum state (ansatz)
    2. Measure the cost function on the quantum device
    3. Use a classical optimizer to update parameters
    4. Repeat until convergence

    Args:
        backend: Quantum backend for circuit execution.
        shots: Number of measurement shots per evaluation.
        name: Optional agent name.
    """

    def __init__(
        self,
        backend: QuantumBackend,
        shots: int = 1024,
        name: str | None = None,
    ) -> None:
        super().__init__(backend, name=name or "HybridAgent")
        self.shots = shots
        self.opt_history = OptimizationHistory()

    def perceive(self, observation: Observation) -> AgentState:
        self.state.observations.append(observation)
        if self.state.step == 0 and isinstance(observation.data, VariationalTask):
            self.state.custom["task"] = observation.data
        return self.state

    def decide(self, state: AgentState) -> Action:
        task = state.custom.get("task")
        if task is None:
            return Action(action_type=ActionType.TERMINATE, params={"result": None})

        return Action(
            action_type=ActionType.HYBRID,
            params={"task": task},
        )

    def act(self, action: Action) -> Any:
        if action.action_type == ActionType.HYBRID:
            task = action.params["task"]
            return self._run_vqe(task)
        return super().act(action)

    def run(self, task: Any) -> AgentResult:
        """Run the variational optimization."""
        if not isinstance(task, VariationalTask):
            return super().run(task)

        logger.info(f"[{self.name}] Starting VQE optimization")
        self.opt_history = OptimizationHistory()
        self._quantum_results = []

        result = self._run_vqe(task)

        return AgentResult(
            success=True,
            value=result,
            history=[
                {
                    "costs": self.opt_history.costs,
                    "num_evaluations": self.opt_history.num_circuit_evals,
                }
            ],
            quantum_results=self._quantum_results,
            total_steps=self.opt_history.num_circuit_evals,
            metadata={
                "agent_name": self.name,
                "final_cost": self.opt_history.costs[-1] if self.opt_history.costs else None,
                "optimal_params": result["optimal_params"] if result else None,
            },
        )

    def _run_vqe(self, task: VariationalTask) -> dict:
        """Execute the VQE optimization loop."""
        num_params = task.num_qubits * 2 * task.ansatz_depth

        # Initialize parameters
        if task.initial_params is not None:
            x0 = np.array(task.initial_params)
        else:
            x0 = np.random.uniform(-np.pi, np.pi, num_params)

        def cost_function(params: np.ndarray) -> float:
            return self._evaluate_cost(
                params.tolist(), task.num_qubits, task.ansatz_depth, task.cost_observable
            )

        # Run classical optimization
        opt_result = minimize(
            cost_function,
            x0,
            method=task.optimizer_method,
            options={"maxiter": task.max_iterations},
        )

        return {
            "optimal_cost": float(opt_result.fun),
            "optimal_params": opt_result.x.tolist(),
            "converged": opt_result.success,
            "num_evaluations": self.opt_history.num_circuit_evals,
            "message": str(opt_result.message),
        }

    def _evaluate_cost(
        self,
        params: list[float],
        num_qubits: int,
        depth: int,
        observable: dict[str, float],
    ) -> float:
        """Evaluate the cost function for given parameters."""
        # Build and execute the ansatz circuit
        circuit = build_variational_ansatz(num_qubits, depth, params)
        circuit.measure_all()

        config = JobConfig(shots=self.shots)
        result = self.backend.execute(circuit, config)
        self._quantum_results.append(result)

        # Calculate expectation value
        cost = result.expectation_value(observable)

        # Record history
        self.opt_history.costs.append(cost)
        self.opt_history.params.append(params)
        self.opt_history.num_circuit_evals += 1

        logger.debug(f"[{self.name}] Eval {self.opt_history.num_circuit_evals}: cost={cost:.6f}")
        return cost
