"""
IdeaVault — one-time model downloader.

  Image: SDXL-Turbo   → ONNX fp16  saved to  backend/models/onnx/sdxl-turbo/
  Video: ModelScope   → PyTorch     saved to  backend/models/video/text-to-video-ms-1.7b/

Usage:
    cd backend
    .venv/bin/python download_models.py
"""

import subprocess
import sys
import time
from pathlib import Path

HERE       = Path(__file__).resolve().parent          # backend/
MODELS_DIR = HERE / "models"
ONNX_DIR   = MODELS_DIR / "onnx"  / "sdxl-turbo"
VIDEO_DIR  = MODELS_DIR / "video" / "text-to-video-ms-1.7b"

SKIP_NONTORCH = [
    "*.msgpack",   # Flax/JAX
    "*.h5",        # TensorFlow Keras
    "tf_model*",
    "flax_model*",
    "*.onnx",      # unrelated ONNX blobs in the repo
    "*.pb",        # TF protobuf
    "*.tflite",
]


def step(msg: str) -> None:
    print(f"\n{'─'*60}\n  {msg}\n{'─'*60}")


# ── 0. Install optimum if missing ─────────────────────────────────────────

def ensure_optimum() -> None:
    try:
        import optimum  # noqa: F401
        print("  optimum already installed.")
    except ImportError:
        step("Installing optimum[onnxruntime]")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q",
             "optimum[onnxruntime]>=1.20.0", "onnxruntime>=1.18.0"],
            check=True,
        )
        print("  Done.")


# ── 1. Export SDXL-Turbo → ONNX fp16 ─────────────────────────────────────

def export_image_model() -> None:
    step(f"Image model — SDXL-Turbo ONNX fp16  → {ONNX_DIR}")

    if (ONNX_DIR / "model_index.json").exists():
        print("  Already exported. Skipping.")
        return

    ONNX_DIR.mkdir(parents=True, exist_ok=True)
    t = time.time()
    r = subprocess.run(
        [sys.executable, "-m", "optimum.exporters.onnx",
         "--model", "stabilityai/sdxl-turbo",
         "--task",  "stable-diffusion-xl-text2img",
         "--dtype", "fp16",
         str(ONNX_DIR)],
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError("ONNX export failed — see output above")
    print(f"  Done in {time.time()-t:.0f}s")


# ── 2. Download video model — PyTorch safetensors only ────────────────────

def download_video_model() -> None:
    step(f"Video model — text-to-video-ms-1.7b  → {VIDEO_DIR}")

    if (VIDEO_DIR / "model_index.json").exists():
        print("  Already downloaded. Skipping.")
        return

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    print("  Skipping TF / Flax / unrelated ONNX blobs.")

    from huggingface_hub import snapshot_download
    t = time.time()
    snapshot_download(
        repo_id="damo-vilab/text-to-video-ms-1.7b",
        local_dir=str(VIDEO_DIR),
        ignore_patterns=SKIP_NONTORCH,
    )
    print(f"  Done in {time.time()-t:.0f}s")


# ── Main ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nIdeaVault model downloader")
    print(f"  Models will be saved to: {MODELS_DIR}")

    failed: list[str] = []

    try:
        ensure_optimum()
    except Exception as e:
        print(f"\n  ERROR installing optimum: {e}")
        failed.append("optimum install")

    if "optimum install" not in failed:
        try:
            export_image_model()
        except Exception as e:
            print(f"\n  ERROR (image): {e}")
            failed.append("sdxl-turbo ONNX export")

    try:
        download_video_model()
    except Exception as e:
        print(f"\n  ERROR (video): {e}")
        failed.append("text-to-video-ms-1.7b")

    print(f"\n{'='*60}")
    if failed:
        for f in failed:
            print(f"  FAILED: {f}")
        sys.exit(1)
    else:
        print("  All models ready.")
        print("  Start the Celery worker and generate!")
    print("="*60)
