from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def generate_token(secret_key: str, user_id: int, role: str, ttl_hours: int) -> str:
    s = URLSafeTimedSerializer(secret_key=secret_key)
    payload = {
        "user_id": user_id,
        "role": role,
        "exp_hint": (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat(),
    }
    return s.dumps(payload)


def verify_token(secret_key: str, token: str, ttl_hours: int) -> dict | None:
    s = URLSafeTimedSerializer(secret_key=secret_key)
    try:
        payload = s.loads(token, max_age=ttl_hours * 3600)
        return {
            "user_id": int(payload["user_id"]),
            "role": str(payload.get("role", "user")),
        }
    except (BadSignature, SignatureExpired, KeyError, ValueError):
        return None
