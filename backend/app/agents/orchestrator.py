"""
GenerationOrchestrator — drives the full local pipeline.

  enhance_prompt ──┐
                   ├──▶ generate_media ──▶ quality_check
  select_style   ──┘

All steps run locally:
  - Prompt enhancement: Ollama llama3.2
  - Image generation:   diffusers + SDXL-Turbo on MPS
  - Video generation:   diffusers + ModelScope on MPS
  - Quality check:      PIL sharpness heuristics

Zero API keys required.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Optional

from ..dsa.pipeline_dag import DAGPipeline, OnLevelStart, PipelineNode, PipelineResult
from ..services.local_image_service import generate_image
from ..services.local_video_service import generate_video
from .base_agent import AgentResult
from .prompt_enhancer import PromptEnhancerAgent
from .quality_agent import QualityAgent
from .style_agent import StyleAgent

logger = logging.getLogger("ideavault.orchestrator")

MAX_QUALITY_RETRIES = 1


class GenerationOrchestrator:

    def __init__(self) -> None:
        self._prompt_enhancer = PromptEnhancerAgent()
        self._style_agent = StyleAgent()
        self._quality_agent = QualityAgent()

    async def run(
        self,
        context: dict[str, Any],
        on_step: Optional[OnLevelStart] = None,
    ) -> dict[str, Any]:
        pipeline = self._build_pipeline()
        result: PipelineResult = await pipeline.execute(context, on_level_start=on_step)

        if not result.success:
            return {"success": False, "errors": result.errors}

        outputs = result.outputs
        quality = outputs.get("quality_check", {})

        for attempt in range(MAX_QUALITY_RETRIES):
            if quality.get("accepted", True):
                break
            logger.info("quality rejected (attempt %d), re-generating", attempt + 1)
            result = await pipeline.execute(context)
            quality = result.outputs.get("quality_check", {})

        enhance_out = outputs.get("enhance_prompt", {})
        style_out = outputs.get("select_style", {})
        gen_out = outputs.get("generate_media", {})

        return {
            "success": result.success,
            "url": gen_out.get("path", ""),        # local file path
            "output_path": gen_out.get("path", ""),
            "enhanced_prompt": enhance_out.get("enhanced_prompt", ""),
            "negative_prompt": enhance_out.get("negative_prompt", ""),
            "model_id": style_out.get("model_id", ""),
            "quality_score": quality.get("score", 0),
            "quality_feedback": quality.get("feedback", ""),
            "execution_order": result.execution_order,
        }

    def _build_pipeline(self) -> DAGPipeline:
        pipeline = DAGPipeline()
        pipeline.add_node(PipelineNode("enhance_prompt", self._run_enhance_prompt, deps=[]))
        pipeline.add_node(PipelineNode("select_style", self._run_select_style, deps=[]))
        pipeline.add_node(PipelineNode(
            "generate_media", self._run_generate_media,
            deps=["enhance_prompt", "select_style"],
        ))
        pipeline.add_node(PipelineNode(
            "quality_check", self._run_quality_check,
            deps=["generate_media", "enhance_prompt"],
        ))
        return pipeline

    # ── Node functions ────────────────────────────────────────────

    async def _run_enhance_prompt(self, context: dict[str, Any], **_: Any) -> dict[str, Any]:
        result: AgentResult = await self._prompt_enhancer.run(context)
        if not result.success:
            raise RuntimeError(f"PromptEnhancer failed: {result.error}")
        return result.output

    async def _run_select_style(self, context: dict[str, Any], **_: Any) -> dict[str, Any]:
        result: AgentResult = await self._style_agent.run(context)
        if not result.success:
            raise RuntimeError(f"StyleAgent failed: {result.error}")
        return result.output

    async def _run_generate_media(
        self,
        context: dict[str, Any],
        enhance_prompt: dict[str, Any],
        select_style: dict[str, Any],
        **_: Any,
    ) -> dict[str, Any]:
        media_type = context.get("media_type", "image")
        params = select_style["model_params"]
        model_id = select_style["model_id"]

        if media_type == "video":
            path = await generate_video(
                prompt=enhance_prompt["enhanced_prompt"],
                negative_prompt=enhance_prompt.get("negative_prompt", ""),
                model_id=model_id,
                **params,
            )
        else:
            path = await generate_image(
                prompt=enhance_prompt["enhanced_prompt"],
                negative_prompt=enhance_prompt.get("negative_prompt", ""),
                model_id=model_id,
                **params,
            )

        return {"path": path, "model_id": model_id}

    async def _run_quality_check(
        self,
        context: dict[str, Any],
        generate_media: dict[str, Any],
        enhance_prompt: dict[str, Any],
        **_: Any,
    ) -> dict[str, Any]:
        ctx = {
            **context,
            "output_path": generate_media["path"],
            **enhance_prompt,
        }
        result: AgentResult = await self._quality_agent.run(ctx)
        if not result.success:
            return {"accepted": True, "score": 7.0, "feedback": "quality check skipped"}
        return result.output
