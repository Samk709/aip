"""
FER-2013 PyTorch MiniXception CNN Trainer & Evaluator
------------------------------------------------------
Trains a lightweight 48x48 grayscale CNN emotion classifier for real-time
CPU inference via Flask.

Data sources (in priority order):
1. Real FER-2013 CSV (Kaggle format: emotion,pixels,Usage) via --csv PATH,
   or auto-detected at data/fer2013.csv or fer2013.csv.
2. Synthetic procedural face generator (fallback when no real dataset is
   available). NOTE: synthetic-data metrics do NOT certify real-webcam
   accuracy — they only validate the training pipeline end-to-end.

Domain-shift handling:
- Webcam-simulation augmentation is applied ON THE FLY during training:
  random brightness/contrast jitter, gaussian blur, small rotations and
  translations, random shadow gradients, CLAHE relighting, sensor noise.
- Evaluation reports accuracy on BOTH a clean held-out test set and a
  webcam-simulated shifted test set, so the robustness gap is visible.

Emotions (7 Classes):
0: angry, 1: disgust, 2: fear, 3: happy, 4: sad, 5: surprise, 6: neutral
"""

import argparse
import os
import numpy as np
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

EMOTION_CLASSES = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']


class MiniXception(nn.Module):
    """
    Lightweight Deep Convolutional Neural Network (MiniXception architecture)
    optimized for 48x48 grayscale FER-2013 facial expression recognition.
    """
    def __init__(self, num_classes=7):
        super(MiniXception, self).__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(32)

        self.block1 = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.2)
        )
        self.block2 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Dropout2d(0.25)
        )
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(128, num_classes)

    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = self.block1(x)
        x = self.block2(x)
        x = self.gap(x)
        x = torch.flatten(x, 1)
        return self.fc(x)


# ---------------------------------------------------------------------------
# Webcam-simulation augmentation
# ---------------------------------------------------------------------------

def augment_webcam_frame(img01: np.ndarray) -> np.ndarray:
    """
    Simulates realistic webcam capture conditions on a float [0,1] 48x48 image:
    random rotation/translation, brightness/contrast jitter, gaussian blur,
    shadow gradient overlays, CLAHE relighting, and sensor noise.
    """
    import cv2

    img = img01.astype(np.float32).copy()

    # Small random rotation (+-12 deg) and translation (+-3 px)
    angle = np.random.uniform(-12.0, 12.0)
    dx = np.random.uniform(-3.0, 3.0)
    dy = np.random.uniform(-3.0, 3.0)
    M = cv2.getRotationMatrix2D((24, 24), angle, 1.0)
    M[0, 2] += dx
    M[1, 2] += dy
    img = cv2.warpAffine(img, M, (48, 48), borderMode=cv2.BORDER_REFLECT)

    # Brightness / contrast jitter (uneven room lighting, auto-exposure)
    alpha = np.random.uniform(0.80, 1.25)  # contrast
    beta = np.random.uniform(-0.15, 0.15)  # brightness
    img = img * alpha + beta

    # Occasional gaussian blur (defocus / motion / low-quality sensor)
    if np.random.rand() < 0.35:
        img = cv2.GaussianBlur(img, (3, 3), 0)

    # Occasional linear shadow gradient across the face (window-side lighting)
    if np.random.rand() < 0.30:
        direction = np.random.rand() < 0.5
        grad = np.linspace(0.0, np.random.uniform(0.10, 0.30), 48, dtype=np.float32)
        grad = grad[:, None] if direction else grad[None, :]
        if np.random.rand() < 0.5:
            grad = np.flip(grad, axis=0 if direction else 1)
        img = img - grad

    # Occasional CLAHE relighting (matches CLAHE preprocessing used at inference)
    if np.random.rand() < 0.50:
        img_u8 = np.clip(img, 0.0, 1.0)
        img_u8 = (img_u8 * 255.0).round().astype(np.uint8)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img = clahe.apply(img_u8).astype(np.float32) / 255.0

    # Sensor noise
    noise = np.random.normal(loc=0.0, scale=np.random.uniform(0.01, 0.05), size=(48, 48))
    img = img + noise.astype(np.float32)

    return np.clip(img, 0.0, 1.0)


class FERDataset(Dataset):
    """Holds raw [0,1] float images; normalizes to [-1,1] per item.
    Applies webcam-simulation augmentation on the fly when augment=True."""

    def __init__(self, X: np.ndarray, y: np.ndarray, augment: bool = False):
        self.X = X
        self.y = y
        self.augment = augment

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        img = self.X[idx, 0]  # (48, 48) in [0,1]
        if self.augment:
            img = augment_webcam_frame(img)
        norm = (img - 0.5) / 0.5
        return torch.from_numpy(norm[None, :, :].astype(np.float32)), torch.tensor(self.y[idx])


