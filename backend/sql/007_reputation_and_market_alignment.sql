-- ============================================================================
-- Market Alignment and Enhanced Reputation System
-- ============================================================================

-- Create market_alignments table to track prediction accuracy
CREATE TABLE IF NOT EXISTS market_alignments (
    id BIGSERIAL PRIMARY KEY,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    predicted_direction TEXT NOT NULL, -- up, down, neutral
    actual_direction TEXT NOT NULL, -- up, down, neutral
    alignment_score NUMERIC NOT NULL, -- 0-1 score
    price_at_post NUMERIC,
    price_24h_later NUMERIC,
    price_change_percent NUMERIC,
    timing_accuracy TEXT, -- early, on_time, late, wrong
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, ticker)
);

-- Add indexes for market_alignments
CREATE INDEX IF NOT EXISTS idx_market_alignments_user_id ON market_alignments(user_id);
CREATE INDEX IF NOT EXISTS idx_market_alignments_ticker ON market_alignments(ticker);
CREATE INDEX IF NOT EXISTS idx_market_alignments_score ON market_alignments(alignment_score DESC);
CREATE INDEX IF NOT EXISTS idx_market_alignments_created ON market_alignments(created_at DESC);

-- Enable RLS
ALTER TABLE market_alignments ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read market alignments
CREATE POLICY "Market alignments are viewable by authenticated users" ON market_alignments
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Add engagement_score column to reputation if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'reputation' AND column_name = 'engagement_score') THEN
        ALTER TABLE reputation ADD COLUMN engagement_score NUMERIC DEFAULT 0;
    END IF;
END $$;

-- Add consistency_score column to reputation if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'reputation' AND column_name = 'consistency_score') THEN
        ALTER TABLE reputation ADD COLUMN consistency_score NUMERIC DEFAULT 0;
    END IF;
END $$;

-- Create user_predictions table for tracking predictions
CREATE TABLE IF NOT EXISTS user_predictions (
    id BIGSERIAL PRIMARY KEY,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    predicted_direction TEXT NOT NULL,
    confidence NUMERIC, -- 0-1
    outcome TEXT, -- correct, incorrect, neutral, pending
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for user_predictions
CREATE INDEX IF NOT EXISTS idx_user_predictions_user_id ON user_predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_predictions_ticker ON user_predictions(ticker);
CREATE INDEX IF NOT EXISTS idx_user_predictions_outcome ON user_predictions(outcome) WHERE outcome IS NOT NULL;

-- Enable RLS
ALTER TABLE user_predictions ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read predictions
CREATE POLICY "User predictions are viewable by authenticated users" ON user_predictions
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Function to compute historical accuracy for a user
CREATE OR REPLACE FUNCTION compute_historical_accuracy(p_user_id UUID)
RETURNS NUMERIC AS $$
DECLARE
    accuracy NUMERIC;
BEGIN
    SELECT AVG(alignment_score) INTO accuracy
    FROM market_alignments
    WHERE user_id = p_user_id;
    
    RETURN COALESCE(accuracy, 0);
END;
$$ LANGUAGE plpgsql;

-- Enhanced recompute_reputation function
CREATE OR REPLACE FUNCTION recompute_reputation()
RETURNS void AS $$
BEGIN
    -- Update reputation scores for all users with posts
    UPDATE reputation r
    SET 
        overall_score = COALESCE(
            (
                -- Base quality score (40%)
                (SELECT AVG(i.quality_score) * 0.4
                 FROM posts p
                 JOIN insights i ON p.id = i.post_id
                 WHERE p.user_id = r.user_id
                   AND i.quality_score IS NOT NULL
                ) +
                -- Historical accuracy (30%)
                (SELECT AVG(ma.alignment_score) * 0.3
                 FROM market_alignments ma
                 WHERE ma.user_id = r.user_id
                ) +
                -- Engagement score (20%)
                (SELECT COUNT(*) * 0.01
                 FROM post_engagement pe
                 JOIN posts p ON pe.post_id = p.id
                 WHERE p.user_id = r.user_id
                   AND pe.type = 'like'
                 LIMIT 20  -- Cap at 0.2
                ) * 0.2 +
                -- Consistency score (10%) - based on posting frequency
                (SELECT 
                    CASE 
                        WHEN COUNT(*) >= 10 THEN 0.1
                        WHEN COUNT(*) >= 5 THEN 0.05
                        ELSE 0.02
                    END
                 FROM posts p
                 WHERE p.user_id = r.user_id
                   AND p.created_at > NOW() - INTERVAL '30 days'
                ) * 0.1
            ),
            0
        ),
        historical_accuracy = compute_historical_accuracy(r.user_id),
        engagement_score = COALESCE(
            (SELECT COUNT(*) * 0.01
             FROM post_engagement pe
             JOIN posts p ON pe.post_id = p.id
             WHERE p.user_id = r.user_id
               AND pe.type = 'like'
             LIMIT 100
            ),
            0
        ),
        consistency_score = COALESCE(
            (SELECT 
                CASE 
                    WHEN COUNT(*) >= 10 THEN 1.0
                    WHEN COUNT(*) >= 5 THEN 0.5
                    ELSE 0.2
                END
             FROM posts p
             WHERE p.user_id = r.user_id
               AND p.created_at > NOW() - INTERVAL '30 days'
            ),
            0
        ),
        updated_at = NOW()
    WHERE EXISTS (
        SELECT 1 FROM posts WHERE user_id = r.user_id
    );
    
    -- Insert reputation for users who don't have one yet
    INSERT INTO reputation (user_id, overall_score, historical_accuracy, engagement_score, consistency_score)
    SELECT DISTINCT p.user_id, 0.5, 0, 0, 0
    FROM posts p
    WHERE NOT EXISTS (
        SELECT 1 FROM reputation r WHERE r.user_id = p.user_id
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get top users by reputation
CREATE OR REPLACE FUNCTION get_top_users_by_reputation(p_limit INT DEFAULT 20)
RETURNS TABLE(
    user_id UUID,
    username TEXT,
    overall_score NUMERIC,
    historical_accuracy NUMERIC,
    post_count BIGINT,
    avg_quality_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.user_id,
        pr.username,
        r.overall_score,
        r.historical_accuracy,
        COUNT(p.id) as post_count,
        AVG(i.quality_score) as avg_quality_score
    FROM reputation r
    JOIN profiles pr ON r.user_id = pr.id
    LEFT JOIN posts p ON r.user_id = p.user_id
    LEFT JOIN insights i ON p.id = i.post_id
    GROUP BY r.user_id, pr.username, r.overall_score, r.historical_accuracy
    ORDER BY r.overall_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get sector expertise for a user
CREATE OR REPLACE FUNCTION get_user_sector_expertise(p_user_id UUID)
RETURNS TABLE(
    sector TEXT,
    post_count BIGINT,
    avg_quality_score NUMERIC,
    avg_alignment_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.sector,
        COUNT(DISTINCT p.id) as post_count,
        AVG(i.quality_score) as avg_quality_score,
        AVG(ma.alignment_score) as avg_alignment_score
    FROM posts p
    JOIN insights i ON p.id = i.post_id
    LEFT JOIN market_alignments ma ON p.id = ma.post_id
    WHERE p.user_id = p_user_id
      AND i.sector IS NOT NULL
    GROUP BY i.sector
    ORDER BY post_count DESC, avg_quality_score DESC;
END;
$$ LANGUAGE plpgsql;





