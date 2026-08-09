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
        return {"provider": "fallback", "emotion": "neutral", "confidence": 0.5, "note": "trained FER model missing"}

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
        confidence = 0.85
        emotions_proba = {str(pred): confidence}

    return {
        "provider": "trained-fer-joblib",
        "emotion": str(pred),
        "confidence": confidence,
        "emotions_breakdown": emotions_proba
    }


def predict_voice_stress_from_features(model_path: str, features: list[float]) -> dict[str, Any]:
    model = _load_joblib_model(model_path)
    if model is None:
        return {"provider": "fallback", "stress": 0.5, "note": "trained SER model missing"}

    stress = float(model.predict([features])[0])
    stress = max(0.0, min(1.0, stress))
    return {"provider": "trained-ser", "stress": round(stress, 3)}
