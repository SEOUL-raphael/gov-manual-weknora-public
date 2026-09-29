-- Run after WeKnora migrations, on this project's dedicated DB only.
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx_2048
ON embeddings USING hnsw ((embedding::halfvec(2048)) halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64) WHERE dimension = 2048;
