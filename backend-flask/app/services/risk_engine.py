def phq_to_severity(phq_score: int) -> str:
    if phq_score <= 4:
        return "No symptoms"
    if phq_score <= 9:
        return "Mild"
    return "Moderate/Severe"


def calculate_multidimensional_risk(phq_score: int, severity: str, text: str = "", emotions: dict = None) -> tuple[int, int, int, str, bool]:
    """
    Returns: (suicide_score, stress_score, recovery_score, risk_level, emergency_alert)
    """
    if not emotions:
        emotions = {}

    # 1. Suicide Score
    suicide_base = 10
    if severity == "Moderate/Severe":
        suicide_base = 50
    elif severity == "Mild":
        suicide_base = 25
    
    sadness = emotions.get("sadness", 0.0) * 100
    fear = emotions.get("fear", 0.0) * 100
    suicide_score = min(100, int(suicide_base + (sadness * 0.4) + (fear * 0.2)))

    crisis_words = ["suicide", "kill", "die", "end it", "worthless", "give up", "hopeless", "can't take it anymore"]
    text_lower = text.lower()
    if any(cw in text_lower for cw in crisis_words):
        suicide_score = min(100, suicide_score + 40)

    # 2. Stress Score
    stress_base = emotions.get("anger", 0.0) * 50 + emotions.get("fear", 0.0) * 50
    stress_score = min(100, int(max(20, stress_base + (phq_score * 2))))

    # 3. Recovery Score
    joy = emotions.get("joy", 0.0) * 100
    recovery_base = 100 - suicide_score
    recovery_score = max(0, min(100, int((recovery_base * 0.7) + (joy * 0.3))))

    # Early Suicide Risk Prediction Model + Emergency Alert
    emergency_alert = False
    if suicide_score > 75 or stress_score > 90 or "kill" in text_lower or "suicide" in text_lower:
        risk_level = "High"
        emergency_alert = True
    elif suicide_score > 40 or stress_score > 60:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return suicide_score, stress_score, recovery_score, risk_level, emergency_alert
