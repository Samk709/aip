"""Downloads the full real FER-2013 train/val splits (Kaggle CSV format) from
the chitradrishti/fer2013 Hugging Face mirror into data/ for real-data training.
Resumable: interrupted downloads continue from the last byte written."""

import time
from pathlib import Path

import requests
import urllib3

BASE = "https://huggingface.co/datasets/chitradrishti/fer2013/resolve/main/fer2013"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILES = ["train.csv", "val.csv"]
# Approximate full sizes used to detect complete downloads (skip if >= 95% present)
EXPECTED_SIZE = {"train.csv": 241_000_000, "val.csv": 30_000_000}


def hf_get(url: str, **kwargs) -> requests.Response:
    """Verified TLS first; falls back to unverified only if this network's
    SSL inspection breaks verification (same as pip --trusted-host)."""
    try:
        r = requests.get(url, timeout=60, **kwargs)
        r.raise_for_status()
        return r
    except requests.exceptions.SSLError:
        urllib3.disable_warnings()
        r = requests.get(url, timeout=60, verify=False, **kwargs)
        r.raise_for_status()
        return r


def download_resumable(url: str, dest: Path, max_attempts: int = 25):
    """Streams a file with HTTP Range resume + retry on connection errors."""
    for attempt in range(1, max_attempts + 1):
        offset = dest.stat().st_size if dest.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            r = hf_get(url, stream=True, headers=headers)
            mode = "ab" if (r.status_code == 206 and offset > 0) else "wb"
            total = int(r.headers.get("content-length", 0)) + offset
            done = offset if mode == "ab" else 0
            with open(dest, mode) as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r    {done/1e6:.1f}/{total/1e6:.1f} MB ({done*100//total}%)", end="", flush=True)
            print(f"\n[OK] Saved {dest} ({dest.stat().st_size/1e6:.1f} MB)")
            return
        except Exception as e:
            print(f"\n[!] Connection error: {type(e).__name__}; resuming from "
                  f"{dest.stat().st_size/1e6:.1f} MB (attempt {attempt}/{max_attempts})")
            time.sleep(2)
    raise RuntimeError(f"Download failed after {max_attempts} attempts: {url}")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dest = DATA_DIR / name
        if dest.exists() and dest.stat().st_size >= EXPECTED_SIZE[name] * 0.95:
            print(f"[i] {dest} already complete ({dest.stat().st_size/1e6:.1f} MB) - skipping")
            continue
        url = f"{BASE}/{name}"
        print(f"[+] Downloading {url}")
        download_resumable(url, dest)
    print("[+] Done.")


if __name__ == "__main__":
    main()
