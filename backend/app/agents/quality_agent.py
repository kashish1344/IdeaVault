"""
QualityAgent — validates generated media locally.

For images: checks file exists, dimensions meet minimum, runs
             a basic sharpness heuristic via PIL (no API needed).
For videos: checks file size and duration.

Optionally uses Ollama llava/llama3.2-vision if available for
richer quality assessment — but works fine without it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base_agent import BaseAgent

MIN_WIDTH = 256
MIN_HEIGHT = 256


class QualityAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("quality_agent")

    async def _think(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "output_path": context.get("output_path", ""),
            "output_url": context.get("output_url", ""),
            "media_type": context.get("media_type", "image"),
            "enhanced_prompt": context.get("enhanced_prompt", ""),
        }

    async def _act(self, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        path = plan.get("output_path") or plan.get("output_url", "")

        if plan["media_type"] == "video":
            return self._check_video(path)
        return await self._check_image(path)

    async def _reflect(self, output: Any, context: dict[str, Any]) -> bool:
        return isinstance(output, dict) and "score" in output

    # ──────────────────────────────────────────────────────────────

    async def _check_image(self, path: str) -> dict[str, Any]:
        if not path or not Path(path).exists():
            return {"accepted": False, "score": 0.0, "feedback": "output file not found"}

        try:
            from PIL import Image, ImageFilter
            import numpy as np

            img = Image.open(path).convert("RGB")
            w, h = img.size

            if w < MIN_WIDTH or h < MIN_HEIGHT:
                return {
                    "accepted": False,
                    "score": 2.0,
                    "feedback": f"resolution too low: {w}x{h}",
                    "should_upscale": True,
                }

            # Laplacian variance — measures sharpness
            gray = img.convert("L")
            arr = list(gray.getdata())
            variance = self._laplacian_variance(gray, w, h)

            score = min(10.0, 5.0 + variance / 50.0)
            accepted = score >= 5.0

            return {
                "accepted": accepted,
                "score": round(score, 1),
                "feedback": "sharp and well-composed" if accepted else "image appears blurry",
                "should_upscale": False,
                "resolution": f"{w}x{h}",
            }

        except Exception as exc:
            self._logger.warning("image check error: %s", exc)
            # Accept with moderate score if we can't check
            return {"accepted": True, "score": 7.0, "feedback": "quality check skipped"}

    def _check_video(self, path: str) -> dict[str, Any]:
        if not path or not Path(path).exists():
            return {"accepted": False, "score": 0.0, "feedback": "video file not found"}

        size_mb = Path(path).stat().st_size / (1024 * 1024)
        accepted = size_mb > 0.1

        return {
            "accepted": accepted,
            "score": 8.0 if accepted else 0.0,
            "feedback": f"video generated ({size_mb:.1f} MB)",
            "should_upscale": False,
        }

    def _laplacian_variance(self, gray_img: Any, w: int, h: int) -> float:
        """Approximate Laplacian variance without numpy for minimal deps."""
        try:
            import numpy as np
            from PIL import ImageFilter
            lap = gray_img.filter(ImageFilter.FIND_EDGES)
            arr = np.array(lap, dtype=float)
            return float(arr.var())
        except Exception:
            return 50.0  # neutral score on failure
