def normalize_face_emotion(face_emotion: str) -> str:
    allowed = {"happy", "sad", "neutral"}
    e = (face_emotion or "neutral").lower().strip()
    return e if e in allowed else "neutral"


def estimate_voice_stress(voice_energy: float, voice_pitch_var: float) -> float:
    # 0 to 1 range stress proxy from basic audio features.
    raw = (0.5 * max(0.0, min(1.0, voice_energy)) + 0.5 * max(0.0, min(1.0, voice_pitch_var)))
    return round(raw, 3)


def fusion_distress_score(text_negative: float, face_emotion: str, voice_stress: float) -> float:
    face_penalty = 0.7 if face_emotion == "sad" else (0.3 if face_emotion == "neutral" else 0.1)
    score = (0.5 * text_negative) + (0.25 * face_penalty) + (0.25 * voice_stress)
    return round(max(0.0, min(1.0, score)), 3)
