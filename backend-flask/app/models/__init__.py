from .entities import (
    User,
    Assessment,
    MoodLog,
    ChatMessage,
    RiskEvent,
    DigitalTwinState,
    EmotionEvent,
    ModerationAudit,
)


def init_models():
    _ = (User, Assessment, MoodLog, ChatMessage, RiskEvent, DigitalTwinState, EmotionEvent, ModerationAudit)
