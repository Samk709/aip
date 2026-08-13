import traceback
import numpy as np
from importlib.util import find_spec
from pathlib import Path
from typing import Any


def _load_joblib_model(model_path: str):
    if find_spec("joblib") is None or not model_path:
        return None
    import joblib
    p = Path(model_path)
    if not p.is_absolute():
        # Resolve relative to project root regardless of CWD
        base_dir = Path(__file__).resolve().parent.parent.parent
        p = base_dir / model_path
    if not p.exists():
        return None
    return joblib.load(p)


def predict_face_emotion_from_embedding(model_path: str, features: list[float]) -> dict[str, Any]:
    model = _load_joblib_model(model_path)
    if model is None:
        return {"provider": "fallback", "emotion": "neutral", "confidence": None, "note": "trained FER model missing; no prediction made"}

    # Pad or slice features to match 32-dim landmark feature schema
    feat_arr = list(features)
    if len(feat_arr) < 32:
        feat_arr = feat_arr + [0.5] * (32 - len(feat_arr))
    elif len(feat_arr) > 32:
        feat_arr = feat_arr[:32]

    pred = model.predict([feat_arr])[0]

    emotions_proba = {}
    if hasattr(model, "predict_proba") and hasattr(model, "classes_"):
        probas = model.predict_proba([feat_arr])[0]
        for cls_name, prob in zip(model.classes_, probas):
            emotions_proba[str(cls_name)] = round(float(prob), 3)
        confidence = float(round(max(probas), 3))
    else:
        # Model exposes no class probabilities — do NOT fabricate a fixed confidence.
        confidence = None

    result = {
        "provider": "trained-fer-joblib",
        "emotion": str(pred),
        "confidence": confidence,
        "emotions_breakdown": emotions_proba
    }
    if confidence is None:
        result["note"] = "Model does not expose class probabilities; confidence unavailable."
    return result


def predict_voice_stress_from_features(model_path: str, features: list[float]) -> dict[str, Any]:
    model = _load_joblib_model(model_path)
    if model is None:
        return {"provider": "fallback", "stress": 0.5, "note": "trained SER model missing"}

    stress = float(model.predict([features])[0])
    stress = max(0.0, min(1.0, stress))
    return {"provider": "trained-ser", "stress": round(stress, 3)}


# Global PyTorch MiniXception Model Cache
_FER_CNN_MODEL = None
_FER_VIT_MODEL = None
_FER_VIT_FAILED = False
EMOTION_CLASSES = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']


def _get_fer_vit_model():
    """
    Loads the pretrained ViT facial-expression model (trpakov/vit-face-expression,
    trained on REAL FER-2013 + AffectNet face photographs) from a local directory.
    Fully offline after the one-time download. Returns None if unavailable.
    """
    global _FER_VIT_MODEL, _FER_VIT_FAILED
    if _FER_VIT_MODEL is not None:
        return _FER_VIT_MODEL
    if _FER_VIT_FAILED:
        return None

    try:
        if find_spec("transformers") is None:
            _FER_VIT_FAILED = True
            return None
        from transformers import ViTForImageClassification

        base = Path(__file__).resolve()
        # Fine-tuned webcam model is preferred when present; pretrained model is the default.
        candidates = [
            base.parent.parent.parent / "models" / "vit-face-expression-finetuned",        # backend-flask/models/
            base.parent.parent.parent.parent / "models" / "vit-face-expression-finetuned", # repo-root models/
            Path("models/vit-face-expression-finetuned"),
            base.parent.parent.parent / "models" / "vit-face-expression",        # backend-flask/models/
            base.parent.parent.parent.parent / "models" / "vit-face-expression", # repo-root models/
            Path("models/vit-face-expression"),
        ]
        model_dir = next(
            (p for p in candidates if (p / "model.safetensors").exists() or (p / "pytorch_model.bin").exists()),
            None,
        )
        if model_dir is None:
            _FER_VIT_FAILED = True
            return None

        model = ViTForImageClassification.from_pretrained(str(model_dir))
        model.eval()
        _FER_VIT_MODEL = model
        print(f"[OK] Loaded pretrained ViT FER model (real FER-2013 + AffectNet photos) from {model_dir}")
        return _FER_VIT_MODEL
    except Exception:
        print(f"[!] Could not initialize ViT FER model:\n{traceback.format_exc()}")
        _FER_VIT_FAILED = True
        return None


def _get_fer_cnn_model():
    global _FER_CNN_MODEL
    if _FER_CNN_MODEL is not None:
        return _FER_CNN_MODEL

    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F

        class MiniXception(nn.Module):
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

        # Check weights location
        possible_paths = [
            Path(__file__).resolve().parent.parent.parent / "models" / "fer_cnn_model.pt",
            Path(__file__).resolve().parent.parent / "models" / "fer_cnn_model.pt",
            Path("models/fer_cnn_model.pt")
        ]
        
        weight_path = next((p for p in possible_paths if p.exists()), None)
        model = MiniXception(num_classes=7)
        
        if weight_path:
            model.load_state_dict(torch.load(weight_path, map_location=torch.device('cpu'), weights_only=True))
            print(f"[OK] Loaded PyTorch MiniXception CNN weights from {weight_path}")
        else:
            print("[!] CRITICAL ERROR: Could not find models/fer_cnn_model.pt!")
        
        model.eval()
        _FER_CNN_MODEL = model
        return _FER_CNN_MODEL
    except Exception as e:
        print(f"[!] CRITICAL ERROR initializing PyTorch FER CNN:\n{traceback.format_exc()}")
        return None


