-- ============================================================================
-- Fix Embedding Dimensions Migration
-- ============================================================================
-- Purpose: Fix post_embeddings table to use vector(1024) instead of vector(1536)
--          to match Cohere embed-english-v3.0 embeddings
-- ============================================================================

-- Drop the existing post_embeddings table if it exists
-- Note: This will delete all existing embeddings. Since the dimension mismatch
-- prevents new embeddings from being inserted, this is safe to do.
DROP TABLE IF EXISTS post_embeddings CASCADE;

-- Recreate post_embeddings table with correct vector dimension (1024)
CREATE TABLE post_embeddings (
    id BIGSERIAL PRIMARY KEY,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('content', 'summary')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, type)
);

-- Create index for vector similarity search
CREATE INDEX idx_post_embeddings_vector ON post_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for post_id lookups
CREATE INDEX idx_post_embeddings_post_id ON post_embeddings(post_id);

-- Create index for type filtering
CREATE INDEX idx_post_embeddings_type ON post_embeddings(type);

-- Enable Row Level Security
ALTER TABLE post_embeddings ENABLE ROW LEVEL SECURITY;

-- Policy: Allow authenticated users to read embeddings
CREATE POLICY "Embeddings are viewable by authenticated users" ON post_embeddings
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Policy: Allow service role to insert/update embeddings
CREATE POLICY "Service role can manage embeddings" ON post_embeddings
    FOR ALL
    USING (auth.role() = 'service_role');

-- Verify the semantic_search_posts function still works with the new dimension
-- (The function already expects vector(1024), so no changes needed)

