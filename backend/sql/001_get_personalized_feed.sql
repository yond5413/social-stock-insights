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
    view_count int,
    like_count int,
    comment_count int,
    engagement_score numeric,
    summary text,
    sentiment text,
    quality_score numeric,
    final_score numeric,
    is_processing boolean
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH latest_insights AS (
        SELECT DISTINCT ON (post_id)
            post_id,
            public.insights.quality_score,
            public.insights.summary,
            public.insights.explanation,
            public.insights.sentiment,
            public.insights.created_at
        FROM public.insights
        ORDER BY post_id, created_at DESC
    ),
    engagement AS (
        SELECT
            post_id,
            COUNT(*) FILTER (WHERE type = 'like') as likes,
            COUNT(*) FILTER (WHERE type = 'dislike') as dislikes,
            COUNT(*) FILTER (WHERE type = 'comment') as comments
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
        COALESCE(p.view_count, 0)::int as view_count,
        COALESCE(e.likes, 0)::int as like_count,
        COALESCE(e.comments, 0)::int as comment_count,
        (
            COALESCE(p.view_count, 0) * 0.1 +
            COALESCE(e.likes, 0) * 5.0 +
            COALESCE(e.comments, 0) * 10.0
        )::numeric as engagement_score,
        li.summary,
        li.sentiment,
        li.quality_score,
        (
            COALESCE(li.quality_score, 0) * 0.5 +
            COALESCE(r.overall_score, 0) * 0.2 +
            COALESCE((COALESCE(e.likes, 0) - COALESCE(e.dislikes, 0))::numeric, 0) * 0.1
        ) as final_score,
        (p.llm_status != 'processed')::boolean as is_processing
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




