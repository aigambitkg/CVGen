"""Quantum-enhanced AI agent for optimization and search problems."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from cvgen.agents.base import (
    Action,
    ActionType,
    AgentState,
    BaseAgent,
    Observation,
)
from cvgen.agents.tools import (
    analyze_result,
    build_grover_diffusion,
    build_grover_oracle,
    optimal_grover_iterations,
)
from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import JobConfig

logger = logging.getLogger(__name__)


@dataclass
class SearchTask:
    """A search/optimization task for the QuantumAgent.

    Args:
        num_qubits: Search space size (2^num_qubits states).
        oracle_fn: Function that returns True for solution states.
                   Takes an integer (state index) and returns bool.
        max_solutions: Expected number of solutions (for iteration count).
    """

    num_qubits: int
    oracle_fn: Callable[[int], bool]
    max_solutions: int = 1


class QuantumAgent(BaseAgent):
    """An AI agent that uses quantum algorithms for search and optimization.

    This agent can:
    - Use Grover's algorithm for unstructured search
    - Generate quantum random numbers for exploration
    - Analyze measurement statistics for decision-making

    Args:
        backend: Quantum backend for circuit execution.
        shots: Number of measurement shots per circuit.
        name: Optional agent name.
    """

    def __init__(
        self,
        backend: QuantumBackend,
        shots: int = 1024,
        name: str | None = None,
    ) -> None:
        super().__init__(backend, name=name or "QuantumAgent")
        self.shots = shots
        self._solutions_found: list[int] = []

    def perceive(self, observation: Observation) -> AgentState:
        self.state.observations.append(observation)

        # If this is the first observation, extract the task
        if self.state.step == 0 and isinstance(observation.data, SearchTask):
            self.state.custom["task"] = observation.data
            self.state.custom["phase"] = "search"
            self.state.custom["iteration"] = 0

        # If we received a circuit result, analyze it
        if hasattr(observation.data, "counts"):
            analysis = analyze_result(observation.data)
            self.state.custom["last_analysis"] = analysis
            logger.debug(f"[{self.name}] Analysis: {analysis['most_likely']}")

        return self.state

    def decide(self, state: AgentState) -> Action:
        task = state.custom.get("task")
        if task is None:
            return Action(action_type=ActionType.TERMINATE, params={"result": None})

        phase = state.custom.get("phase", "search")

        if phase == "search":
            return self._decide_search(state, task)
        elif phase == "verify":
            return self._decide_verify(state, task)
        else:
            return Action(
                action_type=ActionType.TERMINATE,
                params={"result": self._solutions_found},
            )

    def _decide_search(self, state: AgentState, task: SearchTask) -> Action:
        """Decide on a Grover search action."""
        iteration = state.custom.get("iteration", 0)
        num_iterations = optimal_grover_iterations(
            task.num_qubits, task.max_solutions
        )

        if iteration >= num_iterations:
            # Analyze collected results and switch to verify phase
            state.custom["phase"] = "verify"
            return self._decide_verify(state, task)

        # Build Grover circuit
        circuit = self._build_grover_circuit(task, iteration + 1)
        state.custom["iteration"] = iteration + 1

        return Action(
            action_type=ActionType.QUANTUM,
            circuit=circuit,
            config=JobConfig(shots=self.shots),
        )

    def _decide_verify(self, state: AgentState, task: SearchTask) -> Action:
        """Verify candidate solutions classically."""
        # Collect candidates from quantum results
        candidates: set[int] = set()
        for qr in self._quantum_results:
            for bitstring, count in qr.counts.items():
                if count > self.shots * 0.05:  # At least 5% of shots
                    candidates.add(int(bitstring, 2))

        # Verify each candidate with the oracle
        self._solutions_found = [c for c in candidates if task.oracle_fn(c)]

        logger.info(
            f"[{self.name}] Found {len(self._solutions_found)} solutions: "
            f"{self._solutions_found}"
        )

        state.custom["phase"] = "done"
        return Action(
            action_type=ActionType.TERMINATE,
            params={"result": self._solutions_found},
        )

    def _build_grover_circuit(
        self, task: SearchTask, num_iterations: int
    ) -> QuantumCircuit:
        """Build a complete Grover search circuit."""
        n = task.num_qubits
        qc = QuantumCircuit(n)
        qc.name = f"grover_iter{num_iterations}"

        # Initial superposition
        for i in range(n):
            qc.h(i)

        # Find target states for oracle
        targets = []
        for state_idx in range(2**n):
            if task.oracle_fn(state_idx):
                targets.append(state_idx)

        # Apply Grover iterations
        for _ in range(num_iterations):
            # Oracle: mark solution states
            for target in targets:
                oracle = build_grover_oracle(n, target)
                qc.compose(oracle)

            # Diffusion operator
            diffusion = build_grover_diffusion(n)
            qc.compose(diffusion)

        qc.measure_all()
        return qc

    def run_search(self, task: SearchTask) -> list[int]:
        """Convenience method to run a search task and return solutions."""
        result = self.run(task)
        return result.value if result.value else []
