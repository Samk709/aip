import requests


def query_rasa(rasa_webhook_url: str, sender_id: str, message: str) -> str | None:
    if not rasa_webhook_url:
        return None

    try:
        payload = {"sender": sender_id, "message": message}
        resp = requests.post(rasa_webhook_url, json=payload, timeout=6)
        if resp.status_code != 200:
            return None
        data = resp.json()
        texts = [item.get("text", "") for item in data if isinstance(item, dict) and item.get("text")]
        return " ".join(texts) if texts else None
    except requests.RequestException:
        return None
