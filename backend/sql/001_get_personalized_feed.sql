-- Function: get_personalized_feed
-- Purpose: Get personalized feed with ranking based on quality, reputation, and engagement
-- This replaces the complex query in backend/app/routers/feed.py

CREATE OR REPLACE FUNCTION get_personalized_feed(
    p_user_id uuid,
    p_limit int DEFAULT 20,
    p_offset int DEFAULT 0
)
RETURNS TABLE (
    id text,
    user_id text,
    content text,
    tickers text[],
    llm_status text,
    created_at timestamptz,
    summary text,
    quality_score numeric,
    final_score numeric
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH latest_insights AS (
        SELECT DISTINCT ON (post_id)
            post_id,
            quality_score,
            summary,
            explanation,
            created_at
        FROM public.insights
        ORDER BY post_id, created_at DESC
    ),
    engagement AS (
        SELECT
            post_id,
            COUNT(*) FILTER (WHERE type = 'like') as likes,
            COUNT(*) FILTER (WHERE type = 'dislike') as dislikes
        FROM public.post_engagement
        GROUP BY post_id
    )
    SELECT
        p.id::text,
        p.user_id::text,
        p.content,
        p.tickers,
        p.llm_status,
        p.created_at,
        li.summary,
        li.quality_score,
        (
            COALESCE(li.quality_score, 0) * 0.5 +
            COALESCE(r.overall_score, 0) * 0.2 +
            COALESCE((COALESCE(e.likes, 0) - COALESCE(e.dislikes, 0))::numeric, 0) * 0.1
        ) as final_score
    FROM public.posts p
    LEFT JOIN latest_insights li ON li.post_id = p.id
    LEFT JOIN public.reputation r ON r.user_id = p.user_id
    LEFT JOIN engagement e ON e.post_id = p.id
    ORDER BY final_score DESC, p.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION get_personalized_feed(uuid, int, int) TO authenticated;
GRANT EXECUTE ON FUNCTION get_personalized_feed(uuid, int, int) TO service_role;


