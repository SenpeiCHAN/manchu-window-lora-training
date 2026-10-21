"""Download the small, reproducible model set into /data/models.

Run this from the worker container after GPU/CUDA checks. The script does not
accept arbitrary repo IDs so a typo cannot silently replace the base model.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from huggingface_hub import snapshot_download


MODELS = {
    "sd15": {
        "repo_id": "stable-diffusion-v1-5/stable-diffusion-v1-5",
        # The standalone .safetensors checkpoint is downloaded separately.
        # Keep this snapshot limited to small pipeline metadata and tokenizer files.
        "allow_patterns": [
            "model_index.json",
            "scheduler/*.json",
            "tokenizer/*.json",
            "tokenizer/*.txt",
            "tokenizer/*.model",
            "tokenizer/*.vocab",
            "tokenizer/*.merges",
            "text_encoder/config.json",
            "text_encoder/model.fp16.safetensors",
            "unet/config.json",
            "vae/config.json",
        ],
    },
    "wd14": {
        "repo_id": "SmilingWolf/wd-v1-4-convnextv2-tagger-v2",
        "allow_patterns": ["*.json", "*.onnx", "*.txt", "*.csv"],
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["sd15", "wd14", "all"], default="all")
    parser.add_argument("--revision", default="main", help="Use a commit SHA for a reproducible production download.")
    args = parser.parse_args()
    target_root = Path(os.getenv("LORA_DATA_ROOT", "/data")) / "models"
    selected = MODELS.keys() if args.model == "all" else [args.model]
    manifest = []
    for key in selected:
        spec = MODELS[key]
        destination = target_root / key
        destination.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_download(
            repo_id=spec["repo_id"],
            revision=args.revision,
            local_dir=str(destination),
            allow_patterns=spec["allow_patterns"],
            token=os.getenv("HF_TOKEN") or None,
        )
        manifest.append({"name": key, "repo_id": spec["repo_id"], "revision": args.revision, "path": snapshot_path})
    (target_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
