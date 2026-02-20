CREATE TABLE IF NOT EXISTS moderation_audit (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  message_text TEXT NOT NULL,
  is_crisis BOOLEAN DEFAULT FALSE,
  matched_terms TEXT,
  escalation_status VARCHAR(32) DEFAULT 'none',
  created_at TIMESTAMP DEFAULT NOW()
);
