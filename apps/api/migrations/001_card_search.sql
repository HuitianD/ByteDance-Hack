CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS viralcraft_cards (
  id text PRIMARY KEY,
  owner_id text NOT NULL,
  is_public boolean NOT NULL DEFAULT false,
  content jsonb NOT NULL,
  content_hash text NOT NULL,
  embedding_model text NOT NULL,
  embedding vector(1024) NOT NULL
);
CREATE INDEX IF NOT EXISTS viralcraft_cards_owner ON viralcraft_cards(owner_id);
