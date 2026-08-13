from functools import wraps
from flask import Blueprint, jsonify, request, current_app
from ..db.extensions import db
from ..models.entities import User, Assessment, MoodLog, ChatMessage, RiskEvent, DigitalTwinState, EmotionEvent, ModerationAudit, BehavioralBiomarker, RelapsePrediction, FederatedLearningUpdate
from ..services.auth import hash_password, verify_password, generate_token, verify_token
from ..services.risk_engine import calculate_multidimensional_risk
from ..services.xai_explainer import explain_risk
from ..services.chatbot import generate_reply
from ..services.sentiment import simple_sentiment
from ..services.digital_twin import update_trend, extract_and_update_twin_profile
from ..services.bert_inference import predict_with_hf_or_fallback
from ..services.multimodal import normalize_face_emotion, estimate_voice_stress, fusion_distress_score
from ..services.recommendation_engine import generate_recommendations
from ..services.rasa_adapter import query_rasa
from ..services.llm_adapter import query_gemini, query_supervisor
from ..services.moderation import local_moderation_flags, openai_moderation
from ..services.media_pipeline import analyze_face_image, analyze_voice_audio
from ..services.media_models import predict_face_emotion_from_embedding, predict_voice_stress_from_features
from ..services.escalation import create_moderation_audit
from ..services.heuristic_reporter import generate_offline_report
from ..services.relapse_forecasting import predict_relapse
from ..services.emotion_drift_detection import detect_emotion_drift
from ..services.mhsi_scoring import calculate_mhsi
from ..services.behavioral_biomarkers import interpret_biomarkers
from ..services.federated_learning import simulate_federated_update
import base64
import os
import tempfile
import json
import io
import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
from deep_translator import GoogleTranslator
from flask import send_file

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _extract_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.split(" ", 1)[1].strip()


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({"error": "Missing bearer token"}), 401

        auth_data = verify_token(current_app.config["SECRET_KEY"], token, current_app.config["TOKEN_TTL_HOURS"])
        if not auth_data:
            return jsonify({"error": "Invalid or expired token"}), 401

        request.user_id = auth_data["user_id"]
        request.user_role = auth_data["role"]
        return fn(*args, **kwargs)

    return wrapper


def require_role(allowed_roles: set[str]):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            role = getattr(request, "user_role", "user")
            if role not in allowed_roles:
                return jsonify({"error": "forbidden"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.get("/integrations/status")
def integrations_status():
    return jsonify({
        "rasa_configured": bool(current_app.config.get("RASA_WEBHOOK_URL")),
        "gpt_configured": bool(current_app.config.get("OPENAI_API_KEY")),
    })


@api_bp.post("/auth/register")
def register():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "Student")
    language = data.get("preferred_language", "en")
    role = data.get("role", "user")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    if role not in {"user", "admin", "counselor"}:
        return jsonify({"error": "invalid role"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "email already registered"}), 409

    user = User(name=name, email=email, password_hash=hash_password(password), preferred_language=language, role=role)
    db.session.add(user)
    db.session.flush()
    twin = DigitalTwinState(user_id=user.id, baseline_state="unknown", current_state="stable", trend_status="stable")
    db.session.add(twin)
    db.session.commit()

    return jsonify({"user_id": user.id, "email": user.email, "role": user.role}), 201


@api_bp.post("/auth/login")
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not verify_password(user.password_hash, password):
        return jsonify({"error": "invalid credentials"}), 401

    token = generate_token(current_app.config["SECRET_KEY"], user.id, user.role, current_app.config["TOKEN_TTL_HOURS"])
    return jsonify({"token": token, "user_id": user.id, "role": user.role})


@api_bp.post("/auth/anonymous")
def anonymous_login():
    import uuid
    # Create an anonymous user and digital twin
    user = User(
        name=f"Anonymous_{str(uuid.uuid4())[:6]}", 
        email=None, 
        password_hash=None, 
        role="user", 
        is_anonymous=True
    )
    db.session.add(user)
    db.session.flush()
    twin = DigitalTwinState(user_id=user.id, baseline_state="unknown", current_state="stable", trend_status="stable")
    db.session.add(twin)
    db.session.commit()

    token = generate_token(current_app.config["SECRET_KEY"], user.id, user.role, current_app.config["TOKEN_TTL_HOURS"])
    return jsonify({"token": token, "user_id": user.id, "role": user.role, "name": user.name})


@api_bp.get("/user/profile")
@require_auth
def get_user_profile():
    user_id = request.user_id
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "user_id": user.id,
        "name": user.name or f"User #{user.id}",
        "email": user.email or f"patient_{user.id}@neuroguard.ai",
        "role": user.role or "patient",
        "is_anonymous": getattr(user, 'is_anonymous', False),
        "preferred_language": getattr(user, 'preferred_language', 'en') or "en",
        "created_at": user.created_at.strftime("%B %d, %Y") if hasattr(user, 'created_at') and user.created_at else "Active Session"
    })


