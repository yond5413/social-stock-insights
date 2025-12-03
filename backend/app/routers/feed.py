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
    
    print(f"[get_feed] Fetched {len(result.data)} posts from RPC")
    print(f"[get_feed] First post before enrichment: {result.data[0] if result.data else 'none'}")
    
    # Use ensemble ranker to re-rank based on strategy
    ranker = get_ranker(strategy)
    ranked_posts = ranker.rank_posts(result.data)
    
    # Return top results
    ranked_posts = ranked_posts[:limit]
    
    print(f"[get_feed] About to enrich {len(ranked_posts)} posts")
    
    # Enrich with usernames
    ranked_posts = await _enrich_posts_with_usernames(supabase, ranked_posts)
    
    # Enrich with user engagement
    ranked_posts = await _enrich_posts_with_user_engagement(supabase, ranked_posts, user_id)
    
    print(f"[get_feed] After enrichment, first post: {ranked_posts[0] if ranked_posts else 'none'}")
    
    return [FeedItem(**post) for post in ranked_posts]


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
    
    ranked_posts = ranked_posts[:limit]
    
    # Enrich with usernames
    ranked_posts = await _enrich_posts_with_usernames(supabase, ranked_posts)
    
    # Enrich with user engagement
    ranked_posts = await _enrich_posts_with_user_engagement(supabase, ranked_posts, user_id)
    
    return [FeedItem(**post) for post in ranked_posts]


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
    
    ranked_posts = ranked_posts[:limit]
    
    # Enrich with usernames
    ranked_posts = await _enrich_posts_with_usernames(supabase, ranked_posts)
    
    # Enrich with user engagement
    ranked_posts = await _enrich_posts_with_user_engagement(supabase, ranked_posts, user_id)
    
    return [FeedItem(**post) for post in ranked_posts]


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
    
    ranked_posts = ranked_posts[:limit]
    
    # Enrich with usernames
    ranked_posts = await _enrich_posts_with_usernames(supabase, ranked_posts)
    
    # Enrich with user engagement
    ranked_posts = await _enrich_posts_with_user_engagement(supabase, ranked_posts, user_id)
    
    return [FeedItem(**post) for post in ranked_posts]


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
    print(f"\n[get_following_feed] === DEBUGGING FOLLOWER FEED ===")
    print(f"[get_following_feed] Current user_id: {user_id}")
    print(f"[get_following_feed] Limit: {limit}, Offset: {offset}")
    
    # First get list of following IDs
    following_result = supabase.table("follows").select("following_id").eq("follower_id", user_id).execute()
    
    print(f"[get_following_feed] Follow query result: {following_result.data}")
    print(f"[get_following_feed] Number of users following: {len(following_result.data) if following_result.data else 0}")
    
    if not following_result.data or len(following_result.data) == 0:
        print(f"[get_following_feed] User is not following anyone, returning empty feed")
        return []

        
    following_ids = [row["following_id"] for row in following_result.data]
    
    print(f"[get_following_feed] Following user IDs: {following_ids}")
    
    # Fetch posts from these users with proper joins
    posts_result = supabase.table("posts").select(
        "id, user_id, content, tickers, llm_status, created_at, view_count"
    ).in_("user_id", following_ids).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    print(f"[get_following_feed] Posts query returned {len(posts_result.data) if posts_result.data else 0} posts")
    if posts_result.data:
        print(f"[get_following_feed] First post: ID={posts_result.data[0]['id']}, user_id={posts_result.data[0]['user_id']}")

    if not posts_result.data:
        print(f"[get_following_feed] No posts found from followed users, returning empty feed")
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
    
    # Build lookup dictionaries
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
            # Username will be enriched later
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
    
    # Enrich with usernames using the robust helper
    posts = await _enrich_posts_with_usernames(supabase, posts)
    
    # Enrich with user engagement
    posts = await _enrich_posts_with_user_engagement(supabase, posts, user_id)
        
    return [FeedItem(**post) for post in posts]


async def _enrich_posts_with_usernames(supabase: SupabaseClient, posts: List[dict]) -> List[dict]:
    """
    Helper function to fetch usernames for a list of posts and add them to the post objects.
    """
    if not posts:
        print("[_enrich_posts_with_usernames] No posts to enrich")
        return []
    
    print(f"[_enrich_posts_with_usernames] Starting enrichment for {len(posts)} posts")
        
    # Extract user IDs
    user_ids = list(set([str(post.get("user_id")) for post in posts if post.get("user_id")]))
    
    print(f"[_enrich_posts_with_usernames] Extracted {len(user_ids)} unique user_ids: {user_ids[:3]}...")
    
    if not user_ids:
        print("[_enrich_posts_with_usernames] No user_ids found!")
        return posts
        
    # Fetch profiles
    profiles_result = supabase.table("profiles").select("id, username").in_("id", user_ids).execute()
    
    print(f"[_enrich_posts_with_usernames] Fetched {len(profiles_result.data) if profiles_result.data else 0} profiles")
    if profiles_result.data:
        print(f"[_enrich_posts_with_usernames] Sample profile: {profiles_result.data[0]}")
    
    # Create map
    username_map = {}
    if profiles_result.data:
        for profile in profiles_result.data:
            username_map[str(profile["id"])] = profile.get("username")
    
    print(f"[_enrich_posts_with_usernames] Username map: {username_map}")
            
    # Add usernames to posts
    mapped_count = 0
    fallback_count = 0
    
    for post in posts:
        user_id = str(post.get("user_id"))
        if user_id in username_map and username_map[user_id]:
            post["username"] = username_map[user_id]
            mapped_count += 1
        else:
            # Fallback if no username found
            post["username"] = f"User {user_id[:8]}"
            fallback_count += 1
            
    print(f"[_enrich_posts_with_usernames] Enriched {len(posts)} posts: {mapped_count} mapped, {fallback_count} fallbacks")
    return posts


async def _enrich_posts_with_user_engagement(supabase: SupabaseClient, posts: List[dict], user_id: str) -> List[dict]:
    """
    Helper function to check if the current user has liked any of the posts.
    """
    if not posts or not user_id:
        return posts
        
    post_ids = [str(post.get("post_id") or post.get("id")) for post in posts]
    
    if not post_ids:
        return posts
        
    # Fetch likes for these posts by this user
    likes_result = supabase.table("post_engagement").select("post_id").eq("user_id", user_id).eq("type", "like").in_("post_id", post_ids).execute()
    
    liked_post_ids = set()
    if likes_result.data:
        for row in likes_result.data:
            liked_post_ids.add(str(row["post_id"]))
            
    # Add user_has_liked to posts
    for post in posts:
        p_id = str(post.get("post_id") or post.get("id"))
        post["user_has_liked"] = p_id in liked_post_ids
        
    # Fetch bookmarks
    bookmarks_result = supabase.table("bookmarks").select("post_id").eq("user_id", user_id).in_("post_id", post_ids).execute()
    bookmarked_ids = set()
    if bookmarks_result.data:
        for row in bookmarks_result.data:
            bookmarked_ids.add(str(row["post_id"]))
            
    for post in posts:
        p_id = str(post.get("post_id") or post.get("id"))
        post["is_bookmarked"] = p_id in bookmarked_ids
        
    return posts





