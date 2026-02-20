def predict_depression_severity(text: str, phq_score: int | None = None) -> dict:
    # Local fallback inference path (replace with real BERT service/model server in production).
    if phq_score is not None:
        if phq_score <= 4:
            return {"label": "No symptoms", "confidence": 0.84}
        if phq_score <= 9:
            return {"label": "Mild", "confidence": 0.79}
        return {"label": "Moderate/Severe", "confidence": 0.82}

    t = text.lower()
    high_terms = ["hopeless", "suicide", "can't go on", "worthless", "panic", "depressed"]
    mild_terms = ["sad", "tired", "stressed", "anxious", "overwhelmed"]

    if any(k in t for k in high_terms):
        return {"label": "Moderate/Severe", "confidence": 0.72}
    if any(k in t for k in mild_terms):
        return {"label": "Mild", "confidence": 0.68}
    return {"label": "No symptoms", "confidence": 0.63}
