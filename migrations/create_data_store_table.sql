CREATE TABLE IF NOT EXISTS data_store (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  filename TEXT NOT NULL,
  content JSONB NOT NULL,
  data_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_data_store_created_at ON data_store(created_at);
