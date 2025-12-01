from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from ..supabase_client import SupabaseClient
from ..llm import call_openrouter_chat

router = APIRouter()


@router.get("/market")
async def get_market_trends(
    supabase: SupabaseClient,
    time_window: Optional[str] = Query(None, description="Time window: 1h, 4h, 24h, 7d"),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """
    Get emerging market trends detected from post clusters.
    Returns trends sorted by confidence score.
    """
    try:
        result = supabase.rpc("get_active_trends", {
            "p_trend_type": "market",
            "p_time_window": time_window,
            "p_limit": limit,
        }).execute()
        
        return result.data if result.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching market trends: {str(e)}")


@router.get("/community")
async def get_community_trends(
    supabase: SupabaseClient,
    time_window: Optional[str] = Query(None, description="Time window: 1h, 4h, 24h, 7d"),
    limit: int = Query(20, ge=1, le=100),
) -> List[Dict[str, Any]]:
    """
    Get community sentiment trends and hot topics.
    Shows what the community is talking about.
    """
    try:
        result = supabase.rpc("get_active_trends", {
            "p_trend_type": "community",
            "p_time_window": time_window,
            "p_limit": limit,
        }).execute()
        
        return result.data if result.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching community trends: {str(e)}")


@router.get("/tickers/{ticker}")
async def get_ticker_trends(
    ticker: str,
    supabase: SupabaseClient,
    limit: int = Query(10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """
    Get trends specific to a particular ticker.
    Includes sentiment shifts and emerging themes for the ticker.
    """
    try:
        ticker = ticker.upper()
        result = supabase.rpc("get_ticker_trends", {
            "p_ticker": ticker,
            "p_limit": limit,
        }).execute()
        
        return result.data if result.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ticker trends: {str(e)}")


@router.get("/sectors")
async def get_sector_trends(
    supabase: SupabaseClient,
    limit: int = Query(15, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """
    Get trending sectors and industries.
    Useful for identifying which parts of the market are getting attention.
    """
    try:
        result = supabase.rpc("get_active_trends", {
            "p_trend_type": "sector",
            "p_time_window": None,
            "p_limit": limit,
        }).execute()
        
        return result.data if result.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sector trends: {str(e)}")


@router.post("/detect")
async def detect_trends_now(
    supabase: SupabaseClient,
    time_window: str = Query("24h", description="Time window to analyze"),
    min_posts: int = Query(5, description="Minimum posts required to detect a trend"),
) -> Dict[str, Any]:
    """
    Manually trigger trend detection for a given time window.
    This analyzes recent posts and identifies emerging patterns.
    """
    try:
        # Calculate time threshold
        hours_map = {"1h": 1, "4h": 4, "24h": 24, "7d": 168}
        hours = hours_map.get(time_window, 24)
        threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Fetch recent posts
        posts_result = supabase.table("posts").select(
            "id, content, tickers, created_at"
        ).eq("llm_status", "processed").gte(
            "created_at", threshold.isoformat()
        ).order("created_at", desc=True).limit(100).execute()
        
        if not posts_result.data or len(posts_result.data) < min_posts:
            return {
                "message": f"Not enough posts in the last {time_window} to detect trends",
                "post_count": len(posts_result.data) if posts_result.data else 0,
            }
        
        # Prepare posts for LLM analysis
        posts_content = []
        post_ids = []
        all_tickers = set()
        
        for post in posts_result.data[:50]:  # Limit to avoid token limits
            posts_content.append(post["content"][:500])  # Truncate long posts
            post_ids.append(post["id"])
            if post.get("tickers"):
                all_tickers.update(post["tickers"])
        
        # Call LLM for trend detection
        combined_context = f"Recent posts from the last {time_window}:\n\n" + "\n---\n".join(posts_content)
        
        llm_result = await call_openrouter_chat(
            "detect_community_trends",
            combined_context,
            list(all_tickers)
        )
        
        parsed = llm_result["parsed"]
        detected_trends = parsed.get("trends", [])
        
        # Store detected trends in database
        created_trends = []
        for trend_data in detected_trends:
            # Calculate expiration (trends expire based on time window)
            expires_at = datetime.utcnow() + timedelta(hours=hours * 2)
            
            trend_insert = {
                "trend_type": trend_data.get("trend_type", "community"),
                "ticker": trend_data.get("supporting_tickers", [None])[0],  # Primary ticker
                "sector": trend_data.get("sector"),
                "description": trend_data.get("description", ""),
                "confidence": trend_data.get("confidence", 0.5),
                "sentiment_direction": trend_data.get("sentiment_direction"),
                "time_window": time_window,
                "key_themes": trend_data.get("key_themes", []),
                "supporting_post_ids": post_ids[:10],  # Sample of supporting posts
                "expires_at": expires_at.isoformat(),
            }
            
            result = supabase.table("trends").insert(trend_insert).execute()
            if result.data:
                created_trends.append(result.data[0])
        
        return {
            "message": f"Successfully detected {len(created_trends)} trends",
            "trends": created_trends,
            "analyzed_posts": len(posts_result.data),
            "time_window": time_window,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting trends: {str(e)}")


@router.get("/summary")
async def get_trends_summary(
    supabase: SupabaseClient,
) -> Dict[str, Any]:
    """
    Get a comprehensive summary of all active trends across different dimensions.
    Useful for dashboard displays.
    """
    try:
        # Get counts by trend type
        trends_result = supabase.table("trends").select(
            "trend_type, confidence, sentiment_direction"
        ).execute()
        
        if not trends_result.data:
            return {
                "total_trends": 0,
                "by_type": {},
                "by_sentiment": {},
                "avg_confidence": None,
            }
        
        trends = trends_result.data
        by_type = {}
        by_sentiment = {}
        confidences = []
        
        for trend in trends:
            # Count by type
            trend_type = trend.get("trend_type", "unknown")
            by_type[trend_type] = by_type.get(trend_type, 0) + 1
            
            # Count by sentiment
            sentiment = trend.get("sentiment_direction", "neutral")
            by_sentiment[sentiment] = by_sentiment.get(sentiment, 0) + 1
            
            # Collect confidences
            if trend.get("confidence"):
                confidences.append(float(trend["confidence"]))
        
        return {
            "total_trends": len(trends),
            "by_type": by_type,
            "by_sentiment": by_sentiment,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trends summary: {str(e)}")




