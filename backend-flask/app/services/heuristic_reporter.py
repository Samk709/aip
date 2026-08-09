def generate_offline_report(emotion: str) -> str:
    """
    Generates a high-quality, clinical-style problem/solution report
    based entirely on local heuristics (no external API required).
    """
    emotion = emotion.lower()
    
    reports = {
        "sad": {
            "problems": (
                "- Micro-expressions indicate prolonged cognitive load and potential depressive affect.\n"
                "- Downward lip stretching and reduced ocular movement suggest low physical energy."
            ),
            "solutions": (
                "- Behavioral Activation: Schedule one small, easily achievable task today (e.g. a 5-minute walk).\n"
                "- Connect: Reach out to a trusted friend or use the emergency contacts if feelings worsen."
            )
        },
        "anxious": {
            "problems": (
                "- Elevated muscle tension around the jaw and eyes indicates high physiological stress.\n"
                "- Rapid micro-movements suggest an activated sympathetic nervous system (fight-or-flight)."
            ),
            "solutions": (
                "- Box Breathing: Inhale for 4s, hold for 4s, exhale for 4s, hold for 4s. Repeat 5 times.\n"
                "- 5-4-3-2-1 Grounding: Identify 5 things you see, 4 you feel, and 3 you hear to break the anxiety loop."
            )
        },
        "happy": {
            "problems": (
                "- No acute distress markers detected.\n"
                "- Facial muscles indicate baseline stable or positive affective state."
            ),
            "solutions": (
                "- Maintenance: Continue current positive coping mechanisms and daily routines.\n"
                "- Resilience Building: Use this high-energy state to plan ahead or engage in a new hobby."
            )
        },
        "neutral": {
            "problems": (
                "- Affect is currently flat; no strong emotional valence detected.\n"
                "- Could indicate baseline stability, or potential emotional blunting/fatigue depending on context."
            ),
            "solutions": (
                "- Mindfulness: Do a quick internal sweep. Are you feeling numb, or simply relaxed?\n"
                "- Routine check-in: Log your mood daily to establish a more accurate long-term baseline."
            )
        },
        "fear": {
            "problems": (
                "- Widened eyes and tightened mouth indicate acute trigger response.\n"
                "- High likelihood of adrenaline spike and potential panic onset."
            ),
            "solutions": (
                "- Grounding: Immediately wash your face with cold water to trigger the mammalian dive reflex.\n"
                "- Safety check: Remind yourself 'I am safe in this exact moment.' Focus entirely on your physical surroundings."
            )
        }
    }
    
    # Map raw emotions if necessary, otherwise fallback to neutral
    if emotion not in reports:
        if "stress" in emotion or "panic" in emotion:
            emotion = "anxious"
        elif "anger" in emotion:
            emotion = "anxious"  # grouping high arousal
        else:
            emotion = "neutral"
            
    data = reports[emotion]
    
    return f"PROBLEMS:\n{data['problems']}\n\nSOLUTIONS:\n{data['solutions']}"
