"""
PromptEnhancerAgent — uses local Ollama (llama3.2) to transform
a raw user prompt into a detailed, model-optimized generation prompt.

No API keys required. Ollama must be running locally.
Falls back to a rule-based enhancer if Ollama is unavailable.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .base_agent import BaseAgent

OLLAMA_BASE = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:latest"

_SYSTEM = """You are an expert AI art director specializing in generative AI image and video prompts.
Transform the user's raw idea into a highly detailed generation prompt.

Rules:
1. Expand vague descriptions with specific visual details: lighting, composition, color palette, mood, style.
2. Add relevant quality tags: "8K UHD", "photorealistic", "cinematic lighting", "sharp focus", etc.
3. Infer appropriate aspect ratio: portrait subjects → "9:16", landscapes → "16:9", square → "1:1".
4. Write a negative_prompt listing what to avoid: blur, watermark, deformed, low quality, artifacts.
5. Keep enhanced_prompt under 200 words.
6. Return ONLY valid JSON, no markdown, no explanation.

JSON schema:
{
  "enhanced_prompt": "...",
  "negative_prompt": "...",
  "style_tags": ["photorealistic", "cinematic"],
  "aspect_ratio": "16:9"
}"""


class PromptEnhancerAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("prompt_enhancer")

    async def _think(self, context: dict[str, Any]) -> dict[str, Any]:
        raw = context.get("raw_prompt", "").strip()
        if not raw:
            raise ValueError("raw_prompt is required")
        return {
            "raw_prompt": raw,
            "media_type": context.get("media_type", "image"),
            "style_hints": context.get("style_hints", []),
        }

    async def _act(self, plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        user_msg = (
            f"Media type: {plan['media_type']}\n"
            f"Style hints: {', '.join(plan['style_hints']) or 'none'}\n"
            f"Raw prompt: {plan['raw_prompt']}"
        )

        try:
            result = await self._call_ollama(user_msg)
            return result
        except Exception as exc:
            self._logger.warning("Ollama unavailable (%s), using rule-based fallback", exc)
            return self._rule_based_enhance(plan)

    async def _reflect(self, output: Any, context: dict[str, Any]) -> bool:
        required = {"enhanced_prompt", "negative_prompt", "style_tags", "aspect_ratio"}
        return isinstance(output, dict) and required.issubset(output.keys()) and \
               len(output.get("enhanced_prompt", "")) >= 10

    # ──────────────────────────────────────────────────────────────

    async def _call_ollama(self, user_msg: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    "options": {"temperature": 0.7},
                },
            )
            response.raise_for_status()
            content = response.json()["message"]["content"].strip()

            # Strip markdown fences if present
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            return json.loads(content)

    def _rule_based_enhance(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Simple fallback when Ollama is not running."""
        raw = plan["raw_prompt"]
        media = plan["media_type"]
        quality_tags = "highly detailed, sharp focus, professional photography, 8K UHD"
        if media == "video":
            quality_tags = "smooth motion, cinematic, high quality, 4K"

        return {
            "enhanced_prompt": f"{raw}, {quality_tags}",
            "negative_prompt": (
                "blurry, low quality, watermark, signature, deformed, "
                "ugly, bad anatomy, bad proportions, out of focus, noise, grain"
            ),
            "style_tags": plan.get("style_hints", ["photorealistic"]) or ["photorealistic"],
            "aspect_ratio": "16:9",
        }
