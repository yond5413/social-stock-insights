from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from ..supabase_client import SupabaseClient, CurrentUserId
from ..schemas import FeedItem
from ..ranking_engine import get_ranker, RankingStrategy


router = APIRouter()


@router.get("/", response_model=List[FeedItem])
async def get_feed(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    strategy: str = Query("balanced", description="Ranking strategy: balanced, quality_focused, timely, diverse"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[FeedItem]:
    """
    Enhanced personalized feed with configurable ranking strategies.
    
    Strategies:
    - balanced: Equal weight across all signals
    - quality_focused: Prioritize quality + reputation
    - timely: Prioritize recency + market alignment
    - diverse: Maximize ticker and insight type diversity
    """
    # Fetch posts with all necessary data
    result = supabase.rpc(
        "get_personalized_feed",
        {
            "p_user_id": user_id,
            "p_limit": limit * 2,  # Fetch more for better ranking
            "p_offset": offset,
        }
    ).execute()
    
    if not result.data:
        return []
    
    # Use ensemble ranker to re-rank based on strategy
    ranker = get_ranker(strategy)
    ranked_posts = ranker.rank_posts(result.data)
    
    # Return top results
    return [FeedItem(**post) for post in ranked_posts[:limit]]


@router.get("/personalized", response_model=List[FeedItem])
async def get_personalized_feed(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    limit: int = Query(20, ge=1, le=100),
) -> List[FeedItem]:
    """
    Highly personalized feed based on user's reading history and preferences.
    """
    # Get user's sector interests (from their own posts)
    user_posts = supabase.table("posts").select(
        "tickers"
    ).eq("user_id", user_id).limit(20).execute()
    
    user_tickers = set()
    if user_posts.data:
        for post in user_posts.data:
            if post.get("tickers"):
                user_tickers.update(post["tickers"])
    
    # Build user preferences
    user_preferences = {
        "favorite_tickers": list(user_tickers),
    }
    
    # Fetch feed data
    result = supabase.rpc(
        "get_personalized_feed",
        {
            "p_user_id": user_id,
            "p_limit": limit * 2,
            "p_offset": 0,
        }
    ).execute()
    
    if not result.data:
        return []
    
    # Use personalized ranking
    ranker = get_ranker("balanced")  # Could create a true personalized strategy
    ranked_posts = ranker.rank_posts(result.data, user_preferences)
    
    return [FeedItem(**post) for post in ranked_posts[:limit]]


@router.get("/discovery", response_model=List[FeedItem])
async def get_discovery_feed(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    limit: int = Query(20, ge=1, le=100),
) -> List[FeedItem]:
    """
    Discovery feed showing diverse, high-quality content user hasn't seen.
    Emphasizes variety and discovery over personalization.
    """
    # Fetch high-quality diverse posts
    result = supabase.rpc(
        "get_personalized_feed",
        {
            "p_user_id": user_id,
            "p_limit": limit * 3,  # Fetch more for diversity
            "p_offset": 0,
        }
    ).execute()
    
    if not result.data:
        return []
    
    # Use diverse ranking strategy
    ranker = get_ranker("diverse")
    ranked_posts = ranker.rank_posts(result.data)
    
    return [FeedItem(**post) for post in ranked_posts[:limit]]


@router.get("/timely", response_model=List[FeedItem])
async def get_timely_feed(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    limit: int = Query(20, ge=1, le=100),
) -> List[FeedItem]:
    """
    Real-time market-aligned feed prioritizing recent posts about active tickers.
    Perfect for day traders and active investors.
    """
    # Fetch recent posts
    result = supabase.rpc(
        "get_personalized_feed",
        {
            "p_user_id": user_id,
            "p_limit": limit * 2,
            "p_offset": 0,
        }
    ).execute()
    
    if not result.data:
        return []
    
    # Use timely ranking strategy
    ranker = get_ranker("timely")
    ranked_posts = ranker.rank_posts(result.data)
    
    return [FeedItem(**post) for post in ranked_posts[:limit]]



