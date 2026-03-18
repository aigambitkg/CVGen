"""Task orchestration and circuit optimization."""

from __future__ import annotations

from cvgen.orchestrator.fallback import AllBackendsFailedError, FallbackChain, FallbackResult
from cvgen.orchestrator.optimizer import CircuitOptimizer
from cvgen.orchestrator.pipeline import Pipeline, PipelineResult, StepResult
from cvgen.orchestrator.retry import RetryPolicy, RetryResult
from cvgen.orchestrator.scheduler import (
    BackendRequirements,
    JobRecord,
    JobStatistics,
    SmartScheduler,
    TaskScheduler,
)
from cvgen.orchestrator.validator import CircuitValidator, ComplexityEstimate, ValidationResult
from cvgen.orchestrator.workflow import DAGWorkflow, WorkflowResult

__all__ = [
    # Scheduler
    "TaskScheduler",
    "SmartScheduler",
    "JobRecord",
    "JobStatistics",
    "BackendRequirements",
    # Validator
    "CircuitValidator",
    "ValidationResult",
    "ComplexityEstimate",
    # Retry
    "RetryPolicy",
    "RetryResult",
    # Fallback
    "FallbackChain",
    "FallbackResult",
    "AllBackendsFailedError",
    # Pipeline
    "Pipeline",
    "PipelineResult",
    "StepResult",
    # Optimizer
    "CircuitOptimizer",
    # Workflow
    "DAGWorkflow",
    "WorkflowResult",
]
