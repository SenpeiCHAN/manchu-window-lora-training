"""Fetch original Alibaba PuHuiTi 2.0 web fonts into the frontend in Docker."""
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "frontend" / "public" / "fonts"
WEIGHTS = ("55-Regular", "65-Medium", "75-SemiBold", "85-Bold")


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({
        "Referer": "https://www.alibabafonts.com/",
        "Origin": "https://www.alibabafonts.com",
        "User-Agent": "Mozilla/5.0",
    })
    manifest = []
    for weight in WEIGHTS:
        name = f"AlibabaPuHuiTi-2-{weight}"
        url = f"https://fonts.alibabadesign.com/AlibabaPuHuiTi-2/{name}/{name}.woff2"
        target = DESTINATION / f"{name}.woff2"
        response = session.get(url, timeout=90)
        response.raise_for_status()
        if response.content[:4] != b"wOF2" or len(response.content) < 1_000_000:
            raise RuntimeError(f"Expected a complete WOFF2 font from {url}")
        target.write_bytes(response.content)
        manifest.append({"file": target.name, "source": url,
                         "bytes": len(response.content),
                         "sha256": hashlib.sha256(response.content).hexdigest()})
        print(f"{name}: {len(response.content):,} bytes", flush=True)
    (DESTINATION / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
