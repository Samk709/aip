from importlib.util import find_spec
from pathlib import Path
from typing import Any


def _load_joblib_model(model_path: str):
    if find_spec("joblib") is None:
        return None
    import joblib
    p = Path(model_path)
    if not p.exists():
        return None
    return joblib.load(p)


def predict_face_emotion_from_embedding(model_path: str, features: list[float]) -> dict[str, Any]:
    model = _load_joblib_model(model_path)
    if model is None:
        return {"provider": "fallback", "emotion": "neutral", "note": "trained FER model missing"}

    pred = model.predict([features])[0]
    proba = max(model.predict_proba([features])[0]) if hasattr(model, "predict_proba") else 0.7
    return {"provider": "trained-fer", "emotion": str(pred), "confidence": float(round(proba, 3))}


def predict_voice_stress_from_features(model_path: str, features: list[float]) -> dict[str, Any]:
    model = _load_joblib_model(model_path)
    if model is None:
        return {"provider": "fallback", "stress": 0.5, "note": "trained SER model missing"}

    stress = float(model.predict([features])[0])
    stress = max(0.0, min(1.0, stress))
    return {"provider": "trained-ser", "stress": round(stress, 3)}
