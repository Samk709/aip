def phq_to_severity(phq_score: int) -> str:
    if phq_score <= 4:
        return "No symptoms"
    if phq_score <= 9:
        return "Mild"
    return "Moderate/Severe"


def severity_to_risk(severity: str) -> tuple[int, str]:
    mapping = {
        "No symptoms": (20, "Low"),
        "Mild": (55, "Medium"),
        "Moderate/Severe": (85, "High"),
    }
    return mapping.get(severity, (50, "Medium"))
