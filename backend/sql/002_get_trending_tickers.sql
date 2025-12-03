-- Function: get_trending_tickers
-- Purpose: Get trending tickers based on mention count in the last N hours
-- This replaces the query in backend/app/routers/market.py:get_trending()

CREATE OR REPLACE FUNCTION get_trending_tickers(
    p_hours int DEFAULT 24,
    p_limit int DEFAULT 10
)
RETURNS TABLE (
    ticker text,
    count bigint
) 
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t as ticker,
        COUNT(*) as count 
    FROM public.posts, UNNEST(tickers) as t
    WHERE created_at > NOW() - (p_hours || ' hours')::interval 
    GROUP BY t 
    ORDER BY count DESC 
    LIMIT p_limit;
END;
$$;

-- Grant execute permission to authenticated users and anon (for public trending)
GRANT EXECUTE ON FUNCTION get_trending_tickers(int, int) TO authenticated;
GRANT EXECUTE ON FUNCTION get_trending_tickers(int, int) TO anon;
GRANT EXECUTE ON FUNCTION get_trending_tickers(int, int) TO service_role;







