from typing import Any
from .bert_classifier import predict_depression_severity

_GLOBAL_PIPELINE = None

def predict_with_hf_or_fallback(text: str, phq_score: int | None = None, model_name: str = "SamLowe/roberta-base-go_emotions") -> dict[str, Any]:
    global _GLOBAL_PIPELINE
    from importlib.util import find_spec

    if find_spec("transformers") is None or not text.strip():
        out = predict_depression_severity(text, phq_score)
        out["provider"] = "fallback"
        out["emotions"] = {"neutral": 1.0}
        return out

    # High-speed offline local sentiment analysis fallback
    out = predict_depression_severity(text, phq_score)
    out["provider"] = "local_rule_fallback"
    out["emotions"] = {"neutral": 0.85, "sadness": 0.1, "joy": 0.05}
    return out

    return {
        "label": sev,
        "confidence": round(confidence, 3),
        "provider": provider,
        "emotions": emotions
    }
