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
    
    return [FeedItem(**post) for post in ranked_posts[:limit]]


@router.get("/following", response_model=List[FeedItem])
async def get_following_feed(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[FeedItem]:
    """
    Feed of posts from users the current user follows.
    """
    # First get list of following IDs
    following_result = supabase.table("follows").select("following_id").eq("follower_id", user_id).execute()
    
    if not following_result.data:
        return []
        
    following_ids = [row["following_id"] for row in following_result.data]
    
    if not following_ids:
        return []
        
    # Fetch posts from these users
    result = supabase.table("posts").select(
        "*, insights(summary, explanation, sentiment, quality_score, insight_type, sector)"
    ).in_("user_id", following_ids).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    if not result.data:
        return []
        
    posts = []
    for row in result.data:
        insight = row.get("insights", [{}])[0] if row.get("insights") else {}
        
        posts.append({
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "content": row["content"],
            "tickers": row.get("tickers", []),
            "llm_status": row.get("llm_status"),
            "created_at": row["created_at"],
            "view_count": row.get("view_count", 0),
            "like_count": row.get("like_count", 0),
            "comment_count": row.get("comment_count", 0),
            "engagement_score": float(row.get("engagement_score", 0)) if row.get("engagement_score") else 0.0,
            "summary": insight.get("summary"),
            "explanation": insight.get("explanation"),
            "sentiment": insight.get("sentiment"),
            "quality_score": float(insight["quality_score"]) if insight.get("quality_score") else None,
            "final_score": float(row.get("final_score", 0)) if row.get("final_score") else 0.0,
            "insight_type": insight.get("insight_type"),
            "sector": insight.get("sector"),
            "author_reputation": 0.0, # simplified for following feed
            "is_processing": row.get("is_processing", False),
        })
        
    return [FeedItem(**post) for post in posts]




