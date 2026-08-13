"""
Webcam Self-Labeling Capture Tool
---------------------------------
Opens your webcam so YOU can build a domain-matched fine-tuning dataset:
see yourself making an expression, press a number key to save the frame
with that label. Saved to data/webcam_labeled/<class>/.

Controls:
    0=angry  1=disgust  2=fear  3=happy  4=sad  5=surprise  6=neutral
    q or ESC = stop

Target: 200-500 frames total, roughly balanced across the 7 classes.
More clear, frontal, well-lit frames = better fine-tuning.

Usage:
    backend-flask/.venv/Scripts/python.exe scripts/capture_webcam_labels.py
"""

import time
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = REPO_ROOT / "data" / "webcam_labeled"

LABELS = {
    ord("0"): "angry",
    ord("1"): "disgust",
    ord("2"): "fear",
    ord("3"): "happy",
    ord("4"): "sad",
    ord("5"): "surprise",
    ord("6"): "neutral",
}


def main():
    for cls in LABELS.values():
        (OUT_ROOT / cls).mkdir(parents=True, exist_ok=True)

    counts = {cls: len(list((OUT_ROOT / cls).glob("*.png"))) for cls in LABELS.values()}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[!] Cannot open webcam. Close other apps using the camera and retry.")
        return

    print("[+] Capture started. Press 0-6 to label & save the current frame, Q/ESC to stop.")
    print(f"[+] Current dataset: {counts}")

    window = "NeuroGuard FER Label Capture  |  0=angry 1=disgust 2=fear 3=happy 4=sad 5=surprise 6=neutral  |  Q=quit"

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[!] Webcam frame read failed; stopping.")
            break

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 44), (20, 20, 20), -1)
        text = " | ".join(f"{cls}:{counts[cls]}" for cls in LABELS.values())
        cv2.putText(overlay, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 242, 254), 2)
        cv2.imshow(window, overlay)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q"), 27):
            break
        if key in LABELS:
            cls = LABELS[key]
            counts[cls] += 1
            dest = OUT_ROOT / cls / f"frame_{int(time.time() * 1000)}.png"
            cv2.imwrite(str(dest), frame)
            print(f"    [captured] {cls}  (total for class: {counts[cls]})")

    cap.release()
    cv2.destroyAllWindows()

    print("\n[+] Final dataset counts:")
    for cls, n in counts.items():
        print(f"    {cls:>9s}: {n}")
    total = sum(counts.values())
    print(f"[+] Total: {total} labeled frames in {OUT_ROOT}")
    if total >= 100:
        print("[+] Enough data to fine-tune. Run:")
        print("    backend-flask/.venv/Scripts/python.exe scripts/finetune_vit_webcam.py")


if __name__ == "__main__":
    main()
