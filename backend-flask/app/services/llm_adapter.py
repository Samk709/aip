import os
import sys
import google.generativeai as genai

# Disable SSL verification for restricted corporate/university network environments
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384'

_llm_network_disabled = False

def query_gemini(api_key: str, model: str, user_message: str, risk_level: str, memory_summary: str = "", personality: str = "", file_uris: list[str] = None, chat_history: list[dict] = None) -> str | None:
    """
    Context-Aware AI Therapist Adapter using Google Gemini API.
    Supports Optional Document Context via File URIs and multi-turn chat history.
    """
    global _llm_network_disabled
    if not api_key or _llm_network_disabled:
        return None

    try:
        genai.configure(api_key=api_key)
        
        system_prompt = (
            "You are Aurora, an advanced, highly empowering AI life-coach and clinical therapist. "
            "Your goal is to make the user feel heard, validated, and incredibly empowered. "
            "ALWAYS structure your responses using Markdown. "
            "Keep your responses concise, direct, and conversational. Do not use overly complicated step-by-step theories unless specifically asked. "
            "Simply answer what the user is asking while maintaining a warm, supportive, and empathetic tone. "
            "Use markdown bolding or italics for emphasis to make the text beautiful and easy to read.\n\n"
        )
        if memory_summary:
            system_prompt += f"\n\nCRITICAL CONTEXT / AI MEMORY:\nYou MUST leverage the following memory to deeply personalize your response. Treat this as your long-term memory of the user:\n{memory_summary}"
        if personality:
            system_prompt += f"\nUser Personality: {personality}. Adjust tone accordingly."
        else:
            system_prompt += "\nNever provide harmful advice. If risk is high, mandate emergency support."

        generation_config = genai.types.GenerationConfig(temperature=0.5)
        
        gemini = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config=generation_config
        )
        
        formatted_history = []
        if chat_history:
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                formatted_history.append({"role": role, "parts": [msg["parts"]]})
                
        chat = gemini.start_chat(history=formatted_history)
        
        contents = []
        if file_uris:
            for uri in file_uris:
                try:
                    uploaded_file = genai.get_file(uri)
                    contents.append(uploaded_file)
                except Exception as e:
                    print(f"[LLM ADAPTER] Failed to fetch file {uri}: {e}", file=sys.stderr)

        contents.append(f"Risk level: {risk_level}. Message: {user_message}")
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(chat.send_message, contents)
            response = future.result(timeout=2.0)
            return response.text.strip()

    except Exception as e:
        print(f"[LLM ADAPTER] Gemini call failed/timed out: {e}", file=sys.stderr)
        return None
        err = str(e).lower()
        if "429" in err or "quota" in err or "rate" in err:
            return (
                "I'm currently processing a high volume of emotional telemetry, and the free Gemini API requires me to take a brief pause before responding again (Rate Limit Exceeded).\n\n"
                "### Action Required\n"
                "1. **Breathe**: Take a deep breath in through your nose for 4 seconds.\n"
                "2. **Wait**: Please wait 30 seconds and send your message again. I'm right here with you."
            )
        print(f"[Gemini Adapter Exception]: {e}", file=sys.stderr)
        return None

def query_supervisor(api_key: str, model: str, user_message: str, draft_reply: str) -> str:
    """
    Multi-Agent Supervisor: Reviews the drafted reply from the primary AI.
    Returns the original reply appended with a Safe badge, OR overrides the reply with an Emergency Intervention.
    """
    if not api_key or not draft_reply:
        return draft_reply + "\n<br><span class=\"system-tag text-success\"><i class=\"ph-fill ph-check-circle\"></i> SYSTEM FALLBACK</span>"

    try:
        genai.configure(api_key=api_key)
        
        supervisor_prompt = (
            "You are an objective Clinical Safety Supervisor AI. Your exact task is to review a draft message written by the Primary AI therapist and determine if it is clinically safe to send to the user.\n\n"
            "Here is the context:\n"
            f"User said: '{user_message}'\n\n"
            f"Primary AI Drafted: '{draft_reply}'\n\n"
            "Evaluation Criteria:\n"
            "1. Does the draft offer dangerous medical diagnoses?\n"
            "2. Does the draft minimize or ignore clear signs of self-harm or imminent danger?\n"
            "3. Is the draft highly inappropriate or offensive?\n\n"
            "If PASS: Output strictly the word 'PASS'. Do NOT output anything else.\n"
            "If FAIL: Write a completely new, safe, and urgent emergency intervention message (max 3 sentences) instructing the user to contact emergency services immediately."
        )

        generation_config = genai.types.GenerationConfig(temperature=0.1)
        
        gemini = genai.GenerativeModel(
            model_name=model,
            system_instruction="You are the strict, objective Clinical Safety Supervisor AI.",
            generation_config=generation_config
        )
        
        response = gemini.generate_content([supervisor_prompt])
        review = response.text.strip()
        
        if review.upper() == "PASS" or "PASS" in review.upper()[:10]:
            return draft_reply + "\n<br><span class=\"system-tag text-success\" style=\"font-size: 0.75rem; padding: 4px 8px; background: rgba(0, 255, 136, 0.1); border: 1px solid var(--accent-success); border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; margin-top: 10px;\"><i class=\"ph-fill ph-shield-check\"></i> CLINICAL SUPERVISOR: VERIFIED SAFE</span>"
        else:
            # The supervisor failed it and wrote an override
            print(f"[SUPERVISOR] Intercepted dangerous response! Override: {review}", file=sys.stderr)
            return review + "\n<br><span class=\"system-tag text-danger\" style=\"font-size: 0.75rem; padding: 4px 8px; background: rgba(255, 59, 48, 0.1); border: 1px solid var(--accent-primary); border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; margin-top: 10px;\"><i class=\"ph-fill ph-warning\"></i> CLINICAL SUPERVISOR: INTERVENTION TRIGGERED</span>"

    except Exception as e:
        print(f"[Gemini Supervisor Exception]: {e}", file=sys.stderr)
        return draft_reply + "\n<br><span class=\"system-tag text-warning\"><i class=\"ph-fill ph-warning-circle\"></i> SUPERVISOR OFFLINE</span>"

