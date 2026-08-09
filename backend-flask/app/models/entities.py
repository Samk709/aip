from datetime import datetime
from ..db.extensions import db
from sqlalchemy_utils import EncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine
import os

DB_ENCRYPTION_KEY = os.environ.get('DB_ENCRYPTION_KEY', 'default-dev-key-1234567890123456') # Must be 32 bytes or robust for AES


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(32), default="user")
    preferred_language = db.Column(db.String(10), default="en")
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Assessment(db.Model):
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    phq_score = db.Column(db.Integer, nullable=False)
    severity_label = db.Column(db.String(32), nullable=False)
    sleep_pattern_score = db.Column(db.Integer, default=5) # 1-10 (1=terrible, 10=excellent)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MoodLog(db.Model):
    __tablename__ = "mood_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mood_score = db.Column(db.Integer, nullable=False)
    note = db.Column(EncryptedType(db.Text, DB_ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sender = db.Column(db.String(16), nullable=False)
    text = db.Column(EncryptedType(db.Text, DB_ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=False)
    sentiment = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RiskEvent(db.Model):
    __tablename__ = "risk_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    severity_class = db.Column(db.String(32), nullable=False)
    risk_level = db.Column(db.String(16), nullable=False)
    suicide_score = db.Column(db.Integer, default=0)
    stress_score = db.Column(db.Integer, default=0)
    recovery_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DigitalTwinState(db.Model):
    __tablename__ = "digital_twin_state"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    baseline_state = db.Column(db.String(32), default="unknown")
    current_state = db.Column(db.String(32), default="stable")
    trend_status = db.Column(db.String(32), default="stable")
    personality_type = db.Column(db.String(64), nullable=True)
    stress_triggers = db.Column(EncryptedType(db.Text, DB_ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True) # Stored as JSON string
    emotional_pattern = db.Column(EncryptedType(db.Text, DB_ENCRYPTION_KEY, AesEngine, 'pkcs5'), nullable=True) # Stored as JSON string
    memory_summary = db.Column(db.Text, nullable=True) # Context-aware bot memory
    gemini_file_uris = db.Column(db.Text, nullable=True) # JSON list of uploaded file URIs
    mhsi_score = db.Column(db.Integer, default=50) # AI Mental Health Safety Index (0-100)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmotionEvent(db.Model):
    __tablename__ = "emotion_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text_negative_score = db.Column(db.Float, nullable=False)
    face_emotion = db.Column(db.String(16), nullable=False)
    voice_stress_score = db.Column(db.Float, nullable=False)
    fused_distress_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ModerationAudit(db.Model):
    __tablename__ = "moderation_audit"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message_text = db.Column(db.Text, nullable=False)
    is_crisis = db.Column(db.Boolean, default=False)
    matched_terms = db.Column(db.Text, nullable=True)
    escalation_status = db.Column(db.String(32), default="none")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RelapsePrediction(db.Model):
    __tablename__ = "relapse_predictions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    prediction_score = db.Column(db.Float, nullable=False) # 0.0 to 1.0 probability of relapse
    time_frame_days = db.Column(db.Integer, default=14)
    contributing_factors = db.Column(db.Text, nullable=True) # JSON list of factors
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BehavioralBiomarker(db.Model):
    __tablename__ = "behavioral_biomarkers"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    typing_speed_wpm = db.Column(db.Float, default=0.0)
    hesitation_time_ms = db.Column(db.Integer, default=0) # Time before sending message
    backspace_count = db.Column(db.Integer, default=0)
    is_late_night = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FederatedLearningUpdate(db.Model):
    __tablename__ = "fl_updates"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    model_version = db.Column(db.String(64), nullable=False)
    weights_hash = db.Column(db.String(256), nullable=False) # Only store hash of local updates
    status = db.Column(db.String(32), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
