"""Download one Hugging Face file with visible progress into /data."""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests
from huggingface_hub import hf_hub_url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_id")
    parser.add_argument("filename")
    parser.add_argument("destination")
    args = parser.parse_args()
    target = Path(args.destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    url = hf_hub_url(args.repo_id, args.filename)
    partial = target.with_suffix(target.suffix + ".part")
    received = partial.stat().st_size if partial.exists() else 0
    for attempt in range(1, 8):
        try:
            headers = {"Range": f"bytes={received}-"} if received else {}
            with requests.get(url, headers=headers, stream=True, timeout=(30, 120), allow_redirects=True) as response:
                response.raise_for_status()
                if received and response.status_code != 206:
                    received = 0
                total = received + int(response.headers.get("content-length", "0"))
                mode = "ab" if received else "wb"
                with partial.open(mode) as output:
                    for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                        if not chunk:
                            continue
                        output.write(chunk)
                        received += len(chunk)
                        if received % (128 * 1024 * 1024) < len(chunk):
                            print(f"downloaded={received / 1024**3:.2f}GiB total={total / 1024**3:.2f}GiB", flush=True)
            partial.replace(target)
            print(target, target.stat().st_size, flush=True)
            return
        except (requests.RequestException, OSError) as exc:
            print(f"download attempt {attempt} interrupted at {received / 1024**3:.2f}GiB: {exc}", flush=True)
            if attempt == 7:
                raise
            time.sleep(min(2 ** attempt, 30))


if __name__ == "__main__":
    main()
