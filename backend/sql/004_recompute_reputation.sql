-- Function: recompute_reputation
-- Purpose: Update user reputation based on post quality and engagement
-- This is called by the ARQ worker cron job

CREATE OR REPLACE FUNCTION recompute_reputation()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    WITH user_stats AS (
        SELECT 
            p.user_id,
            AVG(i.quality_score) as avg_quality,
            COUNT(DISTINCT p.id) as post_count,
            COALESCE(SUM(CASE WHEN pe.type = 'like' THEN 1 ELSE 0 END), 0) as likes,
            COALESCE(SUM(CASE WHEN pe.type = 'dislike' THEN 1 ELSE 0 END), 0) as dislikes
        FROM public.posts p
        JOIN public.insights i ON i.post_id = p.id
        LEFT JOIN public.post_engagement pe ON pe.post_id = p.id
        GROUP BY p.user_id
    )
    UPDATE public.reputation r
    SET 
        overall_score = (
            (COALESCE(us.avg_quality, 0.5) * 0.7) + 
            (LEAST(us.likes, 100) * 0.003) - 
            (LEAST(us.dislikes, 100) * 0.003)
        ),
        updated_at = NOW()
    FROM user_stats us
    WHERE r.user_id = us.user_id;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION recompute_reputation() TO service_role;