def predict_face_emotion_cnn(cropped_face_gray) -> dict[str, Any]:
    """
    Feeds a cropped grayscale face image into the best available TRAINED model and
    outputs live softmax confidence probabilities across the 7 emotion classes.

    Model priority:
    1. Pretrained ViT (trpakov/vit-face-expression) — trained on REAL FER-2013 +
       AffectNet face photographs. This is the primary decision-maker.
    2. Local MiniXception CNN — fallback only.
    """
    if cropped_face_gray is None or cropped_face_gray.size == 0:
        print("[!] ERROR: cropped face ROI is invalid in predict_face_emotion_cnn!")
        return {"provider": "fallback", "emotion": "uncertain", "confidence": 0.0, "emotions_breakdown": {c: 0.0 for c in EMOTION_CLASSES}}

    # --- Primary: pretrained ViT on real face photographs ---
    vit = _get_fer_vit_model()
    if vit is not None:
        try:
            import torch
            import cv2

            # Grayscale crop -> 224x224 RGB, normalized with the model's training stats
            if cropped_face_gray.ndim == 2:
                rgb = cv2.cvtColor(cropped_face_gray, cv2.COLOR_GRAY2RGB)
            else:
                rgb = cropped_face_gray[..., ::-1]  # BGR -> RGB
            resized = cv2.resize(rgb, (224, 224)).astype(np.float32) / 255.0
            norm = (resized - 0.5) / 0.5
            tensor_in = torch.from_numpy(norm.transpose(2, 0, 1)).unsqueeze(0)  # (1, 3, 224, 224)

            with torch.no_grad():
                logits = vit(pixel_values=tensor_in).logits[0]
                probas_all = torch.softmax(logits, dim=0).numpy()

            # Reorder the model's own label set into EMOTION_CLASSES order
            id2label = {int(k): str(v).lower() for k, v in vit.config.id2label.items()}
            label2idx = {v: k for k, v in id2label.items()}
            probas = np.array([probas_all[label2idx[c]] for c in EMOTION_CLASSES], dtype=np.float32)
            probas = probas / probas.sum()

            emotions_breakdown = {cls_name: round(float(prob), 3) for cls_name, prob in zip(EMOTION_CLASSES, probas)}
            max_idx = int(np.argmax(probas))
            max_conf = float(round(float(probas[max_idx]), 3))

            return {
                "provider": "vit-face-expression-pretrained",
                "emotion": EMOTION_CLASSES[max_idx],
                "confidence": max_conf,
                "emotions_breakdown": emotions_breakdown,
                "raw_probabilities": probas.tolist()
            }
        except Exception:
            print(f"[!] ViT FER inference failed; falling back to MiniXception:\n{traceback.format_exc()}")

    # --- Fallback: local MiniXception CNN ---
    model = _get_fer_cnn_model()
    if model is None:
        print("[!] ERROR: no trained FER model available in predict_face_emotion_cnn!")
        return {"provider": "fallback", "emotion": "uncertain", "confidence": 0.0, "emotions_breakdown": {c: 0.0 for c in EMOTION_CLASSES}}

    try:
        import torch
        import torch.nn.functional as F
        import cv2

        # Step 2: Preprocess 48x48 grayscale face crop with standard zero-centered normalization
        resized = cv2.resize(cropped_face_gray, (48, 48))
        norm_img = (resized.astype("float32") / 255.0 - 0.5) / 0.5
        tensor_in = torch.tensor(norm_img).unsqueeze(0).unsqueeze(0) # Shape: (1, 1, 48, 48)

        # Forward pass for real Softmax output
        with torch.no_grad():
            logits = model(tensor_in)
            probas = F.softmax(logits, dim=1)[0].numpy()

        emotions_breakdown = {cls_name: round(float(prob), 3) for cls_name, prob in zip(EMOTION_CLASSES, probas)}
        max_idx = int(np.argmax(probas))
        max_conf = float(round(float(probas[max_idx]), 3))

        return {
            "provider": "pytorch-minixception-cnn",
            "emotion": EMOTION_CLASSES[max_idx],
            "confidence": max_conf,
            "emotions_breakdown": emotions_breakdown,
            "raw_probabilities": probas.tolist()
        }
    except Exception as e:
        print(f"[!] CRITICAL ERROR in predict_face_emotion_cnn:\n{traceback.format_exc()}")
        return {"provider": "fallback", "emotion": "uncertain", "confidence": 0.0, "emotions_breakdown": {c: 0.0 for c in EMOTION_CLASSES}}


