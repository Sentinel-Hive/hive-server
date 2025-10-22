CREATE TABLE IF NOT EXISTS data_store (
  id SERIAL PRIMARY KEY,
  content JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_data_store_created_at ON data_store(created_at);
