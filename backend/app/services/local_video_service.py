"""
Local video generation via HuggingFace diffusers.

Completely free, open-source, runs locally on MPS / CPU.
Models are downloaded once to ~/.cache/huggingface/ on first use.

Supported models:
  - damo-vilab/text-to-video-ms-1.7b  (ModelScope, ~4GB, fast)
  - cerspense/zeroscope_v2_576w       (higher quality, ~5GB)
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("ideavault.video_service")

OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/ideavault/videos"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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


def _get_dtype(device: str) -> "torch.dtype":
    import torch
    # MPS float16 produces NaN/black frames for video diffusion models.
    # CUDA float16 is fine; MPS and CPU require float32.
    return torch.float16 if device == "cuda" else torch.float32


_MODELS_DIR = Path(__file__).resolve().parents[3] / "models" / "video"


def _local_path(model_id: str) -> str:
    """Return local path if model is present, else fall back to HF repo id."""
    local = _MODELS_DIR / model_id.split("/")[-1]
    if local.exists():
        return str(local)
    return model_id


def _load_pipeline(model_id: str) -> Any:
    if model_id in _pipeline_cache:
        return _pipeline_cache[model_id]

    import torch
    from diffusers import DiffusionPipeline

    device = _get_device()
    dtype = _get_dtype(device)

    source = _local_path(model_id)
    logger.info("loading video pipeline: %s on %s (dtype=%s)", source, device, dtype)

    pipe = DiffusionPipeline.from_pretrained(
        source,
        torch_dtype=dtype,
        local_files_only=source != model_id,
    )
    pipe = pipe.to(device)

    if hasattr(pipe, "enable_attention_slicing"):
        pipe.enable_attention_slicing()
    if hasattr(pipe, "enable_vae_slicing"):
        pipe.enable_vae_slicing()

    _pipeline_cache[model_id] = pipe
    logger.info("video pipeline loaded: %s", model_id)
    return pipe


def _export_frames_to_video(frames: list, output_path: Path, fps: int = 8) -> None:
    from diffusers.utils import export_to_video
    export_to_video(frames, str(output_path), fps=fps)


async def generate_video(
    prompt: str,
    negative_prompt: str = "",
    model_id: str = "damo-vilab/text-to-video-ms-1.7b",
    num_frames: int = 16,
    num_inference_steps: int = 25,
    guidance_scale: float = 7.5,
    width: int = 256,
    height: int = 256,
    fps: int = 8,
    seed: int | None = None,
) -> str:
    """
    Generate a video and save it locally as MP4.
    Returns the absolute file path.
    """
    import asyncio
    import torch

    loop = asyncio.get_running_loop()
    output_path = OUTPUT_DIR / f"{uuid.uuid4().hex}.mp4"

    def _run() -> None:
        pipe = _load_pipeline(model_id)
        device = _get_device()
        generator = torch.Generator(device=device).manual_seed(seed) if seed is not None else None

        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt or None,
            num_frames=num_frames,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
            output_type="pil",
        )

        # Diffusers ≥0.21 wraps output in result.frames (list of lists).
        # Older versions may use result.images or a flat list.
        if hasattr(result, "frames"):
            raw = result.frames
            # Nested: [[PIL, PIL, ...]] — take batch 0
            frames = raw[0] if isinstance(raw[0], (list, tuple)) else list(raw)
        else:
            frames = list(result.images)

        if not frames:
            raise RuntimeError("video pipeline returned no frames")

        _export_frames_to_video(frames, output_path, fps=fps)
        logger.info("video saved: %s (%d frames @ %dfps)", output_path, len(frames), fps)

    await loop.run_in_executor(None, _run)
    return str(output_path)
