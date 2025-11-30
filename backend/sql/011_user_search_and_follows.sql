-- Migration: User Search and Follows
-- Purpose: Add support for user search and follow/unfollow functionality

-- ============================================================================
-- 1. Create follows table
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.follows (
    follower_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, following_id),
    CONSTRAINT no_self_follow CHECK (follower_id != following_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_follows_follower ON public.follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_following ON public.follows(following_id);

-- Enable RLS
ALTER TABLE public.follows ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Everyone can read follows
CREATE POLICY "Follows are viewable by everyone" ON public.follows
    FOR SELECT USING (true);

-- Authenticated users can create follows (must be the follower)
CREATE POLICY "Users can follow others" ON public.follows
    FOR INSERT WITH CHECK (auth.uid() = follower_id);

-- Authenticated users can delete their own follows
CREATE POLICY "Users can unfollow" ON public.follows
    FOR DELETE USING (auth.uid() = follower_id);

-- ============================================================================
-- 2. RPC Function: Search Users
-- ============================================================================
CREATE OR REPLACE FUNCTION public.search_users(
    search_query TEXT,
    max_results INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    username TEXT,
    created_at TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.username,
        p.created_at,
        similarity(p.username, search_query)::FLOAT as similarity
    FROM public.profiles p
    WHERE 
        p.username ILIKE '%' || search_query || '%'
    ORDER BY 
        CASE 
            WHEN p.username ILIKE search_query THEN 1  -- Exact match
            WHEN p.username ILIKE search_query || '%' THEN 2 -- Starts with
            ELSE 3
        END,
        p.username
    LIMIT max_results;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.search_users(TEXT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.search_users(TEXT, INT) TO service_role;

-- ============================================================================
-- 3. RPC Functions: Follow Management
-- ============================================================================

-- Follow a user
CREATE OR REPLACE FUNCTION public.follow_user(target_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.follows (follower_id, following_id)
    VALUES (auth.uid(), target_user_id)
    ON CONFLICT (follower_id, following_id) DO NOTHING;
END;
$$;

GRANT EXECUTE ON FUNCTION public.follow_user(UUID) TO authenticated;

-- Unfollow a user
CREATE OR REPLACE FUNCTION public.unfollow_user(target_user_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    DELETE FROM public.follows
    WHERE follower_id = auth.uid() AND following_id = target_user_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.unfollow_user(UUID) TO authenticated;

-- Get user followers
CREATE OR REPLACE FUNCTION public.get_user_followers(
    target_user_id UUID,
    limit_val INT DEFAULT 20,
    offset_val INT DEFAULT 0
)
RETURNS TABLE (
    user_id UUID,
    username TEXT,
    followed_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.username,
        f.created_at
    FROM public.follows f
    JOIN public.profiles p ON f.follower_id = p.id
    WHERE f.following_id = target_user_id
    ORDER BY f.created_at DESC
    LIMIT limit_val OFFSET offset_val;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_followers(UUID, INT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_followers(UUID, INT, INT) TO service_role;

-- Get user following
CREATE OR REPLACE FUNCTION public.get_user_following(
    target_user_id UUID,
    limit_val INT DEFAULT 20,
    offset_val INT DEFAULT 0
)
RETURNS TABLE (
    user_id UUID,
    username TEXT,
    followed_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.username,
        f.created_at
    FROM public.follows f
    JOIN public.profiles p ON f.following_id = p.id
    WHERE f.follower_id = target_user_id
    ORDER BY f.created_at DESC
    LIMIT limit_val OFFSET offset_val;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_following(UUID, INT, INT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_following(UUID, INT, INT) TO service_role;

-- Get follow stats
CREATE OR REPLACE FUNCTION public.get_user_follow_stats(target_user_id UUID)
RETURNS TABLE (
    followers_count BIGINT,
    following_count BIGINT,
    is_following BOOLEAN -- True if the current auth user is following target_user_id
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM public.follows WHERE following_id = target_user_id) as followers_count,
        (SELECT COUNT(*) FROM public.follows WHERE follower_id = target_user_id) as following_count,
        EXISTS (
            SELECT 1 FROM public.follows 
            WHERE follower_id = auth.uid() AND following_id = target_user_id
        ) as is_following;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_follow_stats(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_user_follow_stats(UUID) TO service_role;
