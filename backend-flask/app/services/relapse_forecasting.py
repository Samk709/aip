from datetime import datetime, timedelta

def predict_relapse(mood_history: list[int], sleep_patterns: list[int], recent_stresses: list[int]) -> tuple[float, list[str]]:
    """
    Mental Health Relapse Forecasting Model
    Predicts probability (0.0 to 1.0) of a depression/anxiety relapse in the next 2-4 weeks.
    
    Inputs:
    - mood_history: list of recent mood scores (0-10, lower is worse)
    - sleep_patterns: list of recent sleep quality scores (1-10)
    - recent_stresses: list of recent stress scores (0-100)
    
    Returns: (probability, list_of_factors)
    """
    factors = []
    risk_score = 0.0
    
    # Needs at least a few days of data to make a reasonable prediction
    if len(mood_history) < 3 or len(sleep_patterns) < 3:
        return 0.1, ["Insufficient data for forecasting"]

    # 1. Analyze Mood Trend (Negative trajectory)
    recent_moods = mood_history[-5:] # look at last 5
    if len(recent_moods) > 1:
        mood_slope = recent_moods[-1] - recent_moods[0]
        if mood_slope < -2:
            risk_score += 0.35
            factors.append("Sharp decline in recent mood trajectory")
        elif mood_slope < 0:
            risk_score += 0.15
            factors.append("Gradual decline in mood")

    # 2. Analyze Sleep Pattern (Poor sleep is a massive relapse predictor)
    avg_sleep = sum(sleep_patterns[-5:]) / len(sleep_patterns[-5:])
    if avg_sleep <= 4:
        risk_score += 0.40
        factors.append("Severe sleep disruption detected")
    elif avg_sleep <= 6:
        risk_score += 0.20
        factors.append("Suboptimal sleep quality")

    # 3. Accumulated Stress
    if recent_stresses and sum(recent_stresses[-3:]) / len(recent_stresses[-3:]) > 70:
        risk_score += 0.25
        factors.append("Prolonged high stress levels")

    # Cap risk at 0.95 (never 100% certain)
    final_prob = min(0.95, risk_score)
    
    if final_prob > 0.65:
        factors.append("High likelihood of relapse within 14-28 days")

    return final_prob, factors
