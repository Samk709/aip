import json

def update_trend(last_mood: int | None, new_mood: int) -> str:
    if last_mood is None:
        return "stable"
    if new_mood - last_mood >= 2:
        return "improving"
    if last_mood - new_mood >= 2:
        return "worsening"
    return "stable"

def extract_and_update_twin_profile(text: str, current_triggers_json: str | None) -> str:
    """
    Very basic heuristic extraction of triggers from text to update the digital twin.
    In a full production scenario, we'd pass this to an LLM for extraction.
    """
    try:
        triggers = json.loads(current_triggers_json) if current_triggers_json else []
    except json.JSONDecodeError:
        triggers = []

    text_lower = text.lower()
    potential_triggers = ["work", "exam", "sleep", "relationship", "money", "family", "school", "health"]
    
    for pt in potential_triggers:
        if pt in text_lower and pt not in triggers:
            triggers.append(pt)
            
    # keep only latest 10
    triggers = triggers[-10:]
    return json.dumps(triggers)

