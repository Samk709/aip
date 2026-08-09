import random

def generate_recommendations(risk_level: str, triggers_json: str, emotions: dict) -> list[dict]:
    """
    Returns personalized therapy recommendations based on risk, triggers, and emotions.
    """
    recommendations = []

    if risk_level == "High":
        recommendations.append({
            "type": "immediate_action",
            "title": "5-4-3-2-1 Grounding Technique",
            "description": "Notice 5 things you see, 4 you can touch, 3 you hear, 2 you smell, and 1 you taste.",
            "duration": "2 mins"
        })
        recommendations.append({
            "type": "professional_help",
            "title": "Speak to a Counselor",
            "description": "Please reach out to a professional or helpline immediately. You are not alone.",
            "duration": "N/A"
        })
        return recommendations

    # Emotion-based Strict Mapping (Feature 4)
    # If stressed -> breathing exercise
    if emotions.get("stress", 0) > 0.3 or emotions.get("anxiety", 0) > 0.3:
        recommendations.append({
            "type": "breathing",
            "title": "4-7-8 Breathing Exercise",
            "description": "Inhale 4s, hold 7s, exhale 8s. A proven technique to rapidly lower stress.",
            "duration": "3 mins",
            "link": "https://www.youtube.com/results?search_query=4-7-8+breathing"
        })
        
    # If sad -> motivational quotes & behavioral activation
    if emotions.get("sadness", 0) > 0.3 or emotions.get("depression", 0) > 0.3:
        recommendations.append({
            "type": "motivational",
            "title": "Daily Motivational Wisdom",
            "description": "\"Not until we are lost do we begin to understand ourselves.\" Take a tiny, positive step today.",
            "duration": "1 min"
        })
        recommendations.append({
            "type": "activation",
            "title": "Behavioral Activation: Short Walk",
            "description": "Step outside for just 5 minutes. Notice the temperature and take a deep breath.",
            "duration": "5-10 mins"
        })

    # If anxious/fearful -> meditation
    if emotions.get("fear", 0) > 0.3 or emotions.get("anxiety", 0) > 0.3:
        recommendations.append({
            "type": "meditation",
            "title": "Guided Anxiety Meditation",
            "description": "Follow a 5-minute guided meditation focusing on grounding and present-moment awareness.",
            "duration": "5 mins",
            "link": "https://www.youtube.com/results?search_query=anxiety+grounding+meditation"
        })

    # Additional Trigger-based CBT
    if "work" in triggers_json or "exam" in triggers_json:
        recommendations.append({
            "type": "cbt",
            "title": "CBT Micro-Therapy: Reframing",
            "description": "Identify one catastrophic thought you're having right now, and write down an alternative, more realistic outcome.",
            "duration": "5 mins"
        })

    # Default fallback
    if len(recommendations) < 2:
        recommendations.append({
            "type": "relaxation",
            "title": "Progressive Muscle Relaxation (PMR)",
            "description": "Tense and then slowly release each muscle group, starting from your toes and moving up.",
            "duration": "5 mins",
            "link": "https://www.youtube.com/results?search_query=progressive+muscle+relaxation"
        })

    # Remove duplicates and limit to 3
    unique_recs = []
    seen = set()
    for r in recommendations:
        if r["title"] not in seen:
            unique_recs.append(r)
            seen.add(r["title"])

    return unique_recs[:3] # Return top 3 recommendations
