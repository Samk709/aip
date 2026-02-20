-- Example SQL migration for production PostgreSQL deployment.
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email);

CREATE TABLE IF NOT EXISTS emotion_events (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  text_negative_score REAL NOT NULL,
  face_emotion VARCHAR(16) NOT NULL,
  voice_stress_score REAL NOT NULL,
  fused_distress_score REAL NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
