-- Function: hybrid_search_posts
-- Purpose: Hybrid search combining semantic (vector) and keyword (full-text) search
-- This improves recall for specific terms (like "GPUs") that might be missed by vector search

CREATE OR REPLACE FUNCTION hybrid_search_posts(
    query_text text,
    query_embedding vector(1024),
    match_threshold float,
    search_limit int
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
    WITH vector_search AS (
        SELECT
            p.id,
            (1 - (pe.embedding <=> query_embedding)) as similarity
        FROM public.post_embeddings pe
        JOIN public.posts p ON p.id = pe.post_id
        WHERE pe.type = 'content'
        AND (1 - (pe.embedding <=> query_embedding)) > match_threshold
        ORDER BY pe.embedding <=> query_embedding
        LIMIT search_limit
    ),
    keyword_search AS (
        SELECT
            p.id,
            0.8 as similarity -- Base score for keyword matches if no vector match
        FROM public.posts p
        WHERE to_tsvector('english', p.content) @@ websearch_to_tsquery('english', query_text)
        LIMIT search_limit
    )
    SELECT
        p.id::text,
        p.user_id::text,
        p.content,
        p.tickers,
        p.llm_status,
        p.created_at,
        COALESCE(vs.similarity, ks.similarity) as similarity
    FROM (
        SELECT vs.id, vs.similarity FROM vector_search vs
        UNION
        SELECT ks.id, ks.similarity FROM keyword_search ks
    ) unique_matches
    JOIN public.posts p ON p.id = unique_matches.id
    LEFT JOIN vector_search vs ON vs.id = unique_matches.id
    LEFT JOIN keyword_search ks ON ks.id = unique_matches.id
    -- Prioritize vector match score if available, otherwise use keyword score
    -- If both exist, we could boost it, but for now max or coalesce is fine.
    -- Let's actually boost if both exist:
    -- similarity = vs.similarity + (0.1 if keyword match else 0)
    ORDER BY 
        (COALESCE(vs.similarity, 0) + (CASE WHEN ks.id IS NOT NULL THEN 0.1 ELSE 0 END)) DESC
    LIMIT search_limit;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION hybrid_search_posts(text, vector(1024), float, int) TO authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search_posts(text, vector(1024), float, int) TO service_role;

