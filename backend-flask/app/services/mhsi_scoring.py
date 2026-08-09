def calculate_mhsi(suicide_score: int, stress_score: int, avg_mood: int, phq_severity: str) -> int:
    """
    AI Mental Health Safety Index (MHSI)
    A proprietary 0 - 100 score indicating overall mental safety at this exact moment.
    100 = Perfectly Safe / Stable
    0 = Critical Emergency
    """
    
    # 1. Start from perfect safety
    index = 100.0
    
    # 2. Suicide Risk Weight (Heavy deduction)
    # If suicide score is 100, deduct 80 points.
    suicide_deduction = (suicide_score / 100.0) * 80.0
    index -= suicide_deduction
    
    # 3. Stress Weight
    # If stress is 100, deduct 20 points
    stress_deduction = (stress_score / 100.0) * 20.0
    index -= stress_deduction
    
    # 4. Mood baseline buffer
    # If user has good mood (10), add back some resilience points (up to 10)
    resilience_bonus = (avg_mood / 10.0) * 10.0
    index += resilience_bonus
    
    # 5. Clinical Severity Floor / Ceilings
    if phq_severity == "Moderate/Severe" and index > 70:
        index = 70 # Cap max safety if clinically severe
    
    return max(0, min(100, int(index)))
