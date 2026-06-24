"""
StyleAgent — selects the local diffusers model and parameters
based on style tags, quality preset, and media type.

All models are free and run locally via HuggingFace diffusers.
No API keys needed.
"""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent

# ── Local image model catalogue ────────────────────────────────────────────
_IMAGE_MODELS = {
    "sdxl-turbo": {
        "model_id": "stabilityai/sdxl-turbo",
        "strengths": ["speed", "general", "photorealistic"],
        "steps": 4,
        "guidance_scale": 0.0,   # turbo uses 0 guidance
        "width": 512,
        "height": 512,
        "estimated_seconds": 15,
    },
    "sdxl": {
        "model_id": "stabilityai/stable-diffusion-xl-base-1.0",
        "strengths": ["quality", "artistic", "detailed"],
        "steps": 20,
        "guidance_scale": 7.5,
        "width": 1024,
        "height": 1024,
        "estimated_seconds": 60,
    },
    "sd15": {
        "model_id": "runwayml/stable-diffusion-v1-5",
        "strengths": ["speed", "general", "lightweight"],
        "steps": 20,
        "guidance_scale": 7.5,
        "width": 512,
        "height": 512,
        "estimated_seconds": 20,
    },
}

# ── Local video model catalogue ────────────────────────────────────────────
# max_frames: the model was trained/tested up to this count — beyond it
# quality degrades or OOM occurs on consumer hardware.
_VIDEO_MODELS = {
    "modelscope": {
        "model_id": "damo-vilab/text-to-video-ms-1.7b",
        "strengths": ["general", "lightweight"],
        "fps": 8,
        "max_frames": 24,
        "num_inference_steps": 25,
        "guidance_scale": 7.5,
        "width": 256,
        "height": 256,
        "estimated_seconds": 120,
    },
    "zeroscope": {
        "model_id": "cerspense/zeroscope_v2_576w",
        "strengths": ["quality", "cinematic"],
        "fps": 8,
        "max_frames": 36,
        "num_inference_steps": 40,
        "guidance_scale": 7.5,
        "width": 576,
        "height": 320,
        "estimated_seconds": 180,
    },
}


class StyleAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("style_agent")

    async def _think(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "style_tags": context.get("style_tags", []),
            "media_type": context.get("media_type", "image"),
            "quality_preset": context.get("quality_preset", "standard"),
        }

    async def _act(self, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        tags = set(plan["style_tags"])
        quality = plan["quality_preset"]

        if plan["media_type"] == "video":
            duration = context.get("duration_seconds", 4)
            return self._select_video(tags, quality, duration)
        return self._select_image(tags, quality)

    async def _reflect(self, output: Any, context: dict[str, Any]) -> bool:
        return isinstance(output, dict) and "model_id" in output

    # ──────────────────────────────────────────────────────────────

    def _select_image(self, tags: set[str], quality: str) -> dict[str, Any]:
        if quality == "draft":
            spec = _IMAGE_MODELS["sdxl-turbo"]
        elif quality == "ultra":
            spec = _IMAGE_MODELS["sdxl"]
        else:
            spec = _IMAGE_MODELS["sdxl-turbo"]  # fast default for local

        return {
            "model_id": spec["model_id"],
            "model_params": {
                "num_inference_steps": spec["steps"],
                "guidance_scale": spec["guidance_scale"],
                "width": spec["width"],
                "height": spec["height"],
            },
            "estimated_seconds": spec["estimated_seconds"],
        }

    def _select_video(self, tags: set[str], quality: str, duration_seconds: int = 4) -> dict[str, Any]:
        spec = _VIDEO_MODELS["zeroscope"] if quality == "ultra" else _VIDEO_MODELS["modelscope"]

        fps = spec["fps"]
        max_frames = spec["max_frames"]
        # Clamp to what the model supports — going over max_frames causes OOM / quality collapse
        num_frames = min(max_frames, max(8, duration_seconds * fps))

        return {
            "model_id": spec["model_id"],
            "model_params": {
                "num_frames": num_frames,
                "num_inference_steps": spec["num_inference_steps"],
                "guidance_scale": spec["guidance_scale"],
                "fps": fps,
                "width": spec["width"],
                "height": spec["height"],
            },
            "estimated_seconds": spec["estimated_seconds"],
        }
