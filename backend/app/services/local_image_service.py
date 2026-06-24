"""
Local image generation via ONNX Runtime (primary) or PyTorch MPS (fallback).

ONNX path:  optimum ORTStableDiffusionXLPipeline + CoreML EP on Apple M4
            ~2–3× faster than PyTorch MPS after one-time export (~10 min).

Fallback:   diffusers AutoPipelineForText2Image on MPS/CPU
            Used automatically if ONNX model not yet exported.

Run download_models.py once to export the ONNX model before first use.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("ideavault.image_service")

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/ideavault/images"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"
ONNX_DIR   = MODELS_DIR / "onnx"

_pipeline_cache: dict[str, Any] = {}


def _get_device() -> str:
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _onnx_model_dir(model_id: str) -> Path:
    # e.g. "stabilityai/sdxl-turbo" → models/onnx/sdxl-turbo
    return ONNX_DIR / model_id.split("/")[-1]


def _load_onnx_pipeline(model_id: str) -> Any | None:
    """Load ONNX pipeline with CoreML execution provider (Apple M4)."""
    model_dir = _onnx_model_dir(model_id)
    if not (model_dir / "model_index.json").exists():
        return None

    try:
        from optimum.onnxruntime import ORTStableDiffusionXLPipeline

        import platform
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            provider = "CoreMLExecutionProvider"
        else:
            provider = "CUDAExecutionProvider" if _get_device() == "cuda" else "CPUExecutionProvider"

        logger.info("loading ONNX image pipeline: %s (provider=%s)", model_id, provider)
        pipe = ORTStableDiffusionXLPipeline.from_pretrained(
            str(model_dir),
            provider=provider,
        )
        logger.info("ONNX pipeline loaded: %s", model_id)
        return pipe
    except Exception as exc:
        logger.warning("ONNX load failed (%s), will use PyTorch fallback", exc)
        return None


def _load_pytorch_pipeline(model_id: str) -> Any:
    """PyTorch fallback pipeline via diffusers."""
    import torch
    from diffusers import AutoPipelineForText2Image, DiffusionPipeline

    device = _get_device()
    dtype = torch.float16 if device in ("cuda", "mps") else torch.float32
    logger.info("loading PyTorch image pipeline: %s on %s", model_id, device)

    if "turbo" in model_id.lower():
        pipe = AutoPipelineForText2Image.from_pretrained(
            model_id,
            torch_dtype=dtype,
            variant="fp16" if device != "cpu" else None,
        )
    else:
        pipe = DiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)

    pipe = pipe.to(device)
    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    logger.info("PyTorch pipeline loaded: %s on %s", model_id, device)
    return pipe


def _load_pipeline(model_id: str) -> Any:
    if model_id in _pipeline_cache:
        return _pipeline_cache[model_id]

    pipe = _load_onnx_pipeline(model_id) or _load_pytorch_pipeline(model_id)
    _pipeline_cache[model_id] = pipe
    return pipe


async def generate_image(
    prompt: str,
    negative_prompt: str = "",
    model_id: str = "stabilityai/sdxl-turbo",
    num_inference_steps: int = 4,
    guidance_scale: float = 0.0,
    width: int = 512,
    height: int = 512,
    seed: int | None = None,
) -> str:
    import asyncio
    import torch

    loop = asyncio.get_running_loop()
    output_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.png"

    def _run() -> None:
        pipe = _load_pipeline(model_id)
        # Use CPU generator — works cross-device (MPS/CUDA/CPU) without compatibility issues
        generator = torch.Generator("cpu").manual_seed(seed) if seed is not None else None

        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "num_inference_steps": num_inference_steps,
            "width": width,
            "height": height,
        }
        if generator is not None:
            kwargs["generator"] = generator
        if guidance_scale > 0:
            kwargs["negative_prompt"] = negative_prompt or None
            kwargs["guidance_scale"] = guidance_scale

        result = pipe(**kwargs)
        image = result.images[0]
        image.save(str(output_path))
        logger.info("image saved: %s (%dx%d)", output_path, image.width, image.height)

    await loop.run_in_executor(None, _run)
    return str(output_path)
