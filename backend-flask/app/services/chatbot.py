from .sentiment import simple_sentiment


def generate_reply(message: str, language: str, risk_level: str) -> str:
    sentiment = simple_sentiment(message)

    if language == "hi":
        if risk_level == "High":
            return "मुझे लगता है कि आप कठिन समय से गुजर रहे हैं। कृपया तुरंत किसी भरोसेमंद व्यक्ति या हेल्पलाइन से संपर्क करें। चलिए 4-7-8 breathing exercise करते हैं।"
        if sentiment == "negative":
            return "मैं आपके साथ हूँ। क्या आप अभी अपनी भावना 1 से 10 के बीच बता सकते हैं? हम एक छोटी breathing exercise कर सकते हैं।"
        return "बहुत अच्छा। क्या आप आज का छोटा mood check-in पूरा करना चाहेंगे?"

    if risk_level == "High":
        return "I’m really glad you reached out. Please contact a trusted person or local emergency help now. We can start with a 4-7-8 breathing exercise together."
    if sentiment == "negative":
        return "I hear you. Would you like to rate your current feeling from 1-10? We can do a short grounding exercise next."
    return "Thanks for sharing. Would you like to complete today’s quick mood check-in?"
