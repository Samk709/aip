import requests


CRISIS_TERMS = {
    "suicide", "kill myself", "end my life", "self-harm", "no reason to live", "hopeless"
}


def local_moderation_flags(text: str) -> dict:
    t = text.lower()
    matched = [k for k in CRISIS_TERMS if k in t]
    return {
        "is_crisis": bool(matched),
        "matched_terms": matched,
    }


def openai_moderation(api_key: str, text: str) -> dict:
    if not api_key:
        return {"provider": "none", "flagged": False}

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"input": text, "model": "omni-moderation-latest"}
    try:
        resp = requests.post("https://api.openai.com/v1/moderations", headers=headers, json=body, timeout=8)
        if resp.status_code != 200:
            return {"provider": "openai", "flagged": False, "error": f"status_{resp.status_code}"}
        data = resp.json()
        flagged = bool(data.get("results", [{}])[0].get("flagged", False))
        return {"provider": "openai", "flagged": flagged}
    except requests.RequestException:
        return {"provider": "openai", "flagged": False, "error": "request_failed"}
