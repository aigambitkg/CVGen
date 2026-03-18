"""QAOA Agent for combinatorial optimization problems.

Implements the Quantum Approximate Optimization Algorithm (QAOA)
for problems like MaxCut, graph coloring, and the Traveling Salesman Problem.
"""

from __future__ import annotations

import logging
import math
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
from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult, JobConfig

logger = logging.getLogger(__name__)


@dataclass
class QAOATask:
    """A combinatorial optimization task for QAOA.

    Args:
        num_qubits: Number of variables (one qubit per variable).
        edges: List of (i, j, weight) tuples representing the problem graph.
                For MaxCut: edges of the graph with optional weights.
        p: Number of QAOA layers (higher = better approximation).
        max_iterations: Maximum classical optimization iterations.
        optimizer_method: SciPy optimizer method.
    """

    num_qubits: int
    edges: list[tuple[int, int, float]]
    p: int = 2
    max_iterations: int = 100
    optimizer_method: str = "COBYLA"


@dataclass
class QAOAHistory:
    """Tracks QAOA optimization progress."""

    costs: list[float] = field(default_factory=list)
    params: list[list[float]] = field(default_factory=list)
    num_evals: int = 0


class QAOAAgent(BaseAgent):
    """Agent implementing the Quantum Approximate Optimization Algorithm.

    QAOA solves combinatorial optimization by alternating between:
    1. Problem unitary: encodes the cost function
    2. Mixer unitary: explores solution space
    Classical optimizer tunes the alternation angles.

    Ideal for: MaxCut, graph partitioning, scheduling, routing problems.

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
        super().__init__(backend, name=name or "QAOAAgent")
        self.shots = shots
        self.history = QAOAHistory()

    def perceive(self, observation: Observation) -> AgentState:
        self.state.observations.append(observation)
        if self.state.step == 0 and isinstance(observation.data, QAOATask):
            self.state.custom["task"] = observation.data
        return self.state

    def decide(self, state: AgentState) -> Action:
        task = state.custom.get("task")
        if task is None:
            return Action(action_type=ActionType.TERMINATE, params={"result": None})
        return Action(action_type=ActionType.HYBRID, params={"task": task})

    def act(self, action: Action) -> Any:
        if action.action_type == ActionType.HYBRID:
            return self._run_qaoa(action.params["task"])
        return super().act(action)

    def run(self, task: Any) -> AgentResult:
        """Run QAOA optimization."""
        if not isinstance(task, QAOATask):
            return super().run(task)

        logger.info(f"[{self.name}] Starting QAOA with p={task.p}")
        self.history = QAOAHistory()
        self._quantum_results = []

        result = self._run_qaoa(task)

        return AgentResult(
            success=True,
            value=result,
            history=[{
                "costs": self.history.costs,
                "num_evaluations": self.history.num_evals,
            }],
            quantum_results=self._quantum_results,
            total_steps=self.history.num_evals,
            metadata={"agent_name": self.name, "p": task.p},
        )

    def _run_qaoa(self, task: QAOATask) -> dict:
        """Execute the QAOA optimization loop."""
        num_params = 2 * task.p  # gamma and beta for each layer
        x0 = np.random.uniform(0, 2 * math.pi, num_params)

        def cost_fn(params: np.ndarray) -> float:
            return self._evaluate(params.tolist(), task)

        opt = minimize(
            cost_fn, x0,
            method=task.optimizer_method,
            options={"maxiter": task.max_iterations},
        )

        # Get best solution from final circuit
        best_circuit = self._build_qaoa_circuit(opt.x.tolist(), task)
        best_circuit.measure_all()
        final_result = self.backend.execute(best_circuit, JobConfig(shots=self.shots * 4))

        best_bitstring = final_result.most_likely()
        best_cost = self._compute_cost(best_bitstring, task)

        return {
            "optimal_cost": best_cost,
            "optimal_bitstring": best_bitstring,
            "optimal_params": opt.x.tolist(),
            "converged": opt.success,
            "num_evaluations": self.history.num_evals,
        }

    def _evaluate(self, params: list[float], task: QAOATask) -> float:
        """Evaluate QAOA cost for given parameters."""
        circuit = self._build_qaoa_circuit(params, task)
        circuit.measure_all()

        result = self.backend.execute(circuit, JobConfig(shots=self.shots))
        self._quantum_results.append(result)

        # Compute expected cost
        total_cost = 0.0
        for bitstring, count in result.counts.items():
            cost = self._compute_cost(bitstring, task)
            total_cost += cost * count / result.shots

        self.history.costs.append(total_cost)
        self.history.params.append(params)
        self.history.num_evals += 1

        logger.debug(f"[{self.name}] Eval {self.history.num_evals}: cost={total_cost:.4f}")
        return -total_cost  # Minimize negative = maximize cost

    def _build_qaoa_circuit(self, params: list[float], task: QAOATask) -> QuantumCircuit:
        """Build a QAOA circuit with given parameters."""
        n = task.num_qubits
        p = task.p
        qc = QuantumCircuit(n)
        qc.name = f"qaoa_p{p}"

        # Initial superposition
        for i in range(n):
            qc.h(i)

        # Alternating layers
        for layer in range(p):
            gamma = params[2 * layer]
            beta = params[2 * layer + 1]

            # Problem unitary: exp(-i * gamma * C)
            for i, j, w in task.edges:
                # ZZ interaction: RZZ(gamma * w) decomposed
                qc.cx(i, j)
                qc.rz(j, 2 * gamma * w)
                qc.cx(i, j)

            # Mixer unitary: exp(-i * beta * B)
            for i in range(n):
                qc.rx(i, 2 * beta)

        return qc

    def _compute_cost(self, bitstring: str, task: QAOATask) -> float:
        """Compute the MaxCut cost for a bitstring."""
        cost = 0.0
        for i, j, w in task.edges:
            if i < len(bitstring) and j < len(bitstring):
                if bitstring[i] != bitstring[j]:
                    cost += w
        return cost
