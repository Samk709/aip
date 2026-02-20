from functools import wraps
from flask import Blueprint, jsonify, request, current_app
from ..db.extensions import db
from ..models.entities import User, Assessment, MoodLog, ChatMessage, RiskEvent, DigitalTwinState, EmotionEvent, ModerationAudit
from ..services.auth import hash_password, verify_password, generate_token, verify_token
from ..services.risk_engine import severity_to_risk
from ..services.chatbot import generate_reply
from ..services.sentiment import simple_sentiment
from ..services.digital_twin import update_trend
from ..services.bert_inference import predict_with_hf_or_fallback
from ..services.multimodal import normalize_face_emotion, estimate_voice_stress, fusion_distress_score
from ..services.rasa_adapter import query_rasa
from ..services.gpt_adapter import query_gpt
from ..services.moderation import local_moderation_flags, openai_moderation
from ..services.media_pipeline import analyze_face_image, analyze_voice_audio, analyze_face_frame_base64
from ..services.media_models import predict_face_emotion_from_embedding, predict_voice_stress_from_features
from ..services.escalation import create_moderation_audit

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


@api_bp.get("/admin/users")
@require_auth
@require_role({"admin"})
def admin_users():
    rows = User.query.order_by(User.created_at.desc()).all()
    return jsonify([{"id": u.id, "email": u.email, "role": u.role, "name": u.name} for u in rows])


@api_bp.post("/assess")
@require_auth
def assess():
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))
    phq_score = int(data["phq_score"])

    bert_out = predict_with_hf_or_fallback(data.get("text", ""), phq_score, current_app.config.get("HF_MODEL_NAME", "distilbert-base-uncased"))
    severity = bert_out["label"]
    risk_score, risk_level = severity_to_risk(severity)

    row = Assessment(user_id=user_id, phq_score=phq_score, severity_label=severity)
    risk = RiskEvent(user_id=user_id, severity_class=severity, risk_level=risk_level, risk_score=risk_score)
    db.session.add_all([row, risk])
    db.session.commit()

    return jsonify({
        "severity": severity,
        "confidence": bert_out["confidence"],
        "model_provider": bert_out.get("provider", "fallback"),
        "risk_score": risk_score,
        "risk_level": risk_level,
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

    text_negative = 1.0 if simple_sentiment(text) == "negative" else 0.25
    voice_stress = estimate_voice_stress(voice_energy, voice_pitch_var)
    fused = fusion_distress_score(text_negative, face, voice_stress)

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


@api_bp.post("/media/analyze")
@require_auth
def media_analyze():
    data = request.get_json(force=True)
    image_path = data.get("image_path", "")
    audio_path = data.get("audio_path", "")

    face = analyze_face_image(image_path) if image_path else {"provider": "none", "emotion": "neutral"}
    voice = analyze_voice_audio(audio_path) if audio_path else {"provider": "none", "stress": 0.5}
    return jsonify({"face": face, "voice": voice})




@api_bp.post("/media/analyze-frame")
@require_auth
def media_analyze_frame():
    data = request.get_json(force=True)
    frame = data.get("frame", "")
    if not frame:
        return jsonify({"error": "frame is required"}), 400
    face = analyze_face_frame_base64(frame)
    return jsonify({"face": face})

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


@api_bp.post("/chat")
@require_auth
def chat():
    data = request.get_json(force=True)
    user_id = int(data.get("user_id", request.user_id))
    text = data["message"]

    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    moderation = local_moderation_flags(text)
    create_moderation_audit(user_id, text, moderation["is_crisis"], moderation["matched_terms"])

    latest_risk = RiskEvent.query.filter_by(user_id=user_id).order_by(RiskEvent.created_at.desc()).first()
    risk_level = "High" if moderation["is_crisis"] else (latest_risk.risk_level if latest_risk else "Medium")

    sentiment = simple_sentiment(text)

    rasa_reply = query_rasa(current_app.config["RASA_WEBHOOK_URL"], str(user_id), text)
    gpt_reply = query_gpt(current_app.config["OPENAI_API_KEY"], current_app.config["OPENAI_MODEL"], text, risk_level)
    local_reply = generate_reply(text, user.preferred_language, risk_level)
    bot_reply = gpt_reply or rasa_reply or local_reply

    db.session.add(ChatMessage(user_id=user_id, sender="user", text=text, sentiment=sentiment))
    db.session.add(ChatMessage(user_id=user_id, sender="bot", text=bot_reply, sentiment="neutral"))
    db.session.commit()

    return jsonify({
        "sentiment": sentiment,
        "risk_level": risk_level,
        "reply": bot_reply,
        "provider": "gpt" if gpt_reply else ("rasa" if rasa_reply else "local"),
        "moderation": moderation,
    })


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


@api_bp.get("/dashboard/<int:user_id>")
@require_auth
def dashboard(user_id: int):
    moods = MoodLog.query.filter_by(user_id=user_id).order_by(MoodLog.created_at.asc()).all()
    risk = RiskEvent.query.filter_by(user_id=user_id).order_by(RiskEvent.created_at.desc()).first()
    twin = DigitalTwinState.query.filter_by(user_id=user_id).first()
    emotion = EmotionEvent.query.filter_by(user_id=user_id).order_by(EmotionEvent.created_at.desc()).first()

    return jsonify({
        "mood_points": [{"score": m.mood_score, "at": m.created_at.isoformat()} for m in moods],
        "latest_risk": risk.risk_level if risk else "Unknown",
        "digital_twin": {
            "state": twin.current_state if twin else "unknown",
            "trend": twin.trend_status if twin else "unknown",
        },
        "latest_multimodal": {
            "face_emotion": emotion.face_emotion if emotion else "unknown",
            "voice_stress_score": emotion.voice_stress_score if emotion else None,
            "fused_distress_score": emotion.fused_distress_score if emotion else None,
        },
    })