# ---------------------------------------------------------------------------
# Data loading: real FER-2013 CSV or synthetic fallback generator
# ---------------------------------------------------------------------------

def _rows_to_arrays(rows):
    """Converts CSV rows (emotion,pixels) into (X [0,1], y) arrays."""
    X, y = [], []
    for row in rows:
        try:
            label = int(row["emotion"])
            pixels = np.fromstring(row["pixels"], sep=" ", dtype=np.float32)
        except (KeyError, ValueError):
            continue
        if label < 0 or label >= 7 or pixels.size != 2304:
            continue
        X.append((pixels / 255.0).reshape(1, 48, 48))
        y.append(label)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


def load_fer2013_split(train_csv: str, val_csv: str = None):
    """
    Loads real FER-2013 CSVs in Kaggle format.
    - If rows carry a 'Usage' column, Kaggle's own Train/Test split is used.
    - Otherwise train_csv supplies training rows and val_csv (if given) supplies
      the held-out test rows.
    Returns (X_train, y_train, X_test, y_test) with X in [0,1], shape (N,1,48,48).
    """
    import csv

    with open(train_csv, "r", encoding="utf-8") as f:
        train_rows = list(csv.DictReader(f))

    if val_csv:
        # An explicit held-out file always wins over any in-file Usage column
        tr = train_rows
        with open(val_csv, "r", encoding="utf-8") as f:
            te = list(csv.DictReader(f))
    else:
        has_usage = bool(train_rows) and "Usage" in train_rows[0]
        if has_usage:
            tr = [r for r in train_rows if r.get("Usage", "Training") == "Training"]
            te = [r for r in train_rows if r.get("Usage") != "Training"]
        else:
            tr = train_rows
            rng = np.random.default_rng(42)
            idx = rng.permutation(len(tr))
            split = int(len(tr) * 0.9)
            te = [tr[i] for i in idx[split:]]
            tr = [tr[i] for i in idx[:split]]

    X_train, y_train = _rows_to_arrays(tr)
    X_test, y_test = _rows_to_arrays(te)
    return X_train, y_train, X_test, y_test


def load_fer2013_csv(csv_path: str):
    """Backwards-compatible wrapper for a single Kaggle-format CSV."""
    return load_fer2013_split(csv_path)


def create_realistic_face_base(bg_val=0.5):
    """
    Generates a realistic smooth 48x48 human face oval template with continuous gradients.
    Pixel values in [0,1].
    """
    y_grid, x_grid = np.ogrid[:48, :48]
    center_y, center_x = 24, 24

    # Face oval mask
    mask = ((x_grid - center_x)**2 / (18**2) + (y_grid - center_y)**2 / (22**2)) <= 1.0
    img = np.full((48, 48), bg_val, dtype=np.float32)

    # Smooth skin tone luminance
    img[mask] = 0.72 + np.random.uniform(-0.03, 0.03)

    # Eyes baseline (darker sockets)
    img[16:22, 12:20] = 0.35  # Left eye
    img[16:22, 28:36] = 0.35  # Right eye

    # Nose ridge
    img[20:30, 22:26] = 0.78

    # Mouth baseline
    img[34:38, 16:32] = 0.40
    return img


def generate_benchmark_fer_dataset(n_samples=10500):
    """
    Generates 48x48 grayscale pixel tensor representations simulating
    spatial FER-2013 facial expression features. Pixel values in [0,1].
    """
    X = []
    y = []
    samples_per_class = n_samples // 7

    for idx, label in enumerate(EMOTION_CLASSES):
        for _ in range(samples_per_class):
            bg_lum = np.random.uniform(0.1, 0.4)
            img = create_realistic_face_base(bg_val=bg_lum)

            # Synthesize class-specific spatial facial gradients on 48x48 grid
            if label == 'happy':
                # Curved upward smile arc & raised cheeks
                img[32:40, 14:34] = 0.85
                img[34:38, 18:30] = 0.25  # Inner mouth curve
                img[22:28, 10:38] += 0.10  # Cheek highlight
            elif label == 'surprise':
                # Deep open vertical mouth cavity & raised brows
                img[30:44, 18:30] = 0.10  # Large open cavity
                img[10:15, 10:38] = 0.25  # High brows
                img[14:24, 10:38] = 0.85  # Open eye sockets
            elif label == 'angry':
                # V-shaped brow furrow & tight thin mouth
                img[13:18, 14:34] = 0.15  # Low brow furrow
                img[15:19, 21:27] = 0.10  # Mid furrow
                img[35:37, 16:32] = 0.20  # Thin lips
            elif label == 'sad':
                # Downturned mouth corners & drooping eyes
                img[34:38, 16:32] = 0.75
                img[37:42, 14:34] = 0.20  # Lower frown shadow
                img[14:20, 12:36] -= 0.15  # Eyelid shadow
            elif label == 'fear':
                # Wide open eyes & tense elongated mouth
                img[12:22, 10:38] = 0.90  # Wide eyes
                img[16:20, 14:34] = 0.15  # Pupils
                img[33:41, 16:32] = 0.30  # Tense mouth
            elif label == 'disgust':
                # Scrunched nose & asymmetric lip raise
                img[22:30, 18:30] = 0.25  # Wrinkled nose
                img[31:37, 16:32] = 0.30
            else:  # neutral
                # Calm resting face
                img[34:37, 16:32] = 0.35  # Resting mouth line

            X.append(img[np.newaxis, :, :])
            y.append(idx)

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.int64)
    return X, y


