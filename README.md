# Mental Health Risk Prediction + AI Support Chatbot (Enhanced Runnable Starter)

This project now includes **implementation paths** for all previously pending areas:
- BERT prediction service boundary with Hugging Face runtime fallback
- Rasa project scaffold (`rasa-bot/`) + training script
- GPT moderation/policy workflow + audit trail hooks
- OpenCV/librosa-based media analysis hooks (face + voice) + trained FER/SER model loading path
- RBAC-protected admin/counselor APIs + production config/migration/CI scaffolds

---

## 1) Run whole project in VS Code (recommended)

### Step A: Open project
1. Open VS Code.
2. `File -> Open Folder -> /workspace/aip` (or your copied folder).

### Step B: Create Python environment
```bash
cd backend-flask
python -m venv .venv
```
Activate:
- macOS/Linux:
```bash
source .venv/bin/activate
```
- Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```

### Step C: Install dependencies
```bash
pip install -r requirements.txt
# Optional Postgres driver (if using PostgreSQL instead of SQLite):
# pip install -r requirements-db.txt
# Optional heavy ML stack (HF/OpenCV/librosa/torch features):
# pip install -r requirements-ml.txt
```

### Step D: Environment setup
```bash
cp .env.example .env
```
Edit `.env` with your keys/URLs as needed.

### Step E: Run backend
```bash
python run.py
```
Open: `http://localhost:5000`

---

## 2) Optional: run with Docker Compose (backend + postgres)
```bash
docker compose up --build
```

---

## 3) Optional: run/train Rasa
Install Rasa in your environment (separate if preferred), then:
```bash
./scripts/train_rasa.sh
```
To run Rasa API (example):
```bash
cd rasa-bot
rasa run --enable-api --cors "*" -p 5005
```
Set in `.env`:
```env
RASA_WEBHOOK_URL=http://localhost:5005/webhooks/rest/webhook
```

---

## 4) API coverage summary
- Health/config:
  - `GET /api/health`
  - `GET /api/integrations/status`
- Auth/RBAC:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/admin/users` (admin only)
  - `GET /api/admin/moderation-audit` (admin/counselor)
- ML/NLP:
  - `POST /api/assess`
  - `POST /api/nlp/bert/predict`
  - `POST /api/moderation/check`
- Multimodal:
  - `POST /api/multimodal/analyze`
  - `POST /api/media/analyze`
  - `POST /api/media/analyze-frame`
  - `POST /api/media/predict-trained`
- App behavior:
  - `POST /api/mood`
  - `POST /api/chat`
  - `GET /api/dashboard/<user_id>`

---

## 5) Production hardening checklist
1. Replace fallback BERT mapping with your trained model endpoint.
2. Train and deploy Rasa with richer domain/intents/entities.
3. Enable real moderation + audit trails + crisis escalation policy.
4. Replace proxy face/audio heuristics with trained FER + SER models.
5. Use Flask-Migrate/Alembic migrations in CI/CD (`backend-flask/migrations/sql/*` included as starter SQL).
6. Move secrets to vault/secret manager (never commit actual keys).
7. Add HTTPS, reverse proxy, and observability stack.
8. Connect cloud secrets manager and remove local secret fallbacks in production.
9. Enable CI pipeline from `.github/workflows/ci.yml` and add vulnerability scans.

---

## 6) If you move to VS Code now, can you run directly?
**Yes.**
Follow sections 1A–1E exactly. If it fails, common reasons are:
- missing Python 3.10+
- dependency install failed
- Python 3.13 can fail on some optional pinned wheels (use Python 3.10/3.11)
- port 5000/5432 in use
- `.env` misconfiguration
- merge conflict markers still present in files (`<<<<<<<`, `=======`, `>>>>>>>`)

Once backend starts, open `http://localhost:5000` and test auth + assess + multimodal + chat from the UI.


---

## 7) FER/SER trained model usage
Place your trained model files at paths configured in `.env`:
```env
FER_MODEL_PATH=models/fer_model.joblib
SER_MODEL_PATH=models/ser_model.joblib
```
Then call:
- `POST /api/media/predict-trained` with `face_features` and `voice_features`.

## 8) Secrets and Ops doc
See `docs/security/secrets_and_ops.md` for secure deployment checklist.


## 9) Webcam emotion detection in UI
- Login first, open the Face Emotion card, click **Start Camera**, then **Detect Emotion**.
- Allow camera permission in browser when prompted.
