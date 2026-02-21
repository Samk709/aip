import os


def _build_db_uri() -> str:
    env_uri = os.getenv("DATABASE_URL")
    if env_uri:
        return env_uri

    pg_user = os.getenv("POSTGRES_USER")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    pg_host = os.getenv("POSTGRES_HOST")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_db = os.getenv("POSTGRES_DB")
    if all([pg_user, pg_password, pg_host, pg_db]):
        return f"postgresql+psycopg2://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

    return "sqlite:///mental_health.db"


class Config:
    SQLALCHEMY_DATABASE_URI = _build_db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "24"))

    RASA_WEBHOOK_URL = os.getenv("RASA_WEBHOOK_URL", "")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    HF_MODEL_NAME = os.getenv("HF_MODEL_NAME", "distilbert-base-uncased")

    FER_MODEL_PATH = os.getenv("FER_MODEL_PATH", "models/fer_model.joblib")
    SER_MODEL_PATH = os.getenv("SER_MODEL_PATH", "models/ser_model.joblib")
    BUILD_MARKER = os.getenv("BUILD_MARKER", "PRO-UI-2026-02-21")
