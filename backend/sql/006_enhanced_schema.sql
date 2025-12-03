-- ============================================================================
-- Enhanced Schema for Comprehensive Semantic Tagging
-- ============================================================================
-- This migration adds new columns to the insights table for richer semantic
-- analysis and creates tables for trend detection.
-- ============================================================================

-- Expand insights table with new semantic tag columns
DO $$ 
BEGIN
    -- Add sub_sector column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'sub_sector') THEN
        ALTER TABLE insights ADD COLUMN sub_sector TEXT;
    END IF;
    
    -- Add time_horizon column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'time_horizon') THEN
        ALTER TABLE insights ADD COLUMN time_horizon TEXT;
    END IF;
    
    -- Add confidence_level column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'confidence_level') THEN
        ALTER TABLE insights ADD COLUMN confidence_level NUMERIC;
    END IF;
    
    -- Add relevance_score column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'relevance_score') THEN
        ALTER TABLE insights ADD COLUMN relevance_score NUMERIC;
    END IF;
    
    -- Add sentiment column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'sentiment') THEN
        ALTER TABLE insights ADD COLUMN sentiment TEXT;
    END IF;
    
    -- Add key_points column (JSON array)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'key_points') THEN
        ALTER TABLE insights ADD COLUMN key_points JSONB;
    END IF;
    
    -- Add potential_catalysts column (JSON array)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'potential_catalysts') THEN
        ALTER TABLE insights ADD COLUMN potential_catalysts JSONB;
    END IF;
    
    -- Add risk_factors column (JSON array)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'risk_factors') THEN
        ALTER TABLE insights ADD COLUMN risk_factors JSONB;
    END IF;
    
    -- Add market_alignment_score column (for later use)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'insights' AND column_name = 'market_alignment_score') THEN
        ALTER TABLE insights ADD COLUMN market_alignment_score NUMERIC;
    END IF;
END $$;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_insights_sub_sector ON insights(sub_sector) WHERE sub_sector IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_insights_time_horizon ON insights(time_horizon) WHERE time_horizon IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_insights_sentiment ON insights(sentiment) WHERE sentiment IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_insights_relevance_score ON insights(relevance_score DESC) WHERE relevance_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_insights_confidence_level ON insights(confidence_level DESC) WHERE confidence_level IS NOT NULL;

-- ============================================================================
-- Create trends table for community and market trend detection
-- ============================================================================
CREATE TABLE IF NOT EXISTS trends (
    id BIGSERIAL PRIMARY KEY,
    trend_type TEXT NOT NULL, -- market, community, sector, ticker
    ticker TEXT, -- optional, for ticker-specific trends
    sector TEXT, -- optional, for sector-specific trends
    description TEXT NOT NULL,
    confidence NUMERIC, -- 0-1 confidence score
    sentiment_direction TEXT, -- bullish, bearish, mixed
    time_window TEXT NOT NULL, -- 1h, 4h, 24h, 7d
    key_themes JSONB, -- array of key themes
    supporting_post_ids UUID[], -- array of post IDs that support this trend
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ -- trends can expire
);

-- Add indexes for trends table
CREATE INDEX IF NOT EXISTS idx_trends_type ON trends(trend_type);
CREATE INDEX IF NOT EXISTS idx_trends_ticker ON trends(ticker) WHERE ticker IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_trends_sector ON trends(sector) WHERE sector IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_trends_created ON trends(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trends_active ON trends(expires_at) WHERE expires_at IS NULL OR expires_at > NOW();

-- Enable RLS on trends table
ALTER TABLE trends ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read trends
CREATE POLICY "Trends are viewable by authenticated users" ON trends
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- ============================================================================
-- Create post_trends junction table for many-to-many relationship
-- ============================================================================
CREATE TABLE IF NOT EXISTS post_trends (
    id BIGSERIAL PRIMARY KEY,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    trend_id BIGINT NOT NULL REFERENCES trends(id) ON DELETE CASCADE,
    relevance_score NUMERIC, -- how relevant is this post to the trend
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, trend_id)
);

-- Add indexes for post_trends
CREATE INDEX IF NOT EXISTS idx_post_trends_post_id ON post_trends(post_id);
CREATE INDEX IF NOT EXISTS idx_post_trends_trend_id ON post_trends(trend_id);

-- Enable RLS on post_trends
ALTER TABLE post_trends ENABLE ROW LEVEL SECURITY;

-- Allow all authenticated users to read post_trends
CREATE POLICY "Post trends are viewable by authenticated users" ON post_trends
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- ============================================================================
-- Function to get active trends by type
-- ============================================================================
CREATE OR REPLACE FUNCTION get_active_trends(
    p_trend_type TEXT DEFAULT NULL,
    p_time_window TEXT DEFAULT NULL,
    p_limit INT DEFAULT 20
)
RETURNS TABLE(
    id BIGINT,
    trend_type TEXT,
    ticker TEXT,
    sector TEXT,
    description TEXT,
    confidence NUMERIC,
    sentiment_direction TEXT,
    time_window TEXT,
    key_themes JSONB,
    post_count INT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.trend_type,
        t.ticker,
        t.sector,
        t.description,
        t.confidence,
        t.sentiment_direction,
        t.time_window,
        t.key_themes,
        array_length(t.supporting_post_ids, 1) as post_count,
        t.created_at
    FROM trends t
    WHERE (t.expires_at IS NULL OR t.expires_at > NOW())
      AND (p_trend_type IS NULL OR t.trend_type = p_trend_type)
      AND (p_time_window IS NULL OR t.time_window = p_time_window)
    ORDER BY t.confidence DESC, t.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Function to get trends for a specific ticker
-- ============================================================================
CREATE OR REPLACE FUNCTION get_ticker_trends(
    p_ticker TEXT,
    p_limit INT DEFAULT 10
)
RETURNS TABLE(
    id BIGINT,
    description TEXT,
    confidence NUMERIC,
    sentiment_direction TEXT,
    time_window TEXT,
    key_themes JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.description,
        t.confidence,
        t.sentiment_direction,
        t.time_window,
        t.key_themes,
        t.created_at
    FROM trends t
    WHERE t.ticker = p_ticker
      AND (t.expires_at IS NULL OR t.expires_at > NOW())
    ORDER BY t.confidence DESC, t.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;






