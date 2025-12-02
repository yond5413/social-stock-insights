-- ============================================================================
-- Schema Audit & Performance Enhancements
-- ============================================================================
-- This migration adds missing indexes, triggers, and optimizations for the
-- social stocks insights platform.
-- ============================================================================

-- Add composite index for worker queries (find pending posts efficiently)
CREATE INDEX IF NOT EXISTS idx_posts_llm_status_created 
ON posts(llm_status, created_at DESC) 
WHERE llm_status IN ('pending', 'failed');

-- Add composite index for user feed queries
CREATE INDEX IF NOT EXISTS idx_posts_user_created 
ON posts(user_id, created_at DESC);

-- Add index for ticker searches (GIN index for array containment)
CREATE INDEX IF NOT EXISTS idx_posts_tickers 
ON posts USING GIN(tickers);

-- Add indexes for insights table
CREATE INDEX IF NOT EXISTS idx_insights_quality_score 
ON insights(quality_score DESC) WHERE quality_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_insights_insight_type 
ON insights(insight_type) WHERE insight_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_insights_sector 
ON insights(sector) WHERE sector IS NOT NULL;

-- Add index for market snapshots ticker lookups
CREATE INDEX IF NOT EXISTS idx_market_snapshots_ticker 
ON market_snapshots(ticker, timestamp DESC);

-- Add index for reputation lookups
CREATE INDEX IF NOT EXISTS idx_reputation_overall_score 
ON reputation(overall_score DESC) WHERE overall_score IS NOT NULL;

-- ============================================================================
-- Add view_count column to posts if not exists
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'view_count') THEN
        ALTER TABLE posts ADD COLUMN view_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- ============================================================================
-- Add updated_at column to posts if not exists
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'updated_at') THEN
        ALTER TABLE posts ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- ============================================================================
-- Trigger: Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Function: Notify worker on new post creation
-- ============================================================================
CREATE OR REPLACE FUNCTION notify_new_post()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('new_post', json_build_object(
        'post_id', NEW.id,
        'user_id', NEW.user_id,
        'tickers', NEW.tickers
    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS notify_post_creation ON posts;
CREATE TRIGGER notify_post_creation
    AFTER INSERT ON posts
    FOR EACH ROW
    EXECUTE FUNCTION notify_new_post();

-- ============================================================================
-- Add error_message column to posts for debugging failed processing
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'error_message') THEN
        ALTER TABLE posts ADD COLUMN error_message TEXT;
    END IF;
END $$;

-- ============================================================================
-- Add retry_count column to posts for tracking processing retries
-- ============================================================================
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'posts' AND column_name = 'retry_count') THEN
        ALTER TABLE posts ADD COLUMN retry_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- ============================================================================
-- Materialized view for feed performance (refresh periodically)
-- ============================================================================
DROP MATERIALIZED VIEW IF EXISTS feed_cache CASCADE;
CREATE MATERIALIZED VIEW feed_cache AS
SELECT 
    p.id as post_id,
    p.user_id,
    p.content,
    p.tickers,
    p.created_at,
    i.insight_type,
    i.sector,
    i.quality_score,
    i.summary,
    r.overall_score as author_reputation,
    COALESCE(engagement.like_count, 0) as like_count,
    COALESCE(engagement.comment_count, 0) as comment_count,
    -- Calculate final score
    (
        COALESCE(i.quality_score, 0.5) * 0.4 +
        COALESCE(r.overall_score, 0) * 0.3 +
        (COALESCE(engagement.like_count, 0) * 0.1) +
        (COALESCE(engagement.comment_count, 0) * 0.2)
    ) * EXP(-EXTRACT(EPOCH FROM (NOW() - p.created_at)) / 86400.0) as final_score
FROM posts p
LEFT JOIN insights i ON p.id = i.post_id
LEFT JOIN reputation r ON p.user_id = r.user_id
LEFT JOIN (
    SELECT 
        post_id,
        COUNT(*) FILTER (WHERE type = 'like') as like_count,
        COUNT(*) FILTER (WHERE type = 'comment') as comment_count
    FROM post_engagement
    GROUP BY post_id
) engagement ON p.id = engagement.post_id
WHERE p.llm_status = 'processed';

CREATE INDEX idx_feed_cache_final_score ON feed_cache(final_score DESC);
CREATE INDEX idx_feed_cache_created_at ON feed_cache(created_at DESC);

-- Function to refresh feed cache
CREATE OR REPLACE FUNCTION refresh_feed_cache()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY feed_cache;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Statistics view for monitoring
-- ============================================================================
CREATE OR REPLACE VIEW platform_stats AS
SELECT
    (SELECT COUNT(*) FROM posts) as total_posts,
    (SELECT COUNT(*) FROM posts WHERE llm_status = 'pending') as pending_posts,
    (SELECT COUNT(*) FROM posts WHERE llm_status = 'processed') as processed_posts,
    (SELECT COUNT(*) FROM posts WHERE llm_status = 'failed') as failed_posts,
    (SELECT COUNT(*) FROM profiles) as total_users,
    (SELECT COUNT(*) FROM insights) as total_insights,
    (SELECT AVG(quality_score) FROM insights WHERE quality_score IS NOT NULL) as avg_quality_score,
    (SELECT AVG(latency_ms) FROM llm_audit_logs WHERE created_at > NOW() - INTERVAL '24 hours') as avg_llm_latency_24h,
    (SELECT COUNT(*) FROM llm_audit_logs WHERE created_at > NOW() - INTERVAL '1 hour') as llm_calls_last_hour;





