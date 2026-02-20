def simple_sentiment(text: str) -> str:
    t = text.lower()
    negatives = ["sad", "depressed", "anxious", "panic", "bad", "hopeless", "stress"]
    positives = ["good", "better", "happy", "calm", "fine", "okay"]
    if any(k in t for k in negatives):
        return "negative"
    if any(k in t for k in positives):
        return "positive"
    return "neutral"
