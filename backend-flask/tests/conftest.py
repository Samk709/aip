import os
import sys
from pathlib import Path

# Add backend-flask/ directory to Python path so `from app import ...` works in CI/local.
APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["HF_MODEL_NAME"] = ""
