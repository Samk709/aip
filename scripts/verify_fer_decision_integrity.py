"""
FER Decision Integrity Verifier
-------------------------------
Proves (or disproves) that the live emotion result is driven by the trained
MiniXception CNN's softmax output rather than deterministic rule overrides.

Part A (static): scans media_pipeline.py for forbidden decision patterns
(rule-based class priors, weighted fusion, hardcoded confidence constants).

Part B (dynamic): runs predict_face_emotion_cnn on 6+ distinctly different
expression inputs (one prototype per class + webcam-simulated variants) and
prints the RAW softmax breakdown for each. Confidences must be live per-frame
values — no two runs should collapse to identical fixed numbers.

Run from repo root:
    backend-flask/.venv/Scripts/python.exe scripts/verify_fer_decision_integrity.py
"""

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend-flask"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from app.services.media_models import predict_face_emotion_cnn, EMOTION_CLASSES  # noqa: E402
from train_fer_cnn import generate_benchmark_fer_dataset, augment_webcam_frame  # noqa: E402

PIPELINE_FILE = REPO_ROOT / "backend-flask" / "app" / "services" / "media_pipeline.py"

FORBIDDEN_PATTERNS = [
    "landmark_priors",
    "fused_probas",
    "0.85 * landmark",
    "0.15 * cnn",
    "priors[",
    "hybrid-landmark-cnn",
]


def static_check() -> bool:
    src = PIPELINE_FILE.read_text(encoding="utf-8")
    print("=" * 72)
    print(" PART A: Static scan of media_pipeline.py for rule-override patterns ")
    print("=" * 72)
    ok = True
    for pat in FORBIDDEN_PATTERNS:
        hit = pat in src
        status = "FAIL (found)" if hit else "PASS (absent)"
        print(f"  [{status}] '{pat}'")
        ok = ok and not hit
    print(f"\n  Static result: {'PASS - no rule-override patterns present' if ok else 'FAIL - rule patterns remain'}\n")
    return ok


def dynamic_check() -> bool:
    print("=" * 72)
    print(" PART B: Live CNN softmax on distinct expression inputs ")
    print("=" * 72)

    # One prototype per class (indices ordered to hit all 7 classes), then
    # rendered as uint8 images like a real cropped webcam face ROI.
    X, y = generate_benchmark_fer_dataset(n_samples=7)
    raw_confidences = []
    run_id = 0

    def run_case(tag: str, img01: np.ndarray) -> float:
        nonlocal run_id
        run_id += 1
        img_u8 = (np.clip(img01, 0.0, 1.0) * 255.0).round().astype(np.uint8)
        res = predict_face_emotion_cnn(img_u8)
        breakdown = res["emotions_breakdown"]
        # Full-precision top-class probability straight from the softmax tensor
        raw_top = float(max(res["raw_probabilities"]))
        print(f"\n  [{run_id}] {tag}")
        print(f"      predicted={res['emotion']:>9s}  raw_top_prob={raw_top:.6f}  provider={res['provider']}")
        print("      softmax: " + "  ".join(f"{c}={breakdown[c]:.4f}" for c in EMOTION_CLASSES))
        raw_confidences.append(raw_top)
        return raw_top

    np.random.seed(7)
    # 7 clean prototypes (one per class)
    for i in range(7):
        run_case(f"clean prototype '{EMOTION_CLASSES[i]}'", X[i, 0])

    # 4 webcam-simulated variants of different classes (domain-shift conditions)
    for i, cls_idx in enumerate([3, 0, 5, 4]):  # happy, angry, surprise, sad
        run_case(f"webcam-shifted variant of '{EMOTION_CLASSES[cls_idx]}'",
                 augment_webcam_frame(X[cls_idx, 0]))

    distinct = len(set(raw_confidences))
    print("\n" + "-" * 72)
    print(f"  Runs: {len(raw_confidences)} | Distinct raw top-probabilities (full precision): {distinct}")
    ok = distinct == len(raw_confidences)
    print(f"  Dynamic result: {'PASS - every frame produced a unique live softmax value' if ok else 'FAIL - identical values across different inputs'}")
    print("  Note: values clustering near 1.0 indicate SOFTMAX SATURATION, which is")
    print("  expected while the model is trained on the trivially separable synthetic")
    print("  generator. Train on real FER-2013 data (--csv) for calibrated distributions.")
    print("-" * 72)
    return ok


if __name__ == "__main__":
    a = static_check()
    b = dynamic_check()
    print("\n" + "=" * 72)
    print(f" OVERALL: {'PASS' if (a and b) else 'FAIL'}")
    print("=" * 72)
    sys.exit(0 if (a and b) else 1)
