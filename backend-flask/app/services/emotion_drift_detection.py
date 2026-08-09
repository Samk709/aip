def detect_emotion_drift(current_emotions: dict, baseline_emotions: dict) -> tuple[bool, str]:
    """
    Detects sudden spikes or significant changes in negative emotions compared to baseline.
    Returns (has_drift, alert_message).
    """
    if not current_emotions or not baseline_emotions:
        return False, ""
    
    # Calculate drift metrics
    sadness_jump = current_emotions.get("sadness", 0) - baseline_emotions.get("sadness", 0)
    fear_jump = current_emotions.get("fear", 0) - baseline_emotions.get("fear", 0)
    anger_jump = current_emotions.get("anger", 0) - baseline_emotions.get("anger", 0)
    
    # Threshold for a sudden negative emotional spike (e.g., > 40% jump)
    threshold = 0.40
    
    if sadness_jump > threshold and fear_jump > threshold:
        return True, "Critical multi-emotion drift detected (Sadness + Fear spike)."
    elif sadness_jump > threshold:
        return True, "Sudden severe depressive drift detected."
    elif fear_jump > threshold:
        return True, "Sudden severe anxiety/panic drift detected."
    elif anger_jump > threshold:
        return True, "Sudden severe agitation drift detected."
        
    return False, ""
