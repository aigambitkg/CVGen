"""DAG-based workflow execution for quantum-classical pipelines."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Result of a complete DAG workflow execution."""

    node_results: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    total_duration_s: float = 0.0
    execution_order: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"WorkflowResult(success={self.success}, nodes={len(self.node_results)}, "
            f"duration_s={self.total_duration_s:.2f})"
        )


class DAGWorkflow:
    """Directed Acyclic Graph workflow for executing interdependent tasks.

    Supports:
    - Topological execution (respecting dependencies)
    - Parallel execution of independent nodes
    - Cycle detection
    - Visualization to Mermaid format
    - Comprehensive error tracking

    Example:
        workflow = DAGWorkflow("analysis_pipeline")
        workflow.add_node("prepare", prepare_circuit)
        workflow.add_node("execute", execute_on_backend, depends_on=["prepare"])
        workflow.add_node("analyze", analyze_results, depends_on=["execute"])
        result = workflow.run(initial_inputs={"circuit": qc})
    """

    def __init__(self, name: str = "workflow") -> None:
        """Initialize the DAG workflow.

        Args:
            name: Human-readable workflow name.
        """
        self.name = name
        self._nodes: dict[str, Callable] = {}
        self._dependencies: dict[str, list[str]] = {}

    def add_node(
        self,
        name: str,
        fn: Callable,
        depends_on: Optional[list[str]] = None,
    ) -> DAGWorkflow:
        """Add a node to the workflow.

        Args:
            name: Unique node identifier.
            fn: Callable that takes node inputs and returns output.
            depends_on: List of node names this node depends on.

        Returns:
            self for method chaining.

        Raises:
            ValueError: If node already exists.
        """
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists in workflow")

        self._nodes[name] = fn
        self._dependencies[name] = depends_on or []
        return self

    def run(
        self,
        initial_inputs: Optional[dict[str, Any]] = None,
    ) -> WorkflowResult:
        """Execute the workflow in topological order with parallel execution.

        Args:
            initial_inputs: Dictionary of inputs for root nodes.

        Returns:
            WorkflowResult with node outputs and execution metadata.

        Raises:
            ValueError: If workflow contains cycles.
            Exception: If any node execution fails.
        """
        initial_inputs = initial_inputs or {}
        start_time = time.time()

        # Check for cycles
        self._check_for_cycles()

        # Compute topological order and execution groups
        execution_groups = self._compute_execution_groups()

        logger.info(f"[{self.name}] Starting workflow with {len(self._nodes)} nodes")

        node_results: dict[str, Any] = {}
        execution_order: list[str] = []

        # Execute nodes in topological order, with parallel execution within groups
        for group in execution_groups:
            if not group:
                continue

            logger.debug(f"[{self.name}] Executing group: {group}")

            if len(group) == 1:
                # Single node - execute directly
                node_name = group[0]
                try:
                    node_fn = self._nodes[node_name]
                    node_input = self._prepare_node_input(
                        node_name, initial_inputs, node_results
                    )
                    logger.info(f"[{self.name}] Running node: {node_name}")
                    start = time.time()
                    output = node_fn(node_input)
                    duration = time.time() - start
                    node_results[node_name] = output
                    execution_order.append(node_name)
                    logger.debug(f"[{self.name}] Node '{node_name}' completed in {duration:.3f}s")
                except Exception as e:
                    logger.error(f"[{self.name}] Node '{node_name}' failed: {e}")
                    return WorkflowResult(
                        node_results=node_results,
                        success=False,
                        total_duration_s=time.time() - start_time,
                        execution_order=execution_order,
                    )
            else:
                # Multiple independent nodes - execute in parallel
                with ThreadPoolExecutor(max_workers=len(group)) as executor:
                    futures = {}
                    for node_name in group:
                        node_fn = self._nodes[node_name]
                        node_input = self._prepare_node_input(
                            node_name, initial_inputs, node_results
                        )
                        logger.info(f"[{self.name}] Queuing node: {node_name}")
                        future = executor.submit(node_fn, node_input)
                        futures[future] = node_name

                    # Collect results as they complete
                    for future in as_completed(futures):
                        node_name = futures[future]
                        try:
                            output = future.result()
                            node_results[node_name] = output
                            execution_order.append(node_name)
                            logger.debug(
                                f"[{self.name}] Node '{node_name}' completed successfully"
                            )
                        except Exception as e:
                            logger.error(f"[{self.name}] Node '{node_name}' failed: {e}")
                            return WorkflowResult(
                                node_results=node_results,
                                success=False,
                                total_duration_s=time.time() - start_time,
                                execution_order=execution_order,
                            )

        total_duration = time.time() - start_time
        logger.info(f"[{self.name}] Workflow completed successfully in {total_duration:.3f}s")

        return WorkflowResult(
            node_results=node_results,
            success=True,
            total_duration_s=total_duration,
            execution_order=execution_order,
        )

    def _check_for_cycles(self) -> None:
        """Check if the workflow DAG contains cycles.

        Raises:
            ValueError: If a cycle is detected.
        """
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dependent in self._dependencies.get(node, []):
                if dependent not in visited:
                    if has_cycle(dependent):
                        return True
                elif dependent in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if has_cycle(node):
                    raise ValueError(
                        f"Workflow '{self.name}' contains a cycle involving node '{node}'"
                    )

    def _compute_execution_groups(self) -> list[list[str]]:
        """Compute groups of independent nodes for parallel execution.

        Returns:
            List of lists, where each inner list contains nodes that can execute
            in parallel (have no dependencies between them).
        """
        # Calculate in-degree (number of dependencies) for each node
        in_degree: dict[str, int] = {}
        for node in self._nodes:
            in_degree[node] = len(self._dependencies.get(node, []))

        # Topological sort with level tracking
        groups: list[list[str]] = []
        remaining = set(self._nodes.keys())

        while remaining:
            # Find all nodes with no remaining dependencies
            current_level = [node for node in remaining if in_degree[node] == 0]

            if not current_level:
                # This should not happen if _check_for_cycles passed
                raise RuntimeError(
                    f"Circular dependency detected in {self.name}"
                )

            groups.append(current_level)

            # Remove these nodes and update in-degrees
            for node in current_level:
                remaining.remove(node)

            # Update in-degrees for remaining nodes
            for node in remaining:
                node_deps = self._dependencies.get(node, [])
                in_degree[node] = sum(1 for dep in node_deps if dep in remaining)

        return groups

    def _prepare_node_input(
        self,
        node_name: str,
        initial_inputs: dict[str, Any],
        completed_results: dict[str, Any],
    ) -> Any:
        """Prepare input for a node based on its dependencies.

        Args:
            node_name: Name of the node.
            initial_inputs: Initial workflow inputs.
            completed_results: Results from already-executed nodes.

        Returns:
            Input value for the node.
        """
        deps = self._dependencies.get(node_name, [])

        if not deps:
            # Root node - use initial inputs
            return initial_inputs.get(node_name) or {}

        if len(deps) == 1:
            # Single dependency - pass its result directly
            return completed_results.get(deps[0])

        # Multiple dependencies - pass all their results in a dict
        return {dep: completed_results.get(dep) for dep in deps}

    def to_mermaid(self) -> str:
        """Generate a Mermaid diagram of the workflow DAG.

        Returns:
            Mermaid diagram string.
        """
        lines = [f"graph TD"]

        # Add nodes
        for node_name in self._nodes:
            lines.append(f'    {node_name}["{node_name}"]')

        # Add edges
        for node_name, deps in self._dependencies.items():
            for dep in deps:
                lines.append(f"    {dep} --> {node_name}")

        return "\n".join(lines)

    def __len__(self) -> int:
        """Get the number of nodes in the workflow."""
        return len(self._nodes)

    def __repr__(self) -> str:
        return f"DAGWorkflow('{self.name}', nodes={len(self._nodes)})"
