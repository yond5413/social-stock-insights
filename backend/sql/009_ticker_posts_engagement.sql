-- ============================================================================
-- Ticker Posts Ranked by Engagement
-- ============================================================================
-- This migration creates an RPC function to fetch posts for a ticker
-- ranked by engagement, with robust handling of missing data.
-- ============================================================================

-- Create function to get engagement-ranked posts for a ticker
CREATE OR REPLACE FUNCTION get_ticker_posts_by_engagement(
    p_ticker TEXT,
    p_limit INT DEFAULT 20,
    p_offset INT DEFAULT 0
)
RETURNS TABLE(
    post_id UUID,
    user_id UUID,
    content TEXT,
    tickers TEXT[],
    llm_status TEXT,
    created_at TIMESTAMPTZ,
    view_count INT,
    like_count INT,
    comment_count INT,
    engagement_score NUMERIC,
    summary TEXT,
    explanation TEXT,
    sentiment TEXT,
    quality_score NUMERIC,
    insight_type TEXT,
    sector TEXT,
    author_reputation NUMERIC,
    is_processing BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    WITH post_engagement_agg AS (
        -- Aggregate engagement metrics by post
        SELECT 
            post_id,
            COUNT(*) FILTER (WHERE type = 'like') as likes,
            COUNT(*) FILTER (WHERE type = 'dislike') as dislikes,
            COUNT(*) FILTER (WHERE type = 'comment') as comments
        FROM post_engagement
        GROUP BY post_id
    )
    SELECT 
        p.id as post_id,
        p.user_id,
        p.content,
        p.tickers,
        p.llm_status,
        p.created_at,
        COALESCE(p.view_count, 0)::INT as view_count,
        COALESCE(e.likes, 0)::INT as like_count,
        COALESCE(e.comments, 0)::INT as comment_count,
        -- Calculate engagement score with null safety
        (
            COALESCE(p.view_count, 0) * 0.1 +
            COALESCE(e.likes, 0) * 5.0 +
            COALESCE(e.comments, 0) * 10.0
        )::NUMERIC as engagement_score,
        i.summary,
        i.explanation,
        i.sentiment,
        i.quality_score,
        i.insight_type,
        i.sector,
        COALESCE(r.overall_score, 0)::NUMERIC as author_reputation,
        (p.llm_status != 'processed')::BOOLEAN as is_processing
    FROM posts p
    LEFT JOIN post_engagement_agg e ON p.id = e.post_id
    LEFT JOIN insights i ON p.id = i.post_id
    LEFT JOIN reputation r ON p.user_id = r.user_id
    WHERE p.tickers @> ARRAY[p_ticker]
    ORDER BY 
        -- Processed posts first, then pending
        CASE WHEN p.llm_status = 'processed' THEN 0 ELSE 1 END,
        -- Higher engagement first
        (
            COALESCE(p.view_count, 0) * 0.1 +
            COALESCE(e.likes, 0) * 5.0 +
            COALESCE(e.comments, 0) * 10.0
        ) DESC,
        -- Most recent first as tiebreaker
        p.created_at DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION get_ticker_posts_by_engagement(TEXT, INT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_ticker_posts_by_engagement(TEXT, INT, INT) TO anon;

-- Create count function for pagination
CREATE OR REPLACE FUNCTION count_ticker_posts(
    p_ticker TEXT
)
RETURNS INT AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*)
    INTO v_count
    FROM posts
    WHERE tickers @> ARRAY[p_ticker];
    
    RETURN COALESCE(v_count, 0);
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions for count function
GRANT EXECUTE ON FUNCTION count_ticker_posts(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION count_ticker_posts(TEXT) TO anon;

-- Comment for documentation
COMMENT ON FUNCTION get_ticker_posts_by_engagement IS 
'Fetch posts for a ticker ranked by engagement. Uses LEFT JOINs to ensure all posts are returned, even without engagement data. Returns both processed and pending posts.';

COMMENT ON FUNCTION count_ticker_posts IS 
'Count total posts mentioning a ticker for pagination.';





