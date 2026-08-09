def normalize_face_emotion(face_emotion: str) -> str:
    allowed = {"happy", "sad", "neutral"}
    e = (face_emotion or "neutral").lower().strip()
    return e if e in allowed else "neutral"


def estimate_voice_stress(voice_energy: float, voice_pitch_var: float) -> float:
    # 0 to 1 range stress proxy from basic audio features.
    raw = (0.5 * max(0.0, min(1.0, voice_energy)) + 0.5 * max(0.0, min(1.0, voice_pitch_var)))
    return round(raw, 3)


def fusion_distress_score(text_negative: float, face_emotion: str, voice_stress: float, typing_speed_wpm: float = 0.0, prev_distress: float = 0.0) -> float:
    # --- Dynamic Weighting ---
    w_text, w_face, w_voice, w_type = 0.4, 0.2, 0.2, 0.2
    
    face_penalty = 0.7 if face_emotion == "sad" else (0.3 if face_emotion == "neutral" else 0.1)
    
    # Downweight face if neutral (could be poorly lit/not expressive), distribute to text/voice
    if face_emotion == "neutral":
        w_face -= 0.1
        w_text += 0.05
        w_voice += 0.05
        
    typing_stress = 0.0
    if typing_speed_wpm > 80:
        typing_stress = 0.4
    elif 0 < typing_speed_wpm < 15:
        typing_stress = 0.4
        
    current_score = (w_text * text_negative) + (w_face * face_penalty) + (w_voice * voice_stress) + (w_type * typing_stress)
    
    # --- EWMA Temporal Smoothing ---
    alpha = 0.6 # lower alpha = more smoothing
    if prev_distress > 0:
        smoothed_score = (alpha * current_score) + ((1.0 - alpha) * prev_distress)
    else:
        smoothed_score = current_score
        
    return round(max(0.0, min(1.0, smoothed_score)), 3)
