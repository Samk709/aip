# Mental Health Risk Prediction + AI Support Chatbot System (Enhanced Blueprint)

## 1) System Architecture

### A. Core architecture blocks
1. **Client Layer**
   - Web app (HTML/CSS/JS) for chat, assessments, dashboard.
   - Mobile app (Flutter or React Native) for daily check-ins, voice journaling, notifications.
2. **Backend API Layer (Flask)**
   - Authentication, user management, questionnaire APIs, chat APIs, analytics APIs.
   - Serves as orchestrator between NLP/ML modules and databases.
3. **Conversation Layer**
   - **Rasa** for dialogue management (intents, entities, flow control).
   - **GPT-based response module** for dynamic, empathetic conversations under safety policy.
   - Hybrid strategy: Rasa policy + GPT generation + safety filter.
4. **Prediction Layer**
   - **Depression severity classifier (BERT-based NLP)** from chat text and questionnaire features.
   - Severity classes:
     - No symptoms
     - Mild
     - Moderate/Severe
   - **Risk score engine** maps outputs to Low/Medium/High intervention tiers.
5. **Emotion Intelligence Layer**
   - Text emotion + sentiment (BERT).
   - Face emotion detection (OpenCV: happy/sad/neutral).
   - Voice sentiment/stress analysis (prosodic + spectral audio features).
   - Multimodal fusion combines text + face + voice for stronger signal confidence.
6. **Digital Twin Layer (Personal Mental Health Twin)**
   - Creates a virtual longitudinal profile per user.
   - Stores history of mood, severity, triggers, intervention response.
   - Tracks change over time and generates personalized recommendations.
7. **Intervention & Alerting Layer**
   - Suggests breathing/grounding exercises.
   - Crisis alert simulation for severe risk.
   - Automated email alert + emergency resources panel when high-risk criteria are met.
8. **Data Layer**
   - Primary option: PostgreSQL for structured data.
   - Optional document/event store: MongoDB or Firebase for real-time mood stream.
   - Model/artifact storage for versioning.
9. **Analytics & Monitoring Layer**
   - Weekly mood trend graphs, severity trajectory, chatbot usage analytics.
   - Admin panel for drift monitoring, alert counts, and intervention outcomes.

### B. End-to-end runtime flow
1. User submits PHQ-style check-in + chat/voice/video input.
2. NLP and multimodal modules compute text sentiment, facial emotion, voice stress.
3. BERT classifier predicts depression severity (`No symptoms`, `Mild`, `Moderate/Severe`).
4. Risk engine derives Low/Medium/High risk tier.
5. Rasa + GPT generates safe contextual response.
6. Digital Twin updates state/history and adapts recommendations.
7. If severe/high-risk: trigger risk alert email + show emergency contacts/resources.
8. Dashboard updates weekly trend and worsening indicators in real time.

---

## 2) Step-by-Step Development Plan

### Phase 0: Ethics, boundaries, and data governance
- Add explicit disclaimer: tool is decision-support, not diagnosis.
- Configure consent, anonymization, and retention policy.
- Add safety escalation and emergency resource workflows.

### Phase 1: Dataset and labeling pipeline
- Prepare **Extended Distress Analysis Interview Corpus**.
- Use PHQ score ranges to label classes:
  - 0: No symptoms
  - 1: Mild
  - 2: Moderate/Severe
- Build preprocessing scripts for text normalization and metadata cleaning.

### Phase 2: Backend + Rasa foundation
- Build Flask APIs for auth, sessions, chat, assessments, dashboard data.
- Set up Rasa NLU intents/entities and core dialogue policies.
- Add audit logging and message/event pipelines.

### Phase 3: BERT depression severity model
- Fine-tune BERT on labeled corpus.
- Evaluate with class-wise precision/recall/F1 and confusion matrix.
- Export model to inference service.

### Phase 4: Multimodal emotion module
- Text emotion/sentiment inference (BERT head).
- Face emotion detection with OpenCV (happy/sad/neutral).
- Voice stress/sentiment pipeline (e.g., librosa + classifier).
- Implement score fusion logic.

### Phase 5: GPT conversational intelligence integration
- Add GPT response service for dynamic replies.
- Keep classification/risk system separate from generation system.
- Enforce policy filters (self-harm/crisis safe responses + escalation prompts).

### Phase 6: Digital Twin and personalized recommendations
- Implement digital twin profile state machine.
- Track trend deltas (improving/stable/worsening).
- Generate tailored recommendations from historical response patterns.

### Phase 7: Dashboard + alerting + multilingual
- Build mood trend graphs (weekly and monthly).
- Add risk alert system (email + in-app warning + emergency resources).
- Add multilingual support (English + Hindi) for UI and chatbot responses.

### Phase 8: Mobile app delivery + deployment
- Build Flutter/React Native companion app.
- Connect push notifications for check-ins/alerts.
- Containerize and deploy all services.

### Phase 9: Evaluation and paper-ready reporting
- Report model quality and usability outcomes.
- If reproducing your paper baseline, include:
  - **69% accuracy** (classification benchmark)
  - **84% usability score** (SUS/UX benchmark)
- Include ablation results (text-only vs multimodal vs digital twin personalization).

---

## 3) Recommended Datasets

### Primary dataset
1. **Extended Distress Analysis Interview Corpus**
   - Main supervised dataset.
   - Use PHQ score mapping to create severity labels.

