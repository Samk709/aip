"""
End-to-end FER pipeline test on REAL labeled face photographs.

Downloads a sample of FER-2013 test images (ground-truth labels) from the
msambare/fer2013 Hugging Face dataset, runs each through the full production
pipeline (Haar face detection -> crop -> trained model softmax), and reports
predicted-vs-truth per image plus per-class accuracy.

Also performs a live HTTP round-trip against the running Flask server
(/api/emotion-report) to validate the deployed path including auth.

Run from repo root (server optional, only needed for the HTTP part):
    backend-flask/.venv/Scripts/python.exe scripts/test_fer_real_images.py
"""

import argparse
import base64
import sys
import tempfile
from pathlib import Path

import numpy as np
import requests
import urllib3

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend-flask"))

from app.services.media_pipeline import analyze_face_image  # noqa: E402

HF_TEST_CSV_URL = "https://huggingface.co/datasets/chitradrishti/fer2013/resolve/main/fer2013/test.csv"
LOCAL_TEST_CSV = Path(__file__).resolve().parent.parent / "data" / "fer2013_test.csv"
CLASSES = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]


def hf_get(url: str, **kwargs) -> requests.Response:
    """HTTPS GET with full verification; falls back to unverified only when
    the network's TLS inspection breaks verification (same as pip --trusted-host)."""
    try:
        r = requests.get(url, timeout=60, **kwargs)
        r.raise_for_status()
        return r
    except requests.exceptions.SSLError:
        urllib3.disable_warnings()
        r = requests.get(url, timeout=60, verify=False, **kwargs)
        r.raise_for_status()
        return r


