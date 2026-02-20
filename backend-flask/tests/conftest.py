import sys
from pathlib import Path

# Ensure backend-flask/ is on sys.path in local and CI pytest collection contexts.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