### Supporting datasets
2. **GoEmotions** (text emotion enhancement)
3. **EmpatheticDialogues** (supportive response style)
4. **RAVDESS / CREMA-D** (voice emotion pretraining)
5. **FER2013 / CK+** (facial emotion pretraining for OpenCV pipeline)

> Use only datasets with academic/commercial-compatible licenses as needed by your institution.

---

## 4) Model Selection

### A. Depression severity classifier
- **Model**: BERT/RoBERTa fine-tuned on interview corpus.
- **Target labels**: No symptoms, Mild, Moderate/Severe.
- **Metrics**: Accuracy, macro-F1, class recall (especially Moderate/Severe).

### B. Multimodal emotion/stress models
- **Text**: BERT emotion head.
- **Face**: OpenCV + lightweight CNN classifier.
- **Voice**: acoustic features (MFCC, pitch, energy) + classifier (SVM/LightGBM/CRNN).
- **Fusion**: weighted late fusion for final emotional distress confidence.

### C. Conversational engine
- **Rasa** for intent/flow consistency.
- **GPT layer** for rich natural responses.
- **Safety policy module** (hard filters + escalation templates).

### D. Risk scoring engine
- Aggregate severity class + multimodal stress + trend deltas into risk tiers:
  - Low
  - Medium
  - High

---

## 5) Folder Structure (Updated)

```text
mental-health-fyp/
  frontend-web/
    templates/
    static/
      css/
      js/
  mobile-app/
    flutter_or_react_native/
  backend-flask/
    app/
      api/
      services/
      models/
      db/
      alerts/
      digital_twin/
      multilingual/
    tests/
  rasa-bot/
    data/
    domain.yml
    config.yml
    actions/
  ml-nlp/
    bert_severity/
    text_emotion/
    face_emotion_opencv/
    voice_sentiment/
    fusion/
    inference/
  data/
    raw/
    processed/
    labels/
  dashboard/
    analytics/
    charts/
  infra/
    docker/
    ci-cd/
  docs/
    architecture/
    results/
    ethics/
```

---

## 6) Database Schema

### Option A: PostgreSQL (recommended core)
1. `users` (`id`, `email`, `password_hash`, `preferred_language`, `created_at`)
2. `assessments` (`id`, `user_id`, `phq_score`, `severity_label`, `created_at`)
3. `chat_sessions` (`id`, `user_id`, `started_at`, `ended_at`)
4. `chat_messages` (`id`, `session_id`, `sender`, `text`, `intent`, `sentiment`, `created_at`)
5. `emotion_events` (`id`, `user_id`, `text_emotion`, `face_emotion`, `voice_stress`, `fusion_score`, `created_at`)
6. `risk_events` (`id`, `user_id`, `severity_class`, `risk_level`, `risk_score`, `created_at`)
7. `digital_twin_state` (`user_id`, `baseline_state`, `current_state`, `trend_status`, `updated_at`)
8. `interventions` (`id`, `user_id`, `type`, `recommendation`, `accepted`, `created_at`)
9. `alerts` (`id`, `user_id`, `alert_type`, `channel_email`, `status`, `created_at`)
10. `mood_logs` (`id`, `user_id`, `mood_score`, `note`, `created_at`)

### Option B: MongoDB/Firebase (real-time mood stream)
- Store high-frequency mood time-series and UI live updates.
- Sync critical records back to PostgreSQL for reliable reporting.

---

## 7) Deployment Steps

1. Containerize Flask API, Rasa server, ML inference services, dashboard.
2. Deploy on cloud VM/Kubernetes with reverse proxy (Nginx).
3. Set managed database (PostgreSQL) + optional Firebase/MongoDB.
4. Configure email provider (SendGrid/SES) for risk alert notifications.
5. Enable HTTPS, auth token security, API rate limiting, encrypted secrets.
6. Set CI/CD for test, build, deploy.
7. Add monitoring (Grafana/Prometheus or cloud monitoring).

---

## 8) Future Scope Enhancements

1. Personalized intervention using reinforcement learning.
2. More facial emotions beyond happy/sad/neutral.
3. Advanced speech biomarkers for relapse prediction.
4. Wearables integration (sleep/activity/HRV).
5. More languages beyond English/Hindi.
6. Counselor dashboard and triage queue.
7. Federated learning for privacy-preserving updates.

---

## 9) Suggested Technology Stack (as requested)

- **Chatbot framework**: Rasa + GPT augmentation.
- **NLP/Classifier**: BERT (severity + sentiment/emotion).
- **Backend**: Flask.
- **Frontend (web)**: HTML/CSS/JS.
- **Face emotion**: OpenCV.
- **Voice analysis**: Python audio stack (librosa, pyAudioAnalysis, torchaudio).
- **Database**: PostgreSQL + optional Firebase/MongoDB for live mood streams.
- **Mobile**: Flutter or React Native.

---

## 10) Expected Paper/Project Results Section Template

- **Classification Accuracy**: 69% (baseline/report reference).
- **Usability Score**: 84% (user study reference).
- Include additional results:
  - Class-wise F1 for No symptoms / Mild / Moderate-Severe.
  - Multimodal gain over text-only baseline.
  - Alert precision and intervention acceptance rate.

---

## Important Disclaimer
This system is a **decision-support and self-help platform**, not a medical diagnosis system. It must always provide emergency resources and recommend professional help for severe risk indicators.