def evaluate(model, loader):
    model.eval()
    y_true, y_preds = [], []
    with torch.no_grad():
        for b_x, b_y in loader:
            out = model(b_x)
            preds = torch.argmax(out, dim=1)
            y_true.extend(b_y.numpy())
            y_preds.extend(preds.numpy())
    return np.array(y_true), np.array(y_preds)


def train_and_evaluate(output_model_path="models/fer_cnn_model.pt",
                       report_path="docs/FER_2013_Evaluation_Report.md",
                       csv_path=None, train_csv=None, val_csv=None,
                       n_samples=10500, epochs=12, seed=42):
    print("=" * 60)
    print(" FER-2013 PyTorch MiniXception CNN Training & Evaluation ")
    print("=" * 60)

    np.random.seed(seed)
    torch.manual_seed(seed)

    # ---------------- Data ----------------
    if csv_path is None and train_csv is None:
        for candidate_train, candidate_val in (
            ("data/train.csv", "data/val.csv"),
            ("data/fer2013.csv", None),
            ("fer2013.csv", None),
        ):
            if Path(candidate_train).exists():
                train_csv = candidate_train
                val_csv = candidate_val if candidate_val and Path(candidate_val).exists() else None
                break

    if train_csv:
        print(f"[+] Loading REAL FER-2013 dataset from '{train_csv}'"
              + (f" + '{val_csv}'" if val_csv else ""))
        X_train, y_train, X_test, y_test = load_fer2013_split(train_csv, val_csv)
        data_source = f"real FER-2013 CSV ({train_csv})"
    elif csv_path:
        print(f"[+] Loading REAL FER-2013 dataset from '{csv_path}'")
        X_train, y_train, X_test, y_test = load_fer2013_csv(csv_path)
        data_source = f"real FER-2013 CSV ({csv_path})"
    else:
        print("[!] No FER-2013 CSV found (looked for data/fer2013.csv, fer2013.csv).")
        print("[!] Falling back to the SYNTHETIC procedural generator.")
        print("[!] Metrics below validate the pipeline, NOT real-webcam accuracy.")
        X, y = generate_benchmark_fer_dataset(n_samples=n_samples)
        # Stratified-ish 80/20 split: shuffle with fixed seed then split
        idx = np.arange(len(X))
        rng = np.random.default_rng(seed)
        rng.shuffle(idx)
        split = int(len(idx) * 0.8)
        X_train, y_train = X[idx[:split]], y[idx[:split]]
        X_test, y_test = X[idx[split:]], y[idx[split:]]
        data_source = f"synthetic procedural generator ({n_samples} samples)"

    print(f"[+] Data source: {data_source}")
    print(f"[+] Train: {len(y_train)} | Test: {len(y_test)}")

    train_ds = FERDataset(X_train, y_train, augment=True)   # webcam-simulation ON
    test_clean_ds = FERDataset(X_test, y_test, augment=False)
    test_shift_ds = FERDataset(X_test, y_test, augment=True)  # simulated webcam shift

    train_loader = DataLoader(train_ds, batch_size=64, shuffle=True)
    test_clean_loader = DataLoader(test_clean_ds, batch_size=64, shuffle=False)
    test_shift_loader = DataLoader(test_shift_ds, batch_size=64, shuffle=False)

    # ---------------- Train ----------------
    model = MiniXception(num_classes=7)

    # Class-balanced loss: FER-2013 is heavily skewed (disgust ~549 vs happy ~7215).
    # Without this the model collapses onto the majority class.
    class_counts = np.bincount(y_train, minlength=7).astype(np.float32)
    class_weights = torch.tensor(len(y_train) / (7.0 * np.maximum(class_counts, 1.0)))
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    optimizer = torch.optim.Adam(model.parameters(), lr=5e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    model.train()
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for b_x, b_y in train_loader:
            optimizer.zero_grad()
            out = model(b_x)
            loss = criterion(out, b_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()
        if epoch % 2 == 0:
            print(f"[+] Epoch {epoch:02d}/{epochs} - Loss: {total_loss/len(train_loader):.4f}")

    # ---------------- Evaluate (clean + webcam-shifted) ----------------
    y_true, y_preds = evaluate(model, test_clean_loader)
    acc = accuracy_score(y_true, y_preds)
    macro_f1 = f1_score(y_true, y_preds, average='macro')
    report = classification_report(y_true, y_preds, labels=list(range(7)), target_names=EMOTION_CLASSES, zero_division=0)
    cm = confusion_matrix(y_true, y_preds, labels=list(range(7)))

    y_true_s, y_preds_s = evaluate(model, test_shift_loader)
    acc_shift = accuracy_score(y_true_s, y_preds_s)
    macro_f1_shift = f1_score(y_true_s, y_preds_s, average='macro')
    report_shift = classification_report(y_true_s, y_preds_s, labels=list(range(7)), target_names=EMOTION_CLASSES, zero_division=0)

    print(f"\n[OK] CLEAN test set      -> Accuracy: {acc*100:.2f}% | Macro F1: {macro_f1:.4f}")
    print(f"[OK] WEBCAM-SHIFTED test -> Accuracy: {acc_shift*100:.2f}% | Macro F1: {macro_f1_shift:.4f}")
    print("\nClassification Report (clean test):\n", report)

    # ---------------- Save weights ----------------
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    torch.save(model.state_dict(), output_model_path)
    print(f"[OK] Saved trained PyTorch CNN weights to '{output_model_path}'")

    alt_output_path = "backend-flask/models/fer_cnn_model.pt"
    os.makedirs(os.path.dirname(alt_output_path), exist_ok=True)
    torch.save(model.state_dict(), alt_output_path)
    print(f"[OK] Saved trained PyTorch CNN weights to '{alt_output_path}'")

    # ---------------- Markdown report ----------------
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# FER-2013 CNN Model Evaluation & Benchmark Report\n\n")
        f.write("## Model Performance Summary\n\n")
        f.write("- **Architecture**: Lightweight MiniXception CNN (PyTorch)\n")
        f.write("- **Input Format**: 48x48 Grayscale Cropped Face Tensor `(1, 1, 48, 48)`\n")
        f.write("- **Classes (7)**: `angry`, `disgust`, `fear`, `happy`, `sad`, `surprise`, `neutral`\n")
        f.write(f"- **Training Data Source**: {data_source}\n")
        f.write("- **Training Augmentation**: webcam simulation (rotation/translation, brightness/contrast jitter, gaussian blur, shadow gradients, CLAHE relighting, sensor noise)\n")
        f.write(f"- **Clean Test Accuracy**: `{acc * 100:.2f}%` | Macro F1: `{macro_f1:.4f}`\n")
        f.write(f"- **Webcam-Shifted Test Accuracy**: `{acc_shift * 100:.2f}%` | Macro F1: `{macro_f1_shift:.4f}`\n\n")
        if data_source.startswith("synthetic"):
            f.write("> WARNING: trained on the synthetic procedural generator (no FER-2013 CSV found). "
                    "These metrics validate the training pipeline only and do NOT certify real-webcam accuracy. "
                    "Place `fer2013.csv` at `data/fer2013.csv` (or pass `--csv`) and retrain for meaningful metrics.\n\n")
        f.write("## Classification Report (clean held-out test)\n\n```text\n")
        f.write(report)
        f.write("\n```\n\n## Classification Report (webcam-shifted test)\n\n```text\n")
        f.write(report_shift)
        f.write("\n```\n\n## Confusion Matrix (clean held-out test)\n\n")
        f.write("| True \\ Pred | " + " | ".join(EMOTION_CLASSES) + " |\n")
        f.write("| --- | " + " | ".join(["---"] * 7) + " |\n")
        for idx, row in enumerate(cm):
            f.write(f"| **{EMOTION_CLASSES[idx]}** | " + " | ".join(str(c) for c in row) + " |\n")

    print(f"[OK] Saved evaluation report to '{report_path}'")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train MiniXception FER CNN")
    parser.add_argument("--csv", default=None, help="Path to a single FER-2013 CSV (Kaggle format)")
    parser.add_argument("--train-csv", default=None, help="Path to FER-2013 train CSV (emotion,pixels)")
    parser.add_argument("--val-csv", default=None, help="Path to FER-2013 val/test CSV (held-out)")
    parser.add_argument("--samples", type=int, default=10500, help="Synthetic sample count (fallback only)")
    parser.add_argument("--epochs", type=int, default=12)
    args = parser.parse_args()
    train_and_evaluate(csv_path=args.csv, train_csv=args.train_csv, val_csv=args.val_csv,
                       n_samples=args.samples, epochs=args.epochs)
