"""
Fine-tune the pretrained ViT FER model on YOUR self-labeled webcam frames
----------------------------------------------------------------------------
Input : data/webcam_labeled/<class>/*.png  (create with capture_webcam_labels.py)
Output: models/vit-face-expression-finetuned/
        The inference pipeline automatically prefers this directory once it exists.

This addresses the real domain shift: FER-2013 studio photos vs. your actual
webcam, lighting, face, and expression style. Even 200-500 labeled frames
meaningfully adapt the model.

Usage:
    backend-flask/.venv/Scripts/python.exe scripts/finetune_vit_webcam.py
"""

import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend-flask"))

from app.services.media_models import EMOTION_CLASSES  # noqa: E402

DATA_ROOT = REPO_ROOT / "data" / "webcam_labeled"
BASE_MODEL_DIR = REPO_ROOT / "models" / "vit-face-expression"
OUT_DIR = REPO_ROOT / "models" / "vit-face-expression-finetuned"
EPOCHS = 6
LR = 2e-5
BATCH = 16


def augment_frame(img: np.ndarray) -> np.ndarray:
    """Light RGB augmentation for webcam frames: flip, rotation, lighting jitter."""
    import cv2

    out = img.copy()
    h, w = out.shape[:2]
    if np.random.rand() < 0.5:
        out = out[:, ::-1, :].copy()
    angle = np.random.uniform(-10, 10)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    out = cv2.warpAffine(out, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    alpha = np.random.uniform(0.85, 1.15)
    beta = np.random.uniform(-12, 12)
    out = np.clip(out.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)
    return out


class WebcamFERDataset(Dataset):
    def __init__(self, entries, augment=False):
        self.entries = entries  # (path, label_idx)
        self.augment = augment

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, idx):
        import cv2
        path, label = self.entries[idx]
        img = cv2.imread(str(path))  # BGR
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (224, 224))
        if self.augment:
            img = augment_frame(img)
        x = img.astype(np.float32) / 255.0
        x = (x - 0.5) / 0.5
        return torch.from_numpy(x.transpose(2, 0, 1)), torch.tensor(label)


def load_entries():
    entries = []
    for idx, cls in enumerate(EMOTION_CLASSES):
        files = sorted((DATA_ROOT / cls).glob("*.png")) + sorted((DATA_ROOT / cls).glob("*.jpg"))
        if len(files) < 2:
            print(f"[!] Class '{cls}' has only {len(files)} samples (need >= 2 for a train/val split)")
        for f in files:
            entries.append((f, idx))
    return entries


def main():
    if not DATA_ROOT.exists():
        print(f"[!] No labeled data found at {DATA_ROOT}. Run scripts/capture_webcam_labels.py first.")
        return

    entries = load_entries()
    if len(entries) < 20:
        print(f"[!] Only {len(entries)} labeled frames found. Capture more with scripts/capture_webcam_labels.py.")
        return
    print(f"[+] Loaded {len(entries)} labeled webcam frames across {len(EMOTION_CLASSES)} classes")

    # Stratified 80/20 split
    rng = np.random.default_rng(42)
    train_entries, val_entries = [], []
    for idx, cls in enumerate(EMOTION_CLASSES):
        cls_files = [e for e in entries if e[1] == idx]
        rng.shuffle(cls_files)
        split = max(1, int(len(cls_files) * 0.8))
        train_entries.extend(cls_files[:split])
        val_entries.extend(cls_files[split:])
    print(f"[+] Train: {len(train_entries)} | Val: {len(val_entries)}")

    from transformers import ViTForImageClassification

    model = ViTForImageClassification.from_pretrained(str(BASE_MODEL_DIR))
    train_loader = DataLoader(WebcamFERDataset(train_entries, augment=True), batch_size=BATCH, shuffle=True)
    val_loader = DataLoader(WebcamFERDataset(val_entries, augment=False), batch_size=BATCH, shuffle=False)

    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-5)
    criterion = nn.CrossEntropyLoss()

    model.train()
    for epoch in range(1, EPOCHS + 1):
        total = 0.0
        for b_x, b_y in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(pixel_values=b_x).logits, b_y)
            loss.backward()
            optimizer.step()
            total += loss.item()
        print(f"[+] Epoch {epoch:02d}/{EPOCHS} - loss {total / len(train_loader):.4f}")

    # Evaluation on held-out webcam frames
    model.eval()
    y_true, y_pred = [], []
    with torch.no_grad():
        for b_x, b_y in val_loader:
            preds = torch.argmax(model(pixel_values=b_x).logits, dim=1)
            y_true.extend(b_y.numpy())
            y_pred.extend(preds.numpy())

    from sklearn.metrics import classification_report, accuracy_score

    y_true, y_pred = np.array(y_true), np.array(y_pred)
    present = sorted(set(y_true.tolist()))
    print(f"\n[OK] Webcam held-out accuracy: {accuracy_score(y_true, y_pred) * 100:.1f}%")
    print(classification_report(y_true, y_pred, labels=present,
                                target_names=[EMOTION_CLASSES[i] for i in present], zero_division=0))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(OUT_DIR))
    print(f"[OK] Saved fine-tuned model to {OUT_DIR}")
    print("[i] Restart the Flask app - the pipeline will now prefer the fine-tuned model.")


if __name__ == "__main__":
    main()
