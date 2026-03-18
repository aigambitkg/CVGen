"""Quantum Machine Learning Agent.

Implements quantum-enhanced classification and kernel methods using
parameterized quantum circuits (PQC) as feature maps and classifiers.
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
from cvgen.core.types import JobConfig

logger = logging.getLogger(__name__)


@dataclass
class ClassificationTask:
    """A quantum classification task.

    Args:
        train_data: Training features, shape (n_samples, n_features).
        train_labels: Training labels (0 or 1), shape (n_samples,).
        test_data: Test features for prediction. Optional.
        num_qubits: Number of qubits (must be >= n_features).
        ansatz_depth: Number of variational layers.
        max_iterations: Maximum optimization iterations.
    """

    train_data: list[list[float]]
    train_labels: list[int]
    test_data: list[list[float]] | None = None
    num_qubits: int | None = None
    ansatz_depth: int = 2
    max_iterations: int = 50


@dataclass
class QMLHistory:
    """Tracks QML training progress."""

    losses: list[float] = field(default_factory=list)
    accuracies: list[float] = field(default_factory=list)
    num_evals: int = 0


class QMLAgent(BaseAgent):
    """Agent for quantum machine learning classification.

    Uses a variational quantum classifier:
    1. Data encoding: maps classical features to quantum state
    2. Variational circuit: parameterized quantum layers
    3. Measurement: classifies based on measurement outcome

    The quantum kernel provides implicit high-dimensional feature mapping
    that can capture complex decision boundaries.

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
        super().__init__(backend, name=name or "QMLAgent")
        self.shots = shots
        self.history = QMLHistory()
        self._optimal_params: list[float] | None = None

    def perceive(self, observation: Observation) -> AgentState:
        self.state.observations.append(observation)
        if self.state.step == 0 and isinstance(observation.data, ClassificationTask):
            self.state.custom["task"] = observation.data
        return self.state

    def decide(self, state: AgentState) -> Action:
        task = state.custom.get("task")
        if task is None:
            return Action(action_type=ActionType.TERMINATE, params={"result": None})
        return Action(action_type=ActionType.HYBRID, params={"task": task})

    def act(self, action: Action) -> Any:
        if action.action_type == ActionType.HYBRID:
            return self._train_and_predict(action.params["task"])
        return super().act(action)

    def run(self, task: Any) -> AgentResult:
        """Run quantum classification."""
        if not isinstance(task, ClassificationTask):
            return super().run(task)

        logger.info(f"[{self.name}] Starting quantum classification")
        self.history = QMLHistory()
        self._quantum_results = []

        result = self._train_and_predict(task)

        return AgentResult(
            success=True,
            value=result,
            history=[
                {
                    "losses": self.history.losses,
                    "accuracies": self.history.accuracies,
                }
            ],
            quantum_results=self._quantum_results,
            total_steps=self.history.num_evals,
            metadata={"agent_name": self.name},
        )

    def _train_and_predict(self, task: ClassificationTask) -> dict:
        """Train the quantum classifier and optionally predict."""
        n_features = len(task.train_data[0])
        n_qubits = task.num_qubits or n_features
        depth = task.ansatz_depth
        num_params = n_qubits * 2 * depth

        x0 = np.random.uniform(-math.pi, math.pi, num_params)

        train_x = np.array(task.train_data)
        train_y = np.array(task.train_labels)

        def loss_fn(params: np.ndarray) -> float:
            return self._compute_loss(params.tolist(), train_x, train_y, n_qubits, depth)

        opt = minimize(
            loss_fn,
            x0,
            method="COBYLA",
            options={"maxiter": task.max_iterations},
        )

        self._optimal_params = opt.x.tolist()

        # Compute training accuracy
        train_preds = self._predict_batch(train_x, n_qubits, depth)
        train_acc = np.mean(np.array(train_preds) == train_y)

        result = {
            "train_accuracy": float(train_acc),
            "optimal_params": self._optimal_params,
            "converged": opt.success,
            "num_evaluations": self.history.num_evals,
            "final_loss": float(opt.fun),
        }

        # Predict on test data if provided
        if task.test_data:
            test_x = np.array(task.test_data)
            result["predictions"] = self._predict_batch(test_x, n_qubits, depth)

        return result

    def _compute_loss(
        self,
        params: list[float],
        train_x: np.ndarray,
        train_y: np.ndarray,
        n_qubits: int,
        depth: int,
    ) -> float:
        """Compute cross-entropy loss over training data."""
        total_loss = 0.0

        for features, label in zip(train_x, train_y):
            prob_1 = self._classify_sample(features.tolist(), params, n_qubits, depth)
            # Binary cross-entropy (with clipping for stability)
            prob_1 = np.clip(prob_1, 1e-7, 1 - 1e-7)
            if label == 1:
                total_loss -= math.log(prob_1)
            else:
                total_loss -= math.log(1 - prob_1)

        loss = total_loss / len(train_y)
        self.history.losses.append(loss)
        self.history.num_evals += 1

        logger.debug(f"[{self.name}] Eval {self.history.num_evals}: loss={loss:.4f}")
        return loss

    def _classify_sample(
        self,
        features: list[float],
        params: list[float],
        n_qubits: int,
        depth: int,
    ) -> float:
        """Classify a single sample. Returns P(class=1)."""
        circuit = self._build_classifier_circuit(features, params, n_qubits, depth)
        circuit.measure_all()

        result = self.backend.execute(circuit, JobConfig(shots=self.shots))
        self._quantum_results.append(result)

        # P(class=1) = probability of measuring |1> on qubit 0
        prob_1 = 0.0
        for bitstring, count in result.counts.items():
            if bitstring[0] == "1":  # First qubit determines class
                prob_1 += count / result.shots

        return prob_1

    def _predict_batch(
        self,
        data: np.ndarray,
        n_qubits: int,
        depth: int,
    ) -> list[int]:
        """Predict class labels for a batch of samples."""
        if self._optimal_params is None:
            raise ValueError("Model not trained yet")

        predictions = []
        for features in data:
            prob_1 = self._classify_sample(features.tolist(), self._optimal_params, n_qubits, depth)
            predictions.append(1 if prob_1 > 0.5 else 0)
        return predictions

    def _build_classifier_circuit(
        self,
        features: list[float],
        params: list[float],
        n_qubits: int,
        depth: int,
    ) -> QuantumCircuit:
        """Build a variational quantum classifier circuit.

        Architecture:
        1. Data encoding: RY(feature) on each qubit
        2. Variational layers: RY + RZ + CNOT entangling
        """
        qc = QuantumCircuit(n_qubits)
        qc.name = "qml_classifier"

        # Data encoding layer
        for i in range(min(len(features), n_qubits)):
            qc.ry(i, features[i])

        # Entangle encoded qubits
        for i in range(n_qubits - 1):
            qc.cx(i, i + 1)

        # Variational layers
        idx = 0
        for _ in range(depth):
            for q in range(n_qubits):
                qc.ry(q, params[idx])
                idx += 1
            for q in range(n_qubits):
                qc.rz(q, params[idx])
                idx += 1
            for q in range(n_qubits - 1):
                qc.cx(q, q + 1)

        return qc