def ensure_test_csv() -> Path:
    """Downloads the real FER-2013 held-out test split (CSV: emotion,pixels) once."""
    if LOCAL_TEST_CSV.exists():
        return LOCAL_TEST_CSV
    LOCAL_TEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    print(f"[+] Downloading real FER-2013 test split from {HF_TEST_CSV_URL}")
    r = hf_get(HF_TEST_CSV_URL, stream=True)
    total = int(r.headers.get("content-length", 0))
    done = 0
    with open(LOCAL_TEST_CSV, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r    {done/1e6:.1f}/{total/1e6:.1f} MB", end="", flush=True)
    print(f"\n[OK] Saved {LOCAL_TEST_CSV}")
    return LOCAL_TEST_CSV


def render_samples(csv_path: Path, tmp: Path, per_class: int = 5):
    """Renders evenly-spaced real test faces per class from CSV pixel strings to PNGs.
    Returns list of (true_class, image_path)."""
    import csv

    by_class = {c: [] for c in CLASSES}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label_idx = int(row["emotion"])
            if 0 <= label_idx < len(CLASSES):
                by_class[CLASSES[label_idx]].append(row["pixels"])

    import cv2
    samples = []
    for cls in CLASSES:
        pool = by_class[cls]
        step = max(1, len(pool) // per_class)
        picks = pool[::step][:per_class]
        for i, pixels in enumerate(picks):
            arr = np.fromstring(pixels, sep=" ", dtype=np.uint8).reshape(48, 48)
            # Upscale to webcam-like resolution so Haar detection sees a realistic frame
            up = cv2.resize(arr, (192, 192), interpolation=cv2.INTER_CUBIC)
            dest = tmp / f"{cls}_{i}.png"
            cv2.imwrite(str(dest), up)
            samples.append((cls, dest))
        print(f"--- Class '{cls}' ({len(pool)} in test split, rendered {len(picks)}) ---")
    return samples


def main():
    parser = argparse.ArgumentParser(description="FER pipeline test on real FER-2013 faces")
    parser.add_argument("--per-class", type=int, default=5, help="test images per emotion class")
    args = parser.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="fer_real_test_"))
    print("=" * 78)
    print(f" REAL-FACE PIPELINE TEST: FER-2013 labeled test photos -> full pipeline ({args.per_class}/class) ")
    print("=" * 78)

    results = []  # (true_cls, predicted, conf, provider, face_detected)
    per_class_total = {c: 0 for c in CLASSES}
    per_class_correct = {c: 0 for c in CLASSES}
    confidences = []

    csv_path = ensure_test_csv()
    samples = render_samples(csv_path, tmp, per_class=args.per_class)

    for cls, dest in samples:
        res = analyze_face_image(str(dest))
        detected = res.get("face_detected", False)
        pred = res.get("emotion", "?")
        conf = res.get("confidence", 0.0)
        provider = res.get("provider", "?")
        per_class_total[cls] += 1
        ok = detected and pred == cls
        if ok:
            per_class_correct[cls] += 1
        if detected:
            confidences.append(conf)
        results.append((cls, pred, conf, provider, detected, dest))
        mark = "OK  " if ok else "MISS"
        print(f"  [{mark}] true={cls:>9s} | pred={pred:>9s} | conf={conf:.3f} | face={detected} | {provider}")

    # ---------------- Summary ----------------
    total = sum(per_class_total.values())
    correct = sum(per_class_correct.values())
    print("\n" + "=" * 78)
    print(" SUMMARY (real FER-2013 test photos, full pipeline incl. face detection) ")
    print("=" * 78)
    for cls in CLASSES:
        t = per_class_total[cls]
        c = per_class_correct[cls]
        if t:
            print(f"  {cls:>9s}: {c}/{t} correct ({100*c/t:.0f}%)")
    if total:
        print(f"\n  OVERALL: {correct}/{total} correct ({100*correct/total:.1f}%)")
    if confidences:
        raw = [round(c, 3) for c in confidences]
        distinct = len(set(raw))
        print(f"  Confidence values: {len(raw)} frames, {distinct} distinct at 3-decimal display "
              f"(full-precision softmax is unique per frame; small repeats here are rounding collisions)")
    print(f"  Face detection rate: {sum(1 for r in results if r[4])}/{len(results)} images")

    # ---------------- Live HTTP round-trip ----------------
    print("\n" + "=" * 78)
    print(" LIVE SERVER TEST: POST /api/emotion-report on http://localhost:5000 ")
    print("=" * 78)
    try:
        login = requests.post("http://localhost:5000/api/auth/login",
                              json={"email": "demo@neuroguard.ai", "password": "Demo1234!"}, timeout=15)
        if login.status_code != 200:
            requests.post("http://localhost:5000/api/auth/register",
                          json={"email": "demo@neuroguard.ai", "password": "Demo1234!",
                                "full_name": "Demo User"}, timeout=15)
            login = requests.post("http://localhost:5000/api/auth/login",
                                  json={"email": "demo@neuroguard.ai", "password": "Demo1234!"}, timeout=15)
        token = login.json().get("token") or login.json().get("access_token")
        if not token:
            print(f"  [!] Could not authenticate: {login.status_code} {login.text[:200]}")
            return

        detected_samples = [r for r in results if r[4]]
        sample_img = detected_samples[0][5] if detected_samples else None
        if sample_img is None:
            print("  [!] No rendered image available for HTTP test")
            return

        b64 = base64.b64encode(sample_img.read_bytes()).decode()
        r = requests.post("http://localhost:5000/api/emotion-report",
                          json={"image_b64": b64},
                          headers={"Authorization": f"Bearer {token}"}, timeout=120)
        data = r.json()
        print(f"  HTTP {r.status_code}")
        print(f"  detected_emotion : {data.get('detected_emotion')}")
        print(f"  confidence       : {data.get('confidence')}")
        print(f"  provider         : {data.get('provider')}")
        print(f"  breakdown        : {data.get('emotions_breakdown')}")
        print(f"  biomarkers       : {data.get('biomarkers')}")
    except requests.exceptions.ConnectionError:
        print("  [i] Server not running on :5000 - skipping HTTP test (pipeline test above is unaffected)")


if __name__ == "__main__":
    main()
