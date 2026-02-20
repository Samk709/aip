import requests


def query_gpt(api_key: str, model: str, user_message: str, risk_level: str) -> str | None:
    if not api_key:
        return None

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a safe mental wellbeing assistant. Never provide harmful advice. If risk is high, encourage emergency support.",
                },
                {
                    "role": "user",
                    "content": f"Risk level: {risk_level}. Message: {user_message}",
                },
            ],
            "temperature": 0.5,
        }
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError, TypeError):
        return None
