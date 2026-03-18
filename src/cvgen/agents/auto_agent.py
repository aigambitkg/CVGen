"""Auto Agent — intelligent meta-agent that selects the best quantum strategy.

Analyzes the problem, estimates complexity, and automatically chooses
the optimal algorithm (Grover, VQE, QAOA, QML) and backend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from cvgen.agents.base import AgentResult
from cvgen.backends.base import QuantumBackend
from cvgen.backends.simulator import StateVectorSimulator

logger = logging.getLogger(__name__)


class ProblemType(Enum):
    """Detected problem types."""

    SEARCH = auto()            # Unstructured search → Grover
    OPTIMIZATION = auto()      # Continuous optimization → VQE
    COMBINATORIAL = auto()     # Combinatorial optimization → QAOA
    CLASSIFICATION = auto()    # Binary classification → QML
    UNKNOWN = auto()


@dataclass
class AutoTask:
    """A task for the Auto Agent to analyze and route.

    Provide the problem description and data. The Auto Agent will
    determine the best quantum algorithm and execute it.

    Args:
        problem_type: Hint for problem type. Auto-detected if None.
        data: Problem-specific data (varies by problem type).
        num_qubits: Desired qubit count. Auto-sized if None.
        prefer_speed: If True, prefer faster execution over accuracy.
    """

    problem_type: str | None = None
    data: dict[str, Any] | None = None
    num_qubits: int | None = None
    prefer_speed: bool = False


class AutoAgent:
    """Meta-agent that automatically selects the best quantum strategy.

    Analyzes the problem characteristics and routes to the most
    appropriate specialized agent (Grover, VQE, QAOA, QML).

    This is the recommended entry point for users who want quantum
    acceleration without choosing algorithms manually.

    Args:
        backend: Quantum backend. If None, uses built-in simulator.
        shots: Default shot count for quantum circuits.
    """

    def __init__(
        self,
        backend: QuantumBackend | None = None,
        shots: int = 1024,
    ) -> None:
        self.backend = backend or StateVectorSimulator()
        self.shots = shots

    def run(self, task: AutoTask) -> AgentResult:
        """Analyze the task and run with the best agent."""
        problem_type = self._detect_problem_type(task)
        logger.info(f"[AutoAgent] Detected problem type: {problem_type.name}")

        if problem_type == ProblemType.SEARCH:
            return self._run_search(task)
        elif problem_type == ProblemType.OPTIMIZATION:
            return self._run_vqe(task)
        elif problem_type == ProblemType.COMBINATORIAL:
            return self._run_qaoa(task)
        elif problem_type == ProblemType.CLASSIFICATION:
            return self._run_qml(task)
        else:
            return AgentResult(
                success=False,
                value={"error": "Could not determine problem type. Provide a problem_type hint."},
                metadata={"agent_name": "AutoAgent"},
            )

    def _detect_problem_type(self, task: AutoTask) -> ProblemType:
        """Detect the problem type from task data and hints."""
        # Explicit hint
        if task.problem_type:
            type_map = {
                "search": ProblemType.SEARCH,
                "grover": ProblemType.SEARCH,
                "optimization": ProblemType.OPTIMIZATION,
                "vqe": ProblemType.OPTIMIZATION,
                "combinatorial": ProblemType.COMBINATORIAL,
                "qaoa": ProblemType.COMBINATORIAL,
                "maxcut": ProblemType.COMBINATORIAL,
                "classification": ProblemType.CLASSIFICATION,
                "qml": ProblemType.CLASSIFICATION,
            }
            detected = type_map.get(task.problem_type.lower())
            if detected:
                return detected

        # Auto-detect from data
        data = task.data or {}

        if "target_states" in data or "oracle_fn" in data:
            return ProblemType.SEARCH
        if "edges" in data or "graph" in data:
            return ProblemType.COMBINATORIAL
        if "train_data" in data or "features" in data:
            return ProblemType.CLASSIFICATION
        if "cost_observable" in data:
            return ProblemType.OPTIMIZATION

        return ProblemType.UNKNOWN

    def _run_search(self, task: AutoTask) -> AgentResult:
        """Route to Grover search agent."""
        from cvgen.agents.quantum_agent import QuantumAgent, SearchTask

        data = task.data or {}
        target_states = data.get("target_states", [])
        num_qubits = task.num_qubits or max(2, len(target_states).bit_length() + 1)

        target_set = set(target_states)
        search_task = SearchTask(
            num_qubits=num_qubits,
            oracle_fn=lambda x, _ts=target_set: x in _ts,
            max_solutions=len(target_states) or 1,
        )

        agent = QuantumAgent(self.backend, shots=self.shots)
        solutions = agent.run_search(search_task)

        return AgentResult(
            success=len(solutions) > 0,
            value={"solutions": solutions, "algorithm": "grover"},
            quantum_results=agent._quantum_results,
            metadata={"agent_name": "AutoAgent→QuantumAgent"},
        )

    def _run_vqe(self, task: AutoTask) -> AgentResult:
        """Route to VQE optimization agent."""
        from cvgen.agents.hybrid_agent import HybridAgent, VariationalTask

        data = task.data or {}
        vqe_task = VariationalTask(
            num_qubits=task.num_qubits or data.get("num_qubits", 2),
            cost_observable=data.get("cost_observable", {}),
            ansatz_depth=data.get("ansatz_depth", 2),
            max_iterations=data.get("max_iterations", 50),
        )

        agent = HybridAgent(self.backend, shots=self.shots)
        result = agent.run(vqe_task)
        result.metadata["agent_name"] = "AutoAgent→HybridAgent"
        result.metadata["algorithm"] = "vqe"
        return result

    def _run_qaoa(self, task: AutoTask) -> AgentResult:
        """Route to QAOA combinatorial optimization agent."""
        from cvgen.agents.qaoa_agent import QAOAAgent, QAOATask

        data = task.data or {}
        edges = data.get("edges", [])
        # Convert edge format if needed
        formatted_edges = []
        for e in edges:
            if len(e) == 2:
                formatted_edges.append((e[0], e[1], 1.0))
            else:
                formatted_edges.append(tuple(e))

        num_nodes = 0
        for e in formatted_edges:
            num_nodes = max(num_nodes, e[0] + 1, e[1] + 1)

        qaoa_task = QAOATask(
            num_qubits=task.num_qubits or num_nodes,
            edges=formatted_edges,
            p=data.get("p", 2),
            max_iterations=data.get("max_iterations", 50),
        )

        agent = QAOAAgent(self.backend, shots=self.shots)
        result = agent.run(qaoa_task)
        result.metadata["agent_name"] = "AutoAgent→QAOAAgent"
        result.metadata["algorithm"] = "qaoa"
        return result

    def _run_qml(self, task: AutoTask) -> AgentResult:
        """Route to QML classification agent."""
        from cvgen.agents.qml_agent import ClassificationTask, QMLAgent

        data = task.data or {}
        qml_task = ClassificationTask(
            train_data=data.get("train_data", []),
            train_labels=data.get("train_labels", []),
            test_data=data.get("test_data"),
            num_qubits=task.num_qubits,
            ansatz_depth=data.get("ansatz_depth", 2),
            max_iterations=data.get("max_iterations", 50),
        )

        agent = QMLAgent(self.backend, shots=self.shots)
        result = agent.run(qml_task)
        result.metadata["agent_name"] = "AutoAgent→QMLAgent"
        result.metadata["algorithm"] = "qml"
        return result

    @staticmethod
    def complexity_estimate(task: AutoTask) -> dict:
        """Estimate the computational complexity of a task.

        Returns estimated circuit depth, qubit count, and recommended
        backend (simulator vs cloud hardware).
        """
        data = task.data or {}
        n = task.num_qubits or 4

        estimates = {
            "estimated_qubits": n,
            "estimated_depth": 0,
            "recommended_backend": "simulator",
            "estimated_shots": 1024,
        }

        if "target_states" in data:
            # Grover: depth ~ O(sqrt(N))
            import math
            estimates["estimated_depth"] = int(math.sqrt(2 ** n)) * 3 * n
        elif "edges" in data:
            # QAOA: depth ~ O(p * |E|)
            p = data.get("p", 2)
            estimates["estimated_depth"] = p * len(data["edges"]) * 4 + n
        elif "train_data" in data:
            # QML: depth ~ O(depth * n)
            depth = data.get("ansatz_depth", 2)
            estimates["estimated_depth"] = depth * 3 * n + n
        elif "cost_observable" in data:
            # VQE: depth ~ O(depth * n)
            depth = data.get("ansatz_depth", 2)
            estimates["estimated_depth"] = depth * 3 * n

        # Recommend cloud for large circuits
        if n > 10 or estimates["estimated_depth"] > 100:
            estimates["recommended_backend"] = "cloud"
            estimates["estimated_shots"] = 4096

        return estimates
