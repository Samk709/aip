def update_trend(last_mood: int | None, new_mood: int) -> str:
    if last_mood is None:
        return "stable"
    if new_mood - last_mood >= 2:
        return "improving"
    if last_mood - new_mood >= 2:
        return "worsening"
    return "stable"