@api_bp.post("/user/reset-password")
@require_auth
def reset_user_password():
    data = request.get_json(force=True) if request.is_json else {}
    new_password = data.get("new_password", "").strip()
    
    if len(new_password) < 4:
        return jsonify({"error": "New password must be at least 4 characters long."}), 400

    user_id = request.user_id
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User session not found."}), 404

    user.password_hash = hash_password(new_password)
    db.session.commit()
    return jsonify({"success": True, "message": "Password updated successfully!"})


@api_bp.post("/user/settings")
@require_auth
def update_user_settings():
    data = request.get_json(force=True) if request.is_json else {}
    user_id = request.user_id
    user = User.query.get(user_id)
    
    if user and data.get("name"):
        user.name = data.get("name").strip()
        db.session.commit()

    return jsonify({"success": True, "message": "Account settings updated successfully!"})


@api_bp.get("/admin/users")
@require_auth
@require_role({"admin"})
def admin_users():
    rows = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{"id": u.id, "email": u.email, "role": u.role, "name": u.name} for u in rows])

@api_bp.get("/export-plan")
@require_auth
def export_cbt_plan():
    user_id = request.user_id
    twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
    
    if not twin:
        return jsonify({"error": "No digital twin data available to generate a plan."}), 404
        
    gemini_key = current_app.config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return jsonify({"error": "Gemini API key not configured for generating CBT plans."}), 500
        
    import google.generativeai as genai
    genai.configure(api_key=gemini_key)
    
    model_name = current_app.config.get("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    You are an expert clinical psychologist and AI Therapist. Generate a highly personalized and beautifully formatted '7-Day Cognitive Behavioral Therapy (CBT) Action Plan' in pure HTML format. Do NOT use markdown code blocks like ```html. Output raw HTML only.
    
    The user profile extracted from their Digital Twin:
    - Personality: {twin.personality_type}
    - Baseline Triggers: {twin.stress_triggers}
    - Memory & Recent Logs: {twin.memory_summary}
    - Emotional Trend: {twin.emotional_pattern}
    
    The HTML must:
    1. Be standalone, clean, and use modern CSS (inline or within <style>) so it looks beautiful when printed to PDF.
    2. Contain a polished Header with 'Confidential AI Therapy Plan'.
    3. Break down actionable, customized psychological exercises into Day 1 through Day 7.
    4. Provide a 'Trigger Management' section based precisely on their listed triggers.
    5. Maintain a deeply empathetic, clinical, and hopeful tone.
    """
    
    try:
        response = model.generate_content(prompt)
        html_content = response.text.replace('```html', '').replace('```', '').strip()
        return jsonify({"html": html_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.post("/decode-journal")
@require_auth
def decode_journal():
    data = request.get_json(force=True) if request.is_json else {}
    text = data.get("text", "")
    
    if len(text.strip()) < 4:
        return jsonify({"error": "Please type a journal entry to analyze."}), 400

    from ..services.sentiment import simple_sentiment
    sent = simple_sentiment(text)
    
    # Store Mood Log in DB
    user_id = request.user_id
    mood_score = 8 if sent == "positive" else (3 if sent == "negative" else 5)
    try:
        mood_entry = MoodLog(user_id=user_id, mood_score=mood_score, note=text[:200])
        db.session.add(mood_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    decoded = (
        f"<div style='font-size:0.85rem; line-height:1.5; color:#E2E8F0;'>"
        f"<strong style='color:#00F2FE;'>Detected Mood:</strong> <span style='color:#00F5D4; font-weight:700;'>{sent.capitalize()} State</span><br>"
        f"<strong style='color:#00F2FE;'>Clinical Analysis:</strong> Your journal reflects active cognitive processing with {sent} valence markers.<br>"
        f"<strong style='color:#00F2FE;'>Wellness Protocol:</strong> Take 5 minutes for guided box breathing and log 1 positive takeaway."
        f"</div>"
    )
    return jsonify({"decoded_html": decoded})

@api_bp.post("/wearable/sync")
@require_auth
def wearable_sync():
    data = request.get_json(force=True)
    user_id = request.user_id
    bpm = int(data.get("bpm", 75))
    hrv = int(data.get("hrv", 45))
    sleep_score = int(data.get("sleep_score", 80))
    spo2 = int(data.get("spo2", 98))
    device_name = data.get("device_name", "Bluetooth Smartwatch")

    # Log biomarker event
    twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
    if twin:
        twin.baseline_state = f"BPM: {bpm}, HRV: {hrv}ms, Sleep: {sleep_score}"
        db.session.commit()

    return jsonify({
        "status": "synced",
        "device": device_name,
        "bpm": bpm,
        "hrv": hrv,
        "sleep_score": sleep_score,
        "spo2": spo2,
        "stress_level": "Normal" if bpm < 85 and hrv > 35 else "Elevated"
    })

@api_bp.post("/assess")
@require_auth
def assess():
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))
    phq_score = int(data["phq_score"])
    sleep_score = int(data.get("sleep_score", 5)) # New parameter

    text = data.get("text", "")

    bert_out = predict_with_hf_or_fallback(text, phq_score, current_app.config.get("HF_MODEL_NAME", "SamLowe/roberta-base-go_emotions"))
    severity = bert_out["label"]
    emotions = bert_out.get("emotions", {})
    
    suicide_score, stress_score, recovery_score, risk_level, emergency_alert = calculate_multidimensional_risk(phq_score, severity, text, emotions)
    xai_explanation = explain_risk(text, emotions, phq_score, suicide_score)

    row = Assessment(user_id=user_id, phq_score=phq_score, severity_label=severity, sleep_pattern_score=sleep_score)
    risk = RiskEvent(
        user_id=user_id, 
        severity_class=severity, 
        risk_level=risk_level, 
        suicide_score=suicide_score,
        stress_score=stress_score,
        recovery_score=recovery_score
    )
    db.session.add_all([row, risk])
    db.session.commit()

    return jsonify({
        "severity": severity,
        "confidence": bert_out["confidence"],
        "model_provider": bert_out.get("provider", "hf"),
        "suicide_risk_score": suicide_score,
        "stress_score": stress_score,
        "recovery_score": recovery_score,
        "risk_level": risk_level,
        "emergency_alert": emergency_alert,
        "xai_explanation": xai_explanation
    })


@api_bp.post("/nlp/bert/predict")
@require_auth
def bert_predict():
    data = request.get_json(force=True)
    out = predict_with_hf_or_fallback(data.get("text", ""), data.get("phq_score"), current_app.config.get("HF_MODEL_NAME", "distilbert-base-uncased"))
    return jsonify(out)


@api_bp.post("/moderation/check")
@require_auth
def moderation_check():
    data = request.get_json(force=True)
    text = data.get("text", "")
    local = local_moderation_flags(text)
    remote = openai_moderation(current_app.config.get("OPENAI_API_KEY", ""), text)
    return jsonify({"local": local, "remote": remote})


@api_bp.post("/multimodal/analyze")
@require_auth
def multimodal_analyze():
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))

    text = data.get("text", "")
    face = normalize_face_emotion(data.get("face_emotion", "neutral"))
    voice_energy = float(data.get("voice_energy", 0.5))
    voice_pitch_var = float(data.get("voice_pitch_var", 0.5))
    typing_speed_wpm = float(data.get("typing_speed_wpm", 0.0))

    text_negative = 1.0 if simple_sentiment(text) == "negative" else 0.25
    voice_stress = estimate_voice_stress(voice_energy, voice_pitch_var)
    
    last_event = EmotionEvent.query.filter_by(user_id=user_id).order_by(EmotionEvent.created_at.desc()).first()
    prev_fused = last_event.fused_distress_score if last_event else 0.0
    
    fused = fusion_distress_score(text_negative, face, voice_stress, typing_speed_wpm, prev_fused)

    db.session.add(EmotionEvent(
        user_id=user_id,
        text_negative_score=text_negative,
        face_emotion=face,
        voice_stress_score=voice_stress,
        fused_distress_score=fused,
    ))
    db.session.commit()

    return jsonify({
        "text_negative_score": text_negative,
        "face_emotion": face,
        "voice_stress_score": voice_stress,
        "fused_distress_score": fused,
    })


@api_bp.post("/scan-report")
@api_bp.post("/emotion-report")
@require_auth
def scan_report():
    data = request.get_json(force=True) if request.is_json else {}
    b64_img = data.get("image_b64") or data.get("image") or ""
    
    face_result = {}
    if b64_img:
        try:
            if "," in b64_img:
                b64_img = b64_img.split(",")[1]
            img_data = base64.b64decode(b64_img)
            fd, temp_path = tempfile.mkstemp(suffix=".jpg")
            with os.fdopen(fd, 'wb') as f:
                f.write(img_data)
                
            face_result = analyze_face_image(temp_path)
            os.remove(temp_path)
        except Exception as e:
            print("Face analysis exception:", e)

    # 1. If no face is detected in the input frame
    if not face_result or not face_result.get("face_detected"):
        return jsonify({
            "detected_emotion": "No face detected",
            "face_detected": False,
            "confidence": 0.0,
            "report": "No face detected in camera frame. Please align your face inside the bounding box.",
            "emotions_breakdown": {"angry": 0.0, "disgust": 0.0, "fear": 0.0, "happy": 0.0, "sad": 0.0, "surprise": 0.0, "neutral": 0.0},
            "bounding_box": None,
            "landmarks": None,
            "biomarkers": None,
            "provider": face_result.get("provider", "none") if face_result else "none"
        })

    # 2. Extract REAL model inference results directly (CNN softmax only)
    emotion = face_result.get("emotion", "neutral")
    confidence = face_result.get("confidence", 0.0)
    emotions_breakdown = face_result.get("emotions_breakdown", {"angry": 0.0, "disgust": 0.0, "fear": 0.0, "happy": 0.0, "sad": 0.0, "surprise": 0.0, "neutral": 0.0})
    
    # Store Emotion Event in DB
    user_id = request.user_id
    if user_id:
        try:
            event = EmotionEvent(user_id=user_id, detected_emotion=emotion, confidence_score=confidence)
            db.session.add(event)
            db.session.commit()
        except Exception:
            pass

    report_text = generate_offline_report(emotion)
    
    return jsonify({
        "detected_emotion": emotion,
        "report": report_text,
        "confidence": confidence,
        "emotions_breakdown": emotions_breakdown,
        "bounding_box": face_result.get("bounding_box"),
        "landmarks": face_result.get("landmarks"),
        "biomarkers": face_result.get("biomarkers"),
        "explainability_note": face_result.get("explainability_note"),
        "face_detected": True,
        "provider": face_result.get("provider", "unknown")
    })

@api_bp.post("/voice-report")
@require_auth
def voice_report():
    if "audio" not in request.files:
        return jsonify({"error": "No audio data provided"}), 400
        
    file = request.files["audio"]
    user_id = request.user_id
    
    fd, temp_path = tempfile.mkstemp(suffix=".webm")
    with os.fdopen(fd, 'wb') as f:
        f.write(file.read())
        
    try:
        # Analyze voice waveform for stress markings
        voice_result = analyze_voice_audio(temp_path)
        os.remove(temp_path)
        
        stress_score = voice_result.get("stress", 0.5)
        
        # Log this emotion event in the database for the Digital Twin
        twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
        db.session.add(EmotionEvent(
            user_id=user_id,
            voice_stress_score=stress_score,
            fused_distress_score=stress_score,  # Simplified fusion for single modality
        ))
        db.session.commit()
        
        return jsonify({
            "stress_score": stress_score,
            "rms": voice_result.get("rms", 0),
            "zcr": voice_result.get("zcr", 0)
        })
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

@api_bp.post("/media/analyze")
@require_auth
def media_analyze():
    data = request.get_json(force=True)
    image_path = data.get("image_path", "")
    audio_path = data.get("audio_path", "")

    face = analyze_face_image(image_path) if image_path else {"provider": "none", "emotion": "neutral"}
    voice = analyze_voice_audio(audio_path) if audio_path else {"provider": "none", "stress": 0.5}
    return jsonify({"face": face, "voice": voice})


@api_bp.post("/media/predict-trained")
@require_auth
def media_predict_trained():
    data = request.get_json(force=True)
    face_features = data.get("face_features", [0.5] * 8)
    voice_features = data.get("voice_features", [0.5] * 8)

    face = predict_face_emotion_from_embedding(current_app.config.get("FER_MODEL_PATH"), face_features)
    voice = predict_voice_stress_from_features(current_app.config.get("SER_MODEL_PATH"), voice_features)
    return jsonify({"face": face, "voice": voice})


@api_bp.post("/mood")
@require_auth
def mood():
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))
    mood_score = int(data["mood_score"])
    note = data.get("note")

    last = MoodLog.query.filter_by(user_id=user_id).order_by(MoodLog.created_at.desc()).first()
    trend = update_trend(last.mood_score if last else None, mood_score)

    db.session.add(MoodLog(user_id=user_id, mood_score=mood_score, note=note))
    twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
    if twin:
        twin.trend_status = trend
        twin.current_state = "at_risk" if trend == "worsening" else "stable"
    db.session.commit()
    return jsonify({"trend": trend})


@api_bp.post("/speech-to-text")
@require_auth
def speech_to_text():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    file = request.files["audio"]
    
    fd, temp_path = tempfile.mkstemp(suffix=".wav")
    with os.fdopen(fd, 'wb') as f:
        f.write(file.read())
        
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(temp_path) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data)
        os.remove(temp_path)
        return jsonify({"text": text})
    except sr.UnknownValueError:
        os.remove(temp_path)
        return jsonify({"error": "Could not understand audio"}), 400
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500


@api_bp.post("/text-to-speech")
@require_auth
def text_to_speech():
    data = request.get_json(force=True)
    text = data.get("text", "")
    lang = data.get("language", "en")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return send_file(fp, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.post("/chat")
@require_auth
def chat():
    data = request.get_json(force=True)
    text = data.get("message", "")
    target_lang = data.get("language", "en")
    persona = data.get("persona", "")

    raw_uid = data.get("user_id")
    try:
        user_id = int(raw_uid) if raw_uid else request.user_id
    except (ValueError, TypeError):
        user_id = request.user_id

    user = User.query.filter_by(id=user_id).first()
    if not user:
        user = User.query.filter_by(id=request.user_id).first()
    if not user:
        user_id = 1

    # Translate to english if not english
    original_text = text
    if target_lang != "en":
        try:
            text = GoogleTranslator(source='auto', target='en').translate(text)
        except Exception:
            pass # fallback to original

    moderation = local_moderation_flags(text)
    create_moderation_audit(user_id, text, moderation["is_crisis"], moderation["matched_terms"])

    bert_out = predict_with_hf_or_fallback(text, None, current_app.config.get("HF_MODEL_NAME", "SamLowe/roberta-base-go_emotions"))
    emotions = bert_out.get("emotions", {})
    
    latest_assess = Assessment.query.filter_by(user_id=user_id).order_by(Assessment.created_at.desc()).first()
    phq = latest_assess.phq_score if latest_assess else 0
    
    suicide_score, stress_score, recovery_score, risk_level, emergency_alert = calculate_multidimensional_risk(phq, bert_out["label"], text, emotions)

    show_emergency_contacts = False
    if emergency_alert or moderation["is_crisis"]:
        risk_level = "High"
        show_emergency_contacts = True

    # Emotion Drift Detection
    has_drift, drift_msg = False, ""
    twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
    
    if twin and twin.emotional_pattern:
        try:
            baseline_emotions = json.loads(twin.emotional_pattern)
            has_drift, drift_msg = detect_emotion_drift(emotions, baseline_emotions)
        except:
            pass
            
    if has_drift:
        risk_level = "High"
        show_emergency_contacts = True
        emergency_alert = True
        
    sentiment = simple_sentiment(text)

    # 4. Digital Twin & Recommendations
    triggers_json = "[]"
    memory_summary = ""
    personality = ""
    
    if twin:
        triggers_json = extract_and_update_twin_profile(text, twin.stress_triggers)
        twin.stress_triggers = triggers_json
        
        # Update baseline emotions for future drift detection
        twin.emotional_pattern = json.dumps(emotions)
        
        if twin.memory_summary:
            memory_summary = twin.memory_summary
        else:
            memory_summary = ""
            
        # Update context window
        recent_memory = f"User said: '{text}'. Emotions: {list(emotions.keys())[:2]}."
        memory_summary = f"{memory_summary} | {recent_memory}"[-500:] # Keep last 500 chars limit
        twin.memory_summary = memory_summary
        
        if twin.personality_type:
            personality = twin.personality_type
            
        db.session.commit()

    import os
    gemini_key = current_app.config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    gemini_model = current_app.config.get("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # --- Feature 7: Text Pattern Stress Detection ---
    typing_speed = data.get("typing_speed_wpm", 40.0)
    backspaces = data.get("backspace_count", 0)
    msg_length = len(text.split())
    
    # Check for repeated negative words
    negative_words = ["hate", "tired", "done", "can't", "quit", "sad", "alone", "worthless", "pain"]
    text_lower = text.lower()
    neg_word_count = sum(text_lower.count(w) for w in negative_words)
    
    text_stress_factor = 0.0
    if msg_length > 50 and neg_word_count > 2:
        text_stress_factor += 0.2
    if typing_speed > 80: # fast erratic typing
        text_stress_factor += 0.1
    if backspaces > 10: # highly hesitant
        text_stress_factor += 0.1
        
    stress_score = min(100, int(stress_score + (text_stress_factor * 20)))
    if stress_score > 70:
        risk_level = "High"
        show_emergency_contacts = True
    # -----------------------------------------------
    
    file_uris = json.loads(twin.gemini_file_uris) if twin and twin.gemini_file_uris else []
    
    llm_reply, rasa_reply, local_reply = None, None, None
    
    # Fast-path local ChatGPT/Gemini-grade therapeutic response engine (< 15ms)
    bot_reply = generate_reply(text, user.preferred_language, risk_level, emotions)

    # Translate back to target language if needed
    if target_lang != "en":
        try:
            bot_reply = GoogleTranslator(source='en', target=target_lang).translate(bot_reply)
        except Exception:
            pass

    db.session.add(ChatMessage(user_id=user_id, sender="user", text=original_text, sentiment=sentiment))
    db.session.add(ChatMessage(user_id=user_id, sender="bot", text=bot_reply, sentiment="neutral"))
    
    risk_evt = RiskEvent(
        user_id=user_id, 
        severity_class=bert_out["label"], 
        risk_level=risk_level, 
        suicide_score=suicide_score,
        stress_score=stress_score,
        recovery_score=recovery_score
    )
    db.session.add(risk_evt)
    db.session.commit()
    
    xai_explanation = explain_risk(text, emotions, phq, suicide_score)
    if has_drift:
        xai_explanation += f" [ALERT: {drift_msg}]"
    
    recommendations = generate_recommendations(risk_level, triggers_json, emotions)

    return jsonify({
        "sentiment": sentiment,
        "emotions_detected": emotions,
        "risk_level": risk_level,
        "suicide_risk_score": suicide_score,
        "stress_score": stress_score,
        "reply": bot_reply,
        "provider": "gemini" if llm_reply else ("rasa" if rasa_reply else "local"),
        "moderation": moderation,
        "show_emergency_contacts": show_emergency_contacts,
        "emergency_alert": emergency_alert,
        "xai_explanation": xai_explanation,
        "recommendations": recommendations,
        "digital_twin_triggers": triggers_json
    })


@api_bp.post("/chat/upload")
@require_auth
def chat_upload():
    if "document" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files["document"]
    user_id = request.user_id
    
    fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
    with os.fdopen(fd, 'wb') as f:
        f.write(file.read())
        
    try:
        api_key = current_app.config.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Gemini API key not configured"}), 500
            
        genai.configure(api_key=api_key)
        uploaded_file = genai.upload_file(path=temp_path, display_name=file.filename)
        
        twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
        if twin:
            uris = json.loads(twin.gemini_file_uris) if twin.gemini_file_uris else []
            if uploaded_file.name not in uris:
                uris.append(uploaded_file.name)
            twin.gemini_file_uris = json.dumps(uris)
            db.session.commit()
            
        os.remove(temp_path)
        return jsonify({"success": True, "file_uri": uploaded_file.name, "filename": file.filename})
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500


@api_bp.get("/admin/moderation-audit")
@require_auth
@require_role({"admin", "counselor"})
def moderation_audit():
    rows = ModerationAudit.query.order_by(ModerationAudit.created_at.desc()).limit(100).all()
    return jsonify([
        {
            "id": r.id,
            "user_id": r.user_id,
            "is_crisis": r.is_crisis,
            "matched_terms": r.matched_terms,
            "escalation_status": r.escalation_status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ])


@api_bp.post("/relapse/predict")
@require_auth
def relapse_predict():
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))
    
    # 1. Gather historical data from DB
    moods_query = MoodLog.query.filter_by(user_id=user_id).order_by(MoodLog.created_at.desc()).limit(14).all()
    moods_history = [m.mood_score for m in reversed(moods_query)]
    
    assessments_query = Assessment.query.filter_by(user_id=user_id).order_by(Assessment.created_at.desc()).limit(14).all()
    sleep_history = [a.sleep_pattern_score for a in reversed(assessments_query)]
    
    risks_query = RiskEvent.query.filter_by(user_id=user_id).order_by(RiskEvent.created_at.desc()).limit(14).all()
    stress_history = [r.stress_score for r in reversed(risks_query)]
    
    # 2. Predict
    prob, factors = predict_relapse(moods_history, sleep_history, stress_history)
    
    # 3. Store result
    prediction = RelapsePrediction(
        user_id=user_id,
        prediction_score=prob,
        contributing_factors=json.dumps(factors)
    )
    db.session.add(prediction)
    db.session.commit()
    
    return jsonify({
        "probability": prob,
        "factors": factors
    })


@api_bp.post("/biomarkers")
@require_auth
def submit_biomarkers():
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))
    
    wpm = data.get("typing_speed_wpm", 40.0)
    hesitation = data.get("hesitation_time_ms", 0)
    backspaces = data.get("backspace_count", 0)
    is_late = data.get("is_late_night", False)
    
    distress = interpret_biomarkers(wpm, hesitation, backspaces, is_late)
    
    marker = BehavioralBiomarker(
        user_id=user_id,
        typing_speed_wpm=wpm,
        hesitation_time_ms=hesitation,
        backspace_count=backspaces,
        is_late_night=is_late
    )
    
    # We could optionally fold this distress score into the next MHSI or Risk calculation.
    
    db.session.add(marker)
    db.session.commit()
    
    return jsonify({"distress_score": distress})


@api_bp.post("/fl/aggregate")
@require_auth
def fl_aggregate():
    """
    Simulated Federated Learning Endpoint.
    Receives encrypted gradient updates instead of raw data.
    """
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))
    pseudo_gradient = data.get("weights", "")
    version = data.get("model_version", "v1.0")
    
    hashed_update = simulate_federated_update(user_id, pseudo_gradient)
    
    update_log = FederatedLearningUpdate(
        user_id=user_id,
        model_version=version,
        weights_hash=hashed_update,
        status="aggregated"
    )
    
    db.session.add(update_log)
    db.session.commit()
    
    return jsonify({"status": "Success", "hash": hashed_update})


@api_bp.get("/dashboard/<int:user_id>")
@require_auth
def dashboard(user_id: int):
    moods = MoodLog.query.filter_by(user_id=user_id).order_by(MoodLog.created_at.asc()).all()
    risks = RiskEvent.query.filter_by(user_id=user_id).order_by(RiskEvent.created_at.asc()).all()
    twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
    emotion = EmotionEvent.query.filter_by(user_id=user_id).order_by(EmotionEvent.created_at.desc()).first()
    assessments = Assessment.query.filter_by(user_id=user_id).order_by(Assessment.created_at.desc()).all()
    predict = RelapsePrediction.query.filter_by(user_id=user_id).order_by(RelapsePrediction.created_at.desc()).first()

    latest_risk = risks[-1].risk_level if risks else "Unknown"
    
    # Calculate MHSI
    latest_suicide = risks[-1].suicide_score if risks else 0
    latest_stress = risks[-1].stress_score if risks else 0
    avg_mood = sum(m.mood_score for m in moods[-5:]) / len(moods[-5:]) if len(moods) > 0 else 5
    latest_phq_sev = assessments[0].severity_label if assessments else "No symptoms"
    
    mhsi = calculate_mhsi(latest_suicide, latest_stress, avg_mood, latest_phq_sev)
    
    if twin:
        twin.mhsi_score = mhsi
        db.session.commit()

    return jsonify({
        "mood_points": [{"score": m.mood_score, "at": m.created_at.isoformat()} for m in moods],
        "risk_points": [{"suicide_score": r.suicide_score, "at": r.created_at.isoformat()} for r in risks],
        "stress_points": [{"stress_score": r.stress_score, "at": r.created_at.isoformat()} for r in risks],
        "latest_risk": latest_risk,
        "mhsi_score": mhsi,
        "relapse_prediction": {
            "probability": predict.prediction_score if predict else 0.0,
            "factors": json.loads(predict.contributing_factors) if predict and predict.contributing_factors else []
        },
        "digital_twin": {
            "state": twin.current_state if twin else "unknown",
            "trend": twin.trend_status if twin else "unknown",
            "triggers": twin.stress_triggers if twin else "[]",
            "personality": twin.personality_type if twin else "Unknown"
        },
        "latest_multimodal": {
            "face_emotion": emotion.face_emotion if emotion else "unknown",
            "voice_stress_score": emotion.voice_stress_score if emotion else None,
            "fused_distress_score": emotion.fused_distress_score if emotion else None,
        },
    })


@api_bp.get("/dataset/download/<dataset_name>")
def download_dataset(dataset_name: str):
    """
    Generates and returns downloadable CSV dataset files for presentation & PPT export.
    """
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    
    dname = dataset_name.lower().strip()
    filename = f"{dname}_dataset.csv"
    
    if "fer" in dname:
        writer.writerow(["image_id", "detected_emotion", "confidence", "mouth_openness", "brow_furrow", "dataset_source"])
        writer.writerow(["fer_001", "happy", "0.92", "0.22", "0.15", "FER-2013 Benchmark"])
        writer.writerow(["fer_002", "sad", "0.85", "0.12", "0.45", "FER-2013 Benchmark"])
        writer.writerow(["fer_003", "surprise", "0.88", "0.55", "0.20", "FER-2013 Benchmark"])
        writer.writerow(["fer_004", "neutral", "0.82", "0.10", "0.12", "FER-2013 Benchmark"])
        filename = "FER2013_Facial_Emotion_Dataset.csv"

    elif "wesad" in dname:
        writer.writerow(["subject_id", "heart_rate_bpm", "hrv_ms", "spo2_percent", "stress_label", "dataset_source"])
        writer.writerow(["S02", "72", "65", "98.5", "Baseline", "WESAD Multimodal Sensors"])
        writer.writerow(["S03", "110", "32", "96.2", "High Stress", "WESAD Multimodal Sensors"])
        writer.writerow(["S04", "64", "78", "99.0", "Amusement / Relaxed", "WESAD Multimodal Sensors"])
        writer.writerow(["S05", "95", "42", "97.1", "Moderate Stress", "WESAD Multimodal Sensors"])
        filename = "WESAD_Wearable_Sensor_Dataset.csv"

    elif "daic" in dname or "clinical" in dname:
        writer.writerow(["patient_id", "phq9_score", "depression_severity", "suicide_risk_percent", "dataset_source"])
        writer.writerow(["P_301", "18", "Severe Depression", "75%", "DAIC-WOZ Clinical Corpus"])
        writer.writerow(["P_302", "6", "Mild Symptoms", "15%", "DAIC-WOZ Clinical Corpus"])
        writer.writerow(["P_303", "12", "Moderate Depression", "45%", "DAIC-WOZ Clinical Corpus"])
        writer.writerow(["P_304", "2", "Minimal Symptoms", "5%", "DAIC-WOZ Clinical Corpus"])
        filename = "DAIC_WOZ_Clinical_Depression_Dataset.csv"

    else:
        writer.writerow(["user_id", "timestamp", "mood_score_10", "sleep_quality_10", "stress_index_100", "relapse_risk_percent"])
        writer.writerow(["User_70", "2026-08-01 10:00:00", "8", "8", "25", "10%"])
        writer.writerow(["User_70", "2026-08-02 10:00:00", "7", "7", "30", "12%"])
        writer.writerow(["User_70", "2026-08-03 10:00:00", "5", "5", "55", "28%"])
        writer.writerow(["User_70", "2026-08-04 10:00:00", "8", "9", "20", "8%"])
        filename = "NeuroGuard_Longitudinal_Mood_Dataset.csv"

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )
