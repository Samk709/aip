from ..models.entities import ModerationAudit
from ..db.extensions import db


def create_moderation_audit(user_id: int, message_text: str, is_crisis: bool, matched_terms: list[str]) -> ModerationAudit:
    status = "escalated" if is_crisis else "none"
    row = ModerationAudit(
        user_id=user_id,
        message_text=message_text,
        is_crisis=is_crisis,
        matched_terms=",".join(matched_terms),
        escalation_status=status,
    )
    db.session.add(row)
    return row
