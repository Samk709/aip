from typing import Any
from .bert_classifier import predict_depression_severity


def predict_with_hf_or_fallback(text: str, phq_score: int | None = None, model_name: str = "distilbert-base-uncased") -> dict[str, Any]:
    # Prefer Hugging Face runtime if transformers is installed; otherwise fallback.
    from importlib.util import find_spec

    if find_spec("transformers") is None:
        out = predict_depression_severity(text, phq_score)
        out["provider"] = "fallback"
        return out

    from transformers import pipeline  # imported only when available

    clf = pipeline("sentiment-analysis", model=model_name)
    result = clf(text[:512])[0]

    # Map sentiment proxy to severity for starter production path.
    label = str(result.get("label", "POSITIVE")).upper()
    score = float(result.get("score", 0.5))

    if phq_score is not None:
        base = predict_depression_severity(text, phq_score)
        return {"label": base["label"], "confidence": max(base["confidence"], score), "provider": "hf+phq"}

    if label == "NEGATIVE" and score > 0.75:
        sev = "Moderate/Severe"
    elif label == "NEGATIVE":
        sev = "Mild"
    else:
        sev = "No symptoms"

    return {"label": sev, "confidence": round(score, 3), "provider": "hf"}
