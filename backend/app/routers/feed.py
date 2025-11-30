from typing import List, Optional
from datetime import datetime

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


@router.get("/following", response_model=List[FeedItem])
async def get_following_feed(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[FeedItem]:
    """
    Feed of posts from users the current user follows.
    Only shows posts from users that the logged-in person follows.
    """
    # First get list of following IDs
    following_result = supabase.table("follows").select("following_id").eq("follower_id", user_id).execute()
    
    if not following_result.data or len(following_result.data) == 0:
        return []
        
    following_ids = [row["following_id"] for row in following_result.data]
    
    # Fetch posts from these users with proper joins
    posts_result = supabase.table("posts").select(
        "id, user_id, content, tickers, llm_status, created_at, view_count"
    ).in_("user_id", following_ids).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    if not posts_result.data:
        return []
    
    post_ids = [str(p["id"]) for p in posts_result.data]
    
    # Get insights for these posts
    insights_result = supabase.table("insights").select(
        "post_id, summary, explanation, sentiment, quality_score, insight_type, sector"
    ).in_("post_id", post_ids).execute()
    
    # Get engagement counts
    engagement_result = supabase.table("post_engagement").select(
        "post_id, type"
    ).in_("post_id", post_ids).execute()
    
    # Get reputation scores for authors
    author_ids = list(set([str(p["user_id"]) for p in posts_result.data]))
    reputation_result = supabase.table("reputation").select(
        "user_id, overall_score"
    ).in_("user_id", author_ids).execute()
    
    # Get usernames from profiles
    profiles_result = supabase.table("profiles").select(
        "id, username"
    ).in_("id", author_ids).execute()
    
    # Build lookup dictionaries
    username_map = {}
    if profiles_result.data:
        for profile in profiles_result.data:
            username_map[str(profile["id"])] = profile.get("username") or f"user_{str(profile['id'])[:8]}"
    
    insights_map = {}
    if insights_result.data:
        for insight in insights_result.data:
            post_id = str(insight["post_id"])
            if post_id not in insights_map:
                insights_map[post_id] = insight
    
    engagement_map = {}
    if engagement_result.data:
        for eng in engagement_result.data:
            post_id = str(eng["post_id"])
            if post_id not in engagement_map:
                engagement_map[post_id] = {"likes": 0, "comments": 0, "dislikes": 0}
            eng_type = eng.get("type", "")
            if eng_type == "like":
                engagement_map[post_id]["likes"] += 1
            elif eng_type == "comment":
                engagement_map[post_id]["comments"] += 1
            elif eng_type == "dislike":
                engagement_map[post_id]["dislikes"] += 1
    
    reputation_map = {}
    if reputation_result.data:
        for rep in reputation_result.data:
            reputation_map[str(rep["user_id"])] = float(rep.get("overall_score", 0))
    
    # Build feed items
    posts = []
    for row in posts_result.data:
        post_id = str(row["id"])
        user_id_str = str(row["user_id"])
        
        insight = insights_map.get(post_id, {})
        engagement = engagement_map.get(post_id, {"likes": 0, "comments": 0, "dislikes": 0})
        
        like_count = engagement["likes"]
        comment_count = engagement["comments"]
        view_count = row.get("view_count", 0) or 0
        
        # Calculate engagement score
        engagement_score = (view_count * 0.1 + like_count * 5.0 + comment_count * 10.0)
        
        quality_score = float(insight.get("quality_score")) if insight.get("quality_score") else None
        author_rep = reputation_map.get(user_id_str, 0.0)
        
        # Calculate final score similar to personalized feed
        final_score = (
            (quality_score or 0) * 0.5 +
            author_rep * 0.2 +
            (like_count - engagement["dislikes"]) * 0.1
        )
        
        created_at = row["created_at"]
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        else:
            created_at = str(created_at)
        
        posts.append({
            "id": post_id,
            "user_id": user_id_str,
            "username": username_map.get(user_id_str),
            "content": row["content"],
            "tickers": row.get("tickers", []),
            "llm_status": row.get("llm_status"),
            "created_at": created_at,
            "view_count": view_count,
            "like_count": like_count,
            "comment_count": comment_count,
            "engagement_score": engagement_score,
            "summary": insight.get("summary"),
            "sentiment": insight.get("sentiment"),
            "quality_score": quality_score,
            "final_score": final_score,
            "is_processing": row.get("llm_status") != "processed",
        })
    
    # Sort by final_score and created_at
    posts.sort(key=lambda x: (x["final_score"], x["created_at"]), reverse=True)
        
    return [FeedItem(**post) for post in posts]




