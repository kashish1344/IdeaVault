#!/usr/bin/env python3
"""
Download and export models required by IdeaVault.

Run once before first use:
    cd ideavault
    python scripts/download_models.py

What this does:
  1. Image models  — exports stabilityai/sdxl-turbo to ONNX for CoreML / CUDA
                     acceleration (2-3× faster than PyTorch on Apple M-series).
                     Falls back to HuggingFace cache if optimum is not installed.
  2. Video models  — downloads ModelScope and (optionally) ZeroScope to
                     backend/models/video/ so generation works fully offline.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "backend" / "models"
ONNX_DIR   = MODELS_DIR / "onnx"
VIDEO_DIR  = MODELS_DIR / "video"

IMAGE_MODEL_ID = "stabilityai/sdxl-turbo"
VIDEO_MODELS = {
    "modelscope": "damo-vilab/text-to-video-ms-1.7b",   # ~4 GB, fast (default)
    "zeroscope":  "cerspense/zeroscope_v2_576w",         # ~5 GB, higher quality
}


def export_image_onnx(model_id: str) -> None:
    onnx_dest = ONNX_DIR / model_id.split("/")[-1]
    if (onnx_dest / "model_index.json").exists():
        print(f"[image] ONNX model already present at {onnx_dest} — skipping export.")
        return

    print(f"[image] Exporting {model_id} to ONNX … (this takes ~10 min on first run)")
    try:
        from optimum.exporters.onnx import main_export

        ONNX_DIR.mkdir(parents=True, exist_ok=True)
        main_export(
            model_name_or_path=model_id,
            output=str(onnx_dest),
            task="stable-diffusion-xl",
            opset=17,
        )
        print(f"[image] ONNX export saved to {onnx_dest}")
    except ImportError:
        print(
            "[image] optimum not installed — skipping ONNX export.\n"
            "        Install with:  pip install optimum[exporters]\n"
            "        The service will use the PyTorch/diffusers fallback instead."
        )
    except Exception as exc:
        print(f"[image] ONNX export failed: {exc}")
        print("        The service will fall back to PyTorch automatically.")


def download_video_model(name: str, model_id: str) -> None:
    dest = VIDEO_DIR / model_id.split("/")[-1]
    if dest.exists() and any(dest.iterdir()):
        print(f"[video/{name}] Already present at {dest} — skipping.")
        return

    print(f"[video/{name}] Downloading {model_id} to {dest} …")
    try:
        from huggingface_hub import snapshot_download

        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=model_id,
            local_dir=str(dest),
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*"],
        )
        print(f"[video/{name}] Downloaded to {dest}")
    except ImportError:
        print(
            "[video] huggingface_hub not installed.\n"
            "        Install with:  pip install huggingface_hub\n"
            "        Or the service will auto-download on first generation."
        )
    except Exception as exc:
        print(f"[video/{name}] Download failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download IdeaVault models")
    parser.add_argument("--skip-image",     action="store_true", help="Skip image ONNX export")
    parser.add_argument("--skip-video",     action="store_true", help="Skip video model download")
    parser.add_argument("--zeroscope-only", action="store_true", help="Only download ZeroScope (skip ModelScope)")
    parser.add_argument("--all-video",      action="store_true", help="Download both ModelScope and ZeroScope")
    args = parser.parse_args()

    print("=" * 60)
    print("  IdeaVault — Model Setup")
    print("=" * 60)

    if not args.skip_image:
        export_image_onnx(IMAGE_MODEL_ID)
    else:
        print("[image] Skipped.")

    if not args.skip_video:
        if args.zeroscope_only:
            download_video_model("zeroscope", VIDEO_MODELS["zeroscope"])
        elif args.all_video:
            for name, mid in VIDEO_MODELS.items():
                download_video_model(name, mid)
        else:
            # Default: only the smaller/faster ModelScope model
            download_video_model("modelscope", VIDEO_MODELS["modelscope"])
    else:
        print("[video] Skipped.")

    print("=" * 60)
    print("  Done. Start the server with:  ./start.sh")
    print("=" * 60)


if __name__ == "__main__":
    main()
