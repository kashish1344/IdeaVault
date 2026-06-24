"""
Abstract base class for all agents in the IdeaVault pipeline.

Each agent follows a Think → Act → Reflect loop:
  1. think():  analyze the input and build a plan
  2. act():    execute the plan (call external API, run DSA, etc.)
  3. reflect(): validate output and decide whether to retry

Agents are stateless — all context is passed via AgentInput
and returned via AgentResult.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    success: bool
    output: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retries: int = 0
    latency_ms: float = 0.0


class BaseAgent(ABC):
    """
    Base class for all IdeaVault agents.

    Subclasses implement:
        _think(context) → plan dict
        _act(plan, context) → raw output
        _reflect(output, context) → bool (is output acceptable)
    """

    MAX_RETRIES: int = 3
    RETRY_DELAY_BASE: float = 1.0   # exponential backoff base (seconds)

    def __init__(self, name: str) -> None:
        self.name = name
        self._logger = logging.getLogger(f"ideavault.agent.{name}")

    async def run(self, context: dict[str, Any]) -> AgentResult:
        """Entry point — orchestrates think→act→reflect with retry."""
        start = time.perf_counter()
        retries = 0

        while retries <= self.MAX_RETRIES:
            try:
                plan = await self._think(context)
                self._logger.debug("plan=%s", plan)

                output = await self._act(plan, context)

                if await self._reflect(output, context):
                    elapsed = (time.perf_counter() - start) * 1000
                    return AgentResult(
                        success=True,
                        output=output,
                        retries=retries,
                        latency_ms=elapsed,
                    )

                self._logger.warning("reflect rejected output, retrying (attempt %d)", retries + 1)

            except Exception as exc:
                self._logger.exception("agent error on attempt %d: %s", retries, exc)
                if retries == self.MAX_RETRIES:
                    elapsed = (time.perf_counter() - start) * 1000
                    return AgentResult(
                        success=False,
                        output=None,
                        error=str(exc),
                        retries=retries,
                        latency_ms=elapsed,
                    )

            retries += 1
            await self._backoff(retries)

        elapsed = (time.perf_counter() - start) * 1000
        return AgentResult(
            success=False,
            output=None,
            error="max retries exceeded",
            retries=retries,
            latency_ms=elapsed,
        )

    # ──────────────────────────────────────────────────────────────
    # Abstract hooks
    # ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def _think(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze context and return an execution plan."""

    @abstractmethod
    async def _act(self, plan: dict[str, Any], context: dict[str, Any]) -> Any:
        """Execute the plan and return raw output."""

    @abstractmethod
    async def _reflect(self, output: Any, context: dict[str, Any]) -> bool:
        """Validate output quality. Return False to trigger retry."""

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    async def _backoff(self, attempt: int) -> None:
        import asyncio
        delay = self.RETRY_DELAY_BASE * (2 ** (attempt - 1))
        await asyncio.sleep(min(delay, 30.0))
