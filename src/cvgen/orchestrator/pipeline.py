"""Pipeline for chaining quantum-classical workflows."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result of a single pipeline step."""

    step_name: str
    output: Any
    duration_s: float
    success: bool
    error: str | None = None


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""

    steps: list[StepResult] = field(default_factory=list)
    final_output: Any = None

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def total_duration_s(self) -> float:
        return sum(s.duration_s for s in self.steps)


class Pipeline:
    """A sequential pipeline of quantum and classical processing steps.

    Each step is a callable that takes the output of the previous step
    as input and returns its own output.

    Example:
        pipeline = Pipeline("my_workflow")
        pipeline.add_step("prepare", build_circuit)
        pipeline.add_step("execute", lambda c: backend.execute(c))
        pipeline.add_step("analyze", analyze_result)
        result = pipeline.run(initial_input)
    """

    def __init__(self, name: str = "pipeline") -> None:
        self.name = name
        self._steps: list[tuple[str, Callable]] = []

    def add_step(self, name: str, fn: Callable) -> Pipeline:
        """Add a processing step to the pipeline.

        Args:
            name: Human-readable step name.
            fn: Callable that takes one argument and returns a result.

        Returns:
            self for chaining.
        """
        self._steps.append((name, fn))
        return self

    def run(self, initial_input: Any = None) -> PipelineResult:
        """Execute the pipeline sequentially.

        Args:
            initial_input: Input to the first step.

        Returns:
            PipelineResult with all step results.
        """
        result = PipelineResult()
        current = initial_input

        for step_name, fn in self._steps:
            logger.info(f"[{self.name}] Running step: {step_name}")
            start = time.time()

            try:
                current = fn(current)
                duration = time.time() - start
                result.steps.append(StepResult(
                    step_name=step_name,
                    output=current,
                    duration_s=duration,
                    success=True,
                ))
            except Exception as e:
                duration = time.time() - start
                result.steps.append(StepResult(
                    step_name=step_name,
                    output=None,
                    duration_s=duration,
                    success=False,
                    error=str(e),
                ))
                logger.error(f"[{self.name}] Step '{step_name}' failed: {e}")
                break

        result.final_output = current
        return result

    @property
    def steps(self) -> list[str]:
        return [name for name, _ in self._steps]

    def __len__(self) -> int:
        return len(self._steps)

    def __repr__(self) -> str:
        return f"Pipeline('{self.name}', steps={self.steps})"
