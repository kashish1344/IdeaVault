"""
DAG-based generation pipeline.

Models the multi-step generation workflow as a Directed Acyclic Graph:

  enhance_prompt ──┐
                   ├──▶ generate_image ──▶ upscale ──▶ quality_check ──▶ store
  extract_style  ──┘

Nodes are registered with explicit dependencies.
execute() performs topological sort (Kahn's algorithm) and runs
independent nodes concurrently via asyncio.gather.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Coroutine, Optional

OnLevelStart = Callable[[list[str]], Awaitable[None]]


@dataclass
class PipelineNode:
    name: str
    fn: Callable[..., Coroutine[Any, Any, Any]]
    deps: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    success: bool
    outputs: dict[str, Any]
    errors: dict[str, str] = field(default_factory=dict)
    execution_order: list[list[str]] = field(default_factory=list)


class DAGPipeline:
    """
    Async DAG pipeline executor.

    Usage:
        pipeline = DAGPipeline()
        pipeline.add_node(PipelineNode("enhance", enhance_fn, deps=[]))
        pipeline.add_node(PipelineNode("generate", generate_fn, deps=["enhance"]))
        result = await pipeline.execute(context={...})
    """

    def __init__(self) -> None:
        self._nodes: dict[str, PipelineNode] = {}

    def add_node(self, node: PipelineNode) -> "DAGPipeline":
        if node.name in self._nodes:
            raise ValueError(f"Node '{node.name}' already registered")
        self._nodes[node.name] = node
        return self  # allow chaining

    # ──────────────────────────────────────────────────────────────
    # Topological sort — Kahn's algorithm  O(V + E)
    # ──────────────────────────────────────────────────────────────

    def _topological_levels(self) -> list[list[str]]:
        """
        Returns nodes grouped into levels.
        Nodes in the same level have no dependencies on each other
        and can be executed concurrently.
        """
        in_degree: dict[str, int] = {name: 0 for name in self._nodes}
        dependents: dict[str, list[str]] = {name: [] for name in self._nodes}

        for name, node in self._nodes.items():
            for dep in node.deps:
                if dep not in self._nodes:
                    raise ValueError(f"Node '{name}' depends on unknown '{dep}'")
                in_degree[name] += 1
                dependents[dep].append(name)

        queue: deque[str] = deque(
            name for name, deg in in_degree.items() if deg == 0
        )
        levels: list[list[str]] = []
        visited = 0

        while queue:
            level = list(queue)
            levels.append(level)
            queue.clear()

            for name in level:
                visited += 1
                for dependent in dependents[name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if visited != len(self._nodes):
            cycle_nodes = [n for n, d in in_degree.items() if d > 0]
            raise ValueError(f"Cycle detected in pipeline involving: {cycle_nodes}")

        return levels

    # ──────────────────────────────────────────────────────────────
    # Execution
    # ──────────────────────────────────────────────────────────────

    async def execute(
        self,
        context: dict[str, Any],
        on_level_start: Optional[OnLevelStart] = None,
    ) -> PipelineResult:
        """
        Execute all pipeline nodes respecting dependency order.
        Independent nodes within a level run concurrently.
        on_level_start is awaited before each level with the list of node names.
        """
        try:
            levels = self._topological_levels()
        except ValueError as exc:
            return PipelineResult(success=False, outputs={}, errors={"dag": str(exc)})

        outputs: dict[str, Any] = {**context}
        errors: dict[str, str] = {}

        for level in levels:
            if on_level_start is not None:
                try:
                    await on_level_start(level)
                except Exception:
                    pass  # step-tracking failure must never abort the pipeline
            tasks = {
                name: asyncio.create_task(
                    self._run_node(self._nodes[name], outputs)
                )
                for name in level
            }
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            for name, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    errors[name] = str(result)
                else:
                    outputs[name] = result

            if errors:
                return PipelineResult(
                    success=False,
                    outputs=outputs,
                    errors=errors,
                    execution_order=levels,
                )

        return PipelineResult(
            success=True,
            outputs=outputs,
            execution_order=levels,
        )

    @staticmethod
    async def _run_node(node: PipelineNode, context: dict[str, Any]) -> Any:
        dep_inputs = {dep: context[dep] for dep in node.deps if dep in context}
        return await node.fn(context=context, **dep_inputs)

    def validate(self) -> list[str]:
        """Return list of validation errors without executing."""
        errors: list[str] = []
        try:
            self._topological_levels()
        except ValueError as exc:
            errors.append(str(exc))
        return errors
