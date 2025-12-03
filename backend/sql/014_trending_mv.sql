-- Migration: Create Materialized View for Trending Tickers
-- Purpose: Cache expensive trending ticker calculations

-- Create Materialized View
CREATE MATERIALIZED VIEW IF NOT EXISTS trending_tickers_mv AS
WITH expanded_posts AS (
    SELECT 
        unnest(tickers) as ticker,
        user_id,
        created_at
    FROM posts
    WHERE created_at >= NOW() - INTERVAL '24 hours'
)
SELECT 
    ticker,
    COUNT(*) AS post_count,
    COUNT(DISTINCT user_id) as unique_authors,
    MAX(created_at) as last_post_at
FROM expanded_posts
WHERE ticker IS NOT NULL
GROUP BY ticker
ORDER BY post_count DESC;

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_trending_tickers_mv_post_count ON trending_tickers_mv(post_count DESC);
CREATE INDEX IF NOT EXISTS idx_trending_tickers_mv_ticker ON trending_tickers_mv(ticker);

-- Function to refresh the view
CREATE OR REPLACE FUNCTION refresh_trending_tickers()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY trending_tickers_mv;
END;
$$ LANGUAGE plpgsql;

-- Grant access to authenticated users
GRANT SELECT ON trending_tickers_mv TO authenticated;
GRANT EXECUTE ON FUNCTION refresh_trending_tickers TO authenticated;
