import re
from .sentiment import simple_sentiment

def generate_reply(message: str, language: str, risk_level: str, emotions: dict = None) -> str:
    msg_lower = message.lower().strip()
    if not emotions:
        emotions = {}
        
    dominant_emotion = max(emotions, key=emotions.get) if emotions and emotions.get(max(emotions, key=emotions.get), 0) > 0.3 else None

    # Hindi support
    if language == "hi":
        if risk_level == "High":
            return "मुझे आपकी चिंता है। आपकी सुरक्षा सबसे महत्वपूर्ण है। कृपया तुरंत किसी भरोसेमंद व्यक्ति या हेल्पलाइन **1800-599-0019 (Kiran)** पर संपर्क करें।"
        if any(w in msg_lower for w in ["good", "अच्छा", "badhiya", "मस्त"]):
            return "यह जानकर बहुत खुशी हुई! 🌟 आज आपकी दिनचर्या में क्या अच्छा रहा? मुझे और बताएं!"
        return f"मैं आपकी बात समझ रहा हूँ। '{message}' के बारे में थोड़ा और गहराई से चर्चा करते हैं। आप कैसा महसूस कर रहे हैं?"

    # High Risk Emergency Protocol
    if risk_level == "High":
        return (
            "### 🚨 Safety Support Active\n\n"
            "I hear the depth of your pain, and I want you to know **you are not alone**. Your safety is my highest priority.\n\n"
            "Please take a slow, deep breath. I strongly encourage you to connect with a crisis counselor or trusted friend right now:\n"
            "* **National Helpline:** 988 or text `HOME` to 741741\n"
            "* **Kiran Helpline (India):** 1800-599-0019\n"
            "* **International:** 111 / 999\n\n"
            "Please stay safe. I am right here with you."
        )

    # 1. Jokes & Lightness Support ("joke", "jokes", "funny", "laugh", "humor")
    if any(w in msg_lower for w in ["joke", "jokes", "funny", "laugh", "humor"]):
        return (
            "### 😄 Lighthearted Humor & Endorphin Boost\n\n"
            "Here is a quick joke to bring a smile to your face:\n\n"
            "**Why don't scientists trust atoms?**\n"
            "*Because they make up everything!* ⚛️\n\n"
            "Laughter is a proven natural way to lower cortisol and ease tension. How else can I brighten your day right now?"
        )

    # 2. Overthinking & Racing Thoughts Support ("overthinking", "overthink", "racing thoughts", "thought loop")
    if any(w in msg_lower for w in ["overthinking", "overthink", "racing thoughts", "thought loop", "mind wont stop"]):
        return (
            "### 🌀 Overthinking & Cognitive De-escalation Protocol Active\n\n"
            "Overthinking happens when your brain tries to solve future uncertainties all at once. Let's break the cognitive loop together:\n\n"
            "1. **The 5-4-3-2-1 Sensory Grounding**:\n"
            "   - Name **5 objects you can see** right now\n"
            "   - Name **4 textures you can touch**\n"
            "   - Name **3 sounds you hear**\n"
            "   - Name **2 scents you smell**\n"
            "   - Take **1 deep breath**\n\n"
            "2. **Brain Dump**: Type out the exact loop troubling you in the **AI Mood Journal** on the right to discharge it from your working memory.\n\n"
            "What specific thought is looping in your mind right now?"
        )

    # 3. Sleep & Insomnia Support ("sleep", "sleeping", "can't sleep", "insomnia", "awake", "bed", "night")
    if any(w in msg_lower for w in ["sleep", "sleeping", "insomnia", "awake", "tired", "rest", "night", "bed"]):
        return (
            "### 🌙 Sleep Hygiene & Rest Protocol Active\n\n"
            "I understand how frustrating it is when sleep won't come tonight. Let's calm your nervous system right now with these actionable steps:\n\n"
            "1. **The 4-7-8 Breathing Technique**:\n"
            "   - Inhale quietly through your nose for **4 seconds**\n"
            "   - Hold your breath for **7 seconds**\n"
            "   - Exhale completely through your mouth for **8 seconds**\n"
            "   - Repeat this cycle **4 times** to lower your heart rate.\n\n"
            "2. **The 20-Minute Reset Rule**:\n"
            "   - If you have been lying awake for more than 20 minutes, get out of bed.\n"
            "   - Move to a dimly lit room, avoid bright screens, and read or listen to calming ambient soundscapes.\n\n"
            "3. **Cognitive Brain Dump**:\n"
            "   - Lying awake often means your brain is holding onto racing thoughts or to-do lists.\n"
            "   - Write them down in your **AI Mood Journal** right now so your mind can let them go.\n\n"
            "You are safe, and rest will come. Try the 4-7-8 cycle now—I am right here with you."
        )

    # 4. Stress & Overwhelm Support ("stress", "stressed", "overwhelmed", "work", "pressure", "exam", "busy")
    if any(w in msg_lower for w in ["stress", "stressed", "overwhelmed", "work", "study", "exam", "pressure", "busy", "burnt out"]):
        return (
            "### 🧘 Immediate Stress Decompression Strategy\n\n"
            "It sounds like you're carrying a heavy cognitive load right now. When everything feels urgent, our focus fractures.\n\n"
            "Here are your actionable micro-steps:\n"
            "1. **Box Breathing Technique**: Inhale 4s ➔ Hold 4s ➔ Exhale 6s.\n"
            "2. **Micro-Tasking**: Pick just *one single item* to complete in the next 15 minutes, and ignore everything else.\n"
            "3. **Priority Dump**: Type out everything troubling you here. Getting it out of your head lowers cortisol.\n\n"
            "What is the single biggest source of pressure on your mind right now?"
        )

    # 5. Anxiety & Panic Support ("anxious", "anxiety", "panic", "scared", "nervous", "worry", "fear")
    if any(w in msg_lower for w in ["anxious", "anxiety", "panic", "scared", "nervous", "worry", "fear", "frightened"]):
        return (
            "### 🌿 Grounding Protocol Active\n\n"
            "I hear how overwhelming that anxiety feels right now. Let's ground your nervous system together:\n\n"
            "1. **Physiological Sigh**: Take two quick inhales through your nose, then one long slow exhale through your mouth.\n"
            "2. **3-2-1 Sensory Reset**:\n"
            "   - Look around and name **3 objects you can see**\n"
            "   - Name **2 textures you can feel**\n"
            "   - Take **1 deep breath**\n\n"
            "You are safe. What is causing the anxiety to surge right now?"
        )

    # 6. Positive / Mood Check-in Responses ("good", "great", "awesome", "fine")
    if re.search(r'\b(good|great|awesome|fine|happy|nice|well|okay|ok|amazing|fantastic)\b', msg_lower):
        return (
            "That is wonderful to hear! 🌟\n\n"
            "Recognizing positive moments is a fantastic way to build emotional resilience. "
            "What specifically contributed to feeling good today? Tell me more about what's going well, or let me know how I can support your goals!"
        )

    # 7. Sadness & Depression Support ("sad", "depressed", "depression", "lonely", "down", "cry", "crying", "upset", "numb")
    if any(w in msg_lower for w in ["sad", "depressed", "depression", "lonely", "down", "cry", "crying", "upset", "hurt", "hopeless", "numb", "empty"]):
        return (
            "### 💙 Emotional Validation & Compassion Protocol\n\n"
            "I hear the heavy weight of what you're experiencing right now. Please know that it is completely okay to feel this way, and you do not have to force positivity.\n\n"
            "1. **Allow Yourself Rest**: Give yourself permission to pause without feeling guilty.\n"
            "2. **Gentle Self-Compassion**: Sip a warm glass of water or wrap yourself in a comfortable blanket.\n"
            "3. **Express Without Judgment**: Write down your thoughts in the **AI Mood Journal** on the right.\n\n"
            "You are not alone in this dark moment. I am right here listening whenever you're ready to share more."
        )

    # 8. Anger & Frustration Support ("angry", "anger", "furious", "mad", "irritable", "frustrated", "rage")
    if any(w in msg_lower for w in ["angry", "anger", "furious", "mad", "irritable", "frustrated", "rage"]):
        return (
            "### 🔥 TIPP Emotional Regulation Active\n\n"
            "Anger is a natural human emotion signaling that a boundary or expectation was violated. Let's channel that energy safely:\n\n"
            "1. **Temperature Reset**: Splash cold water on your face or hold an ice cube to rapidly calm your vagus nerve.\n"
            "2. **The 90-Second Emotion Wave**: Physical surge of anger lasts 90 seconds. Take 5 slow, deep exhales before reacting.\n"
            "3. **Physical Release**: Do 10 jumping jacks or squeeze a pillow to discharge intense adrenaline.\n\n"
            "What triggered this intense reaction today?"
        )

    # 9. Grief, Loss & Heartbreak ("grief", "grieving", "breakup", "heartbreak", "loss", "mourn")
    if any(w in msg_lower for w in ["grief", "grieving", "breakup", "heartbreak", "heartbroken", "loss", "lost someone", "death", "mourn"]):
        return (
            "### 🕊️ Compassionate Grief Support\n\n"
            "Loss and heartbreak are among the deepest pain we carry. Grief does not move in a linear line—it comes in waves.\n\n"
            "1. **Honor Your Feelings**: Tears and sadness are proof of the love or value you held.\n"
            "2. **Micro-Nurture**: Eat a simple meal, stay hydrated, and rest your body.\n"
            "3. **No Timeline**: Do not rush your healing process.\n\n"
            "I am standing by quietly with you. Take all the time you need."
        )

    # 10. Self-Esteem & Insecurity ("insecure", "imposter", "failure", "worthless", "not good enough")
    if any(w in msg_lower for w in ["insecure", "imposter", "failure", "worthless", "not good enough", "ugly", "useless", "doubt"]):
        return (
            "### ✨ Self-Worth & Cognitive Reframing\n\n"
            "That voice telling you that you are 'not good enough' is an imposter thought—not a fact.\n\n"
            "1. **Separate Feeling from Reality**: Feeling like a failure does not make you one.\n"
            "2. **Fact Check Exercise**: Name 2 challenges you have overcome in the past.\n"
            "3. **Self-Affirmation**: Speak to yourself as you would to a dear friend in your position.\n\n"
            "You are inherently valuable, capable, and worthy of growth."
        )

    # 11. Relationships & Conflict ("relationship", "argument", "fight", "conflict", "toxic", "friend")
    if any(w in msg_lower for w in ["relationship", "argument", "fight", "conflict", "toxic", "friend", "partner", "boyfriend", "girlfriend"]):
        return (
            "### 🤝 Interpersonal Communication & Boundary Protocol\n\n"
            "Navigating relationship conflict can be emotionally draining. Here is how we maintain healthy clarity:\n\n"
            "1. **DEAR MAN Assertiveness**: Describe the situation objectively ➔ Express your feelings ➔ Assert your boundary calmly.\n"
            "2. **Pause During Escalation**: If emotions are elevated, suggest taking a 20-minute cooling break before resuming.\n\n"
            "What specific situation are you navigating right now?"
        )

    # 12. Focus, ADHD & Procrastination ("focus", "adhd", "distracted", "brain fog", "procrastinate")
    if any(w in msg_lower for w in ["focus", "adhd", "distracted", "brain fog", "procrastinate", "procrastinating", "can't focus"]):
        return (
            "### 🎯 Focus & Cognitive Clarity Protocol\n\n"
            "Brain fog and procrastination are signs of cognitive overwhelm, not laziness. Here is how we reboot your focus:\n\n"
            "1. **Pomodoro 25/5**: Work for 25 minutes, then take a mandatory 5-minute break.\n"
            "2. **Single-Tasking**: Hide all open tabs except the one document you need.\n"
            "3. **Hydration Boost**: Drink a full glass of water right now to clear brain fog.\n\n"
            "What is the single task we are tackling first?"
        )

    # 13. Comprehensive Clinical General Fallback
    return (
        f"### 🧠 Clinical Support Protocol Active\n\n"
        f"I hear you clearly regarding *\"{message}\"*. Every emotion and thought you experience is a valid signal from your mind.\n\n"
        "Here are immediate evidence-based steps to ground yourself right now:\n"
        "1. **Physiological Box Breath**: Inhale for 4s ➔ Hold for 4s ➔ Exhale for 6s.\n"
        "2. **AI Mood Journaling**: Unload your raw thoughts into the **AI Mood Journal** panel on the right.\n"
        "3. **Biomarker Scan**: Click **Biomarker Sync** on the left menu to view your live facial affect and heart rate.\n\n"
        "How can I best assist you in navigating this right now?"
    )
