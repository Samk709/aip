from datetime import datetime
from ..db.extensions import db


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(32), default="user")
    preferred_language = db.Column(db.String(10), default="en")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Assessment(db.Model):
    __tablename__ = "assessments"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    phq_score = db.Column(db.Integer, nullable=False)
    severity_label = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MoodLog(db.Model):
    __tablename__ = "mood_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mood_score = db.Column(db.Integer, nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sender = db.Column(db.String(16), nullable=False)
    text = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RiskEvent(db.Model):
    __tablename__ = "risk_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    severity_class = db.Column(db.String(32), nullable=False)
    risk_level = db.Column(db.String(16), nullable=False)
    risk_score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DigitalTwinState(db.Model):
    __tablename__ = "digital_twin_state"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    baseline_state = db.Column(db.String(32), default="unknown")
    current_state = db.Column(db.String(32), default="stable")
    trend_status = db.Column(db.String(32), default="stable")
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
