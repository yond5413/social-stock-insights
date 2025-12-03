-- Function: semantic_search_posts
-- Purpose: Semantic search over posts using pgvector similarity
-- This replaces the query in backend/app/routers/insights.py

CREATE OR REPLACE FUNCTION semantic_search_posts(
    query_embedding vector(1024),
    search_limit int DEFAULT 20
)
RETURNS TABLE (
    id text,
    user_id text,
    content text,
    tickers text[],
    llm_status text,
    created_at timestamptz,
    similarity float
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id::text,
        p.user_id::text,
        p.content,
        p.tickers,
        p.llm_status,
        p.created_at,
        (1 - (pe.embedding <=> query_embedding))::float as similarity
    FROM public.post_embeddings pe
    JOIN public.posts p ON p.id = pe.post_id
    WHERE pe.type = 'content'
    ORDER BY pe.embedding <=> query_embedding
    LIMIT search_limit;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION semantic_search_posts(vector(1024), int) TO authenticated;
GRANT EXECUTE ON FUNCTION semantic_search_posts(vector(1024), int) TO service_role;







