import re

def explain_risk(text: str, emotions: dict, phq_score: int, suicide_score: int) -> dict:
    """
    Generates an Explainable AI (XAI) payload breaking down why a user
    received their specific risk levels.
    """
    text_lower = text.lower()
    
    # Track flagged keywords
    negative_lexicon = ["worthless", "tired", "give up", "hopeless", "sad", "die", "kill", "alone", "anxious", "panic", "stress"]
    matched = [word for word in negative_lexicon if re.search(r'\b' + word + r'\b', text_lower)]
    
    # Identify Primary Emotion Driver
    dominant_emotion = "neutral"
    max_val = 0.0
    for emo, val in emotions.items():
        if val > max_val:
            max_val = val
            dominant_emotion = emo
            
    # XAI Logic Rules
    primary_driver = ""
    if suicide_score > 75:
        primary_driver = "High suicide risk flagged due to explicit crisis vocabulary and/or severe PHQ indications."
    elif phq_score > 15:
        primary_driver = f"Severe PHQ-9 score ({phq_score}) correlates heavily with clinical depression indicators."
    elif dominant_emotion in ["sadness", "fear", "anger"] and max_val > 0.5:
        primary_driver = f"Text analysis strongly detects profound {dominant_emotion} (confidence: {round(max_val*100, 1)}%)."
    else:
        primary_driver = "Routine mental state detected based on standard thresholds."
        
    return {
        "xai_status": "active",
        "primary_driver": primary_driver,
        "matched_keywords": matched,
        "emotion_pattern": f"Dominant Emotion: {dominant_emotion.upper()}",
        "metrics": {
            "phq_influence": f"{round((phq_score / 27) * 100, 1)}%",
            "suicide_risk_percentile": f"{suicide_score}%"
        }
    }
