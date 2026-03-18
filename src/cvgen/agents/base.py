"""Base agent interface for quantum-enhanced AI agents."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from cvgen.backends.base import QuantumBackend
from cvgen.core.circuit import QuantumCircuit
from cvgen.core.types import CircuitResult, JobConfig

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions an agent can take."""

    QUANTUM = auto()      # Execute a quantum circuit
    CLASSICAL = auto()    # Perform classical computation
    HYBRID = auto()       # Quantum-classical hybrid loop
    OBSERVE = auto()      # Gather more information
    TERMINATE = auto()    # Stop execution


@dataclass
class Observation:
    """What the agent perceives from its environment."""

    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    """Internal state of an agent after processing observations."""

    observations: list[Observation] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    step: int = 0
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    """An action decided by the agent."""

    action_type: ActionType
    circuit: QuantumCircuit | None = None
    config: JobConfig | None = None
    classical_fn: Any | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Final result returned by an agent."""

    success: bool
    value: Any
    history: list[dict[str, Any]] = field(default_factory=list)
    quantum_results: list[CircuitResult] = field(default_factory=list)
    total_steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Abstract base class for AI agents with quantum computing capabilities.

    Agents follow a perceive → decide → act loop:
    1. perceive(): Process observations from the environment
    2. decide(): Choose an action based on current state
    3. act(): Execute the action and collect results

    Args:
        backend: Quantum backend for circuit execution.
        max_steps: Maximum number of perceive-decide-act cycles.
        name: Optional agent name for logging.
    """

    def __init__(
        self,
        backend: QuantumBackend,
        max_steps: int = 100,
        name: str | None = None,
    ) -> None:
        self.backend = backend
        self.max_steps = max_steps
        self.name = name or self.__class__.__name__
        self.state = AgentState()
        self._quantum_results: list[CircuitResult] = []

    @abstractmethod
    def perceive(self, observation: Observation) -> AgentState:
        """Process an observation and update internal state."""

    @abstractmethod
    def decide(self, state: AgentState) -> Action:
        """Decide what action to take based on current state."""

    def act(self, action: Action) -> Any:
        """Execute an action. Override for custom behavior."""
        if action.action_type == ActionType.QUANTUM:
            if action.circuit is None:
                raise ValueError("Quantum action requires a circuit")
            result = self.backend.execute(action.circuit, action.config)
            self._quantum_results.append(result)
            return result
        elif action.action_type == ActionType.CLASSICAL:
            if action.classical_fn is None:
                raise ValueError("Classical action requires a function")
            return action.classical_fn(**action.params)
        elif action.action_type == ActionType.TERMINATE:
            return None
        return None

    def run(self, task: Any) -> AgentResult:
        """Execute the full agent loop on a task.

        Args:
            task: The task/problem for the agent to solve.

        Returns:
            AgentResult with the final outcome and execution history.
        """
        logger.info(f"[{self.name}] Starting task")
        self.state = AgentState()
        self._quantum_results = []

        # Initial observation from the task
        observation = Observation(data=task)
        result_value = None

        for step in range(self.max_steps):
            self.state.step = step
            logger.debug(f"[{self.name}] Step {step}")

            # Perceive
            self.state = self.perceive(observation)

            # Decide
            action = self.decide(self.state)

            # Record in history
            self.state.history.append({
                "step": step,
                "action_type": action.action_type.name,
                "has_circuit": action.circuit is not None,
            })

            # Check for termination
            if action.action_type == ActionType.TERMINATE:
                result_value = action.params.get("result")
                logger.info(f"[{self.name}] Terminated at step {step}")
                break

            # Act
            act_result = self.act(action)
            observation = Observation(
                data=act_result,
                metadata={"step": step, "action_type": action.action_type.name},
            )
            result_value = act_result
        else:
            logger.warning(f"[{self.name}] Reached max steps ({self.max_steps})")

        return AgentResult(
            success=True,
            value=result_value,
            history=self.state.history,
            quantum_results=self._quantum_results,
            total_steps=self.state.step + 1,
            metadata={"agent_name": self.name},
        )

    def execute_circuit(
        self, circuit: QuantumCircuit, config: JobConfig | None = None
    ) -> CircuitResult:
        """Convenience method to directly execute a quantum circuit."""
        result = self.backend.execute(circuit, config)
        self._quantum_results.append(result)
        return result
