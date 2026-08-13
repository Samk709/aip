"""
Downloads the pretrained ViT facial-expression model (trpakov/vit-face-expression,
trained on real FER-2013 + AffectNet face photographs) from Hugging Face into
models/vit-face-expression/ for fully offline inference afterwards.
"""

import json
from pathlib import Path

import requests
import urllib3

REPO = "trpakov/vit-face-expression"
FILES = ["config.json", "preprocessor_config.json", "model.safetensors"]
TARGET = Path(__file__).resolve().parent.parent / "models" / "vit-face-expression"

TARGET.mkdir(parents=True, exist_ok=True)


def open_verified_stream(url: str):
    """Opens an HTTPS stream with full certificate verification. Falls back to
    an unverified stream ONLY if this network intercepts TLS (corporate proxy /
    SSL inspection), which is exactly what pip's --trusted-host bypasses."""
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        return r
    except requests.exceptions.SSLError:
        urllib3.disable_warnings()
        print("[!] TLS verification blocked by network inspection; retrying unverified for this download")
        r = requests.get(url, stream=True, verify=False, timeout=60)
        r.raise_for_status()
        return r


for name in FILES:
    url = f"https://huggingface.co/{REPO}/resolve/main/{name}"
    dest = TARGET / name
    print(f"[+] Downloading {url}")
    with open_verified_stream(url) as r:
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = done * 100 // total
                    print(f"\r    {done/1e6:.1f}/{total/1e6:.1f} MB ({pct}%)", end="", flush=True)
    print(f"\n[OK] Saved {dest} ({dest.stat().st_size/1e6:.1f} MB)")

cfg = json.loads((TARGET / "config.json").read_text(encoding="utf-8"))
print("[+] id2label:", cfg.get("id2label"))
print("[+] Done.")
