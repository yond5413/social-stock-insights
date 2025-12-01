-- ============================================================================
-- Ticker Sentiment with Engagement Weighting
-- ============================================================================
-- This migration creates an RPC function to calculate engagement-weighted
-- sentiment for a specific ticker, ensuring ALL posts are counted.
-- ============================================================================

-- Create function to get engagement-weighted sentiment for a ticker
CREATE OR REPLACE FUNCTION get_ticker_sentiment_with_engagement(
    p_ticker TEXT,
    p_days INT DEFAULT 30
)
RETURNS TABLE(
    ticker TEXT,
    total_posts INT,
    processed_posts INT,
    pending_posts INT,
    bullish_count INT,
    bearish_count INT,
    neutral_count INT,
    weighted_bullish NUMERIC,
    weighted_bearish NUMERIC,
    weighted_neutral NUMERIC,
    avg_engagement NUMERIC,
    confidence_level TEXT,
    top_themes JSONB
) AS $$
DECLARE
    v_threshold TIMESTAMPTZ;
BEGIN
    v_threshold := NOW() - (p_days || ' days')::INTERVAL;
    
    RETURN QUERY
    WITH post_engagement_agg AS (
        -- Aggregate engagement metrics by post
        SELECT 
            post_id,
            COUNT(*) FILTER (WHERE type = 'like') as like_count,
            COUNT(*) FILTER (WHERE type = 'dislike') as dislike_count,
            COUNT(*) FILTER (WHERE type = 'comment') as comment_count
        FROM post_engagement
        GROUP BY post_id
    ),
    ticker_posts AS (
        -- Get all posts for this ticker with engagement data
        SELECT 
            p.id,
            p.llm_status,
            p.created_at,
            COALESCE(p.view_count, 0) as view_count,
            COALESCE(e.like_count, 0) as like_count,
            COALESCE(e.comment_count, 0) as comment_count,
            i.sentiment,
            i.key_points,
            -- Calculate engagement score with null safety
            (
                COALESCE(p.view_count, 0) * 0.01 +
                COALESCE(e.like_count, 0) * 0.5 +
                COALESCE(e.comment_count, 0) * 1.0
            ) as engagement_raw
        FROM posts p
        LEFT JOIN post_engagement_agg e ON p.id = e.post_id
        LEFT JOIN insights i ON p.id = i.post_id
        WHERE p.tickers @> ARRAY[p_ticker]
          AND p.created_at >= v_threshold
    ),
    sentiment_calc AS (
        -- Calculate weighted sentiment
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE llm_status = 'processed') as processed,
            COUNT(*) FILTER (WHERE llm_status = 'pending') as pending,
            
            -- Simple counts
            COUNT(*) FILTER (WHERE sentiment = 'bullish') as bullish_cnt,
            COUNT(*) FILTER (WHERE sentiment = 'bearish') as bearish_cnt,
            COUNT(*) FILTER (WHERE sentiment = 'neutral' OR sentiment IS NULL) as neutral_cnt,
            
            -- Weighted counts (base weight 1.0 + engagement bonus)
            SUM(
                CASE WHEN sentiment = 'bullish' 
                THEN 1.0 + LN(1 + engagement_raw)
                ELSE 0 END
            ) as weighted_bull,
            SUM(
                CASE WHEN sentiment = 'bearish' 
                THEN 1.0 + LN(1 + engagement_raw)
                ELSE 0 END
            ) as weighted_bear,
            SUM(
                CASE WHEN sentiment = 'neutral' OR sentiment IS NULL
                THEN 1.0 + LN(1 + engagement_raw)
                ELSE 0 END
            ) as weighted_neut,
            
            -- Average engagement for confidence calculation
            AVG(view_count + like_count * 5 + comment_count * 10) as avg_eng
        FROM ticker_posts
    ),
    themes_agg AS (
        SELECT jsonb_agg(DISTINCT elem) as themes
        FROM ticker_posts, jsonb_array_elements(key_points) elem
        WHERE key_points IS NOT NULL
    ),
    confidence AS (
        -- Determine confidence level
        SELECT 
            CASE 
                WHEN processed = 0 THEN 'pending'
                WHEN processed >= 10 AND avg_eng > 50 THEN 'high'
                WHEN processed >= 3 THEN 'medium'
                ELSE 'low'
            END as conf_level
        FROM sentiment_calc
    )
    SELECT 
        p_ticker,
        COALESCE(sc.total, 0)::INT,
        COALESCE(sc.processed, 0)::INT,
        COALESCE(sc.pending, 0)::INT,
        COALESCE(sc.bullish_cnt, 0)::INT,
        COALESCE(sc.bearish_cnt, 0)::INT,
        COALESCE(sc.neutral_cnt, 0)::INT,
        COALESCE(sc.weighted_bull, 0)::NUMERIC,
        COALESCE(sc.weighted_bear, 0)::NUMERIC,
        COALESCE(sc.weighted_neut, 0)::NUMERIC,
        COALESCE(sc.avg_eng, 0)::NUMERIC,
        COALESCE(c.conf_level, 'low'),
        COALESCE(t.themes, '[]'::JSONB)
    FROM sentiment_calc sc
    CROSS JOIN confidence c
    CROSS JOIN themes_agg t;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION get_ticker_sentiment_with_engagement(TEXT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION get_ticker_sentiment_with_engagement(TEXT, INT) TO anon;

-- Add index for post_engagement if not exists
CREATE INDEX IF NOT EXISTS idx_post_engagement_post_type 
ON post_engagement(post_id, type);

-- Add composite index for insights
CREATE INDEX IF NOT EXISTS idx_insights_post_sentiment 
ON insights(post_id, sentiment) WHERE sentiment IS NOT NULL;

-- Comment for documentation
COMMENT ON FUNCTION get_ticker_sentiment_with_engagement IS 
'Calculate engagement-weighted sentiment for a ticker. Uses LEFT JOINs to ensure all posts are counted, with base weight 1.0 + engagement bonus.';




