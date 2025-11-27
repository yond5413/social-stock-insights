from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..supabase_client import SupabaseClient
from ..llm import call_cohere_embedding
from ..schemas import SearchRequest, SearchResult


router = APIRouter()

# Simple in-memory cache for sentiment data (5-minute TTL)
_sentiment_cache: Dict[str, Dict[str, Any]] = {}
SENTIMENT_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cached_sentiment(ticker: str) -> Optional[Dict[str, Any]]:
    """Get cached sentiment if not expired."""
    cached = _sentiment_cache.get(ticker)
    if cached and (datetime.utcnow() - cached["cached_at"]).total_seconds() < SENTIMENT_CACHE_TTL_SECONDS:
        return cached["data"]
    return None


def _cache_sentiment(ticker: str, data: Dict[str, Any]) -> None:
    """Cache sentiment with timestamp."""
    _sentiment_cache[ticker] = {
        "data": data,
        "cached_at": datetime.utcnow()
    }


@router.post("/search", response_model=List[SearchResult])
async def search_insights(
    payload: SearchRequest,
    supabase: SupabaseClient,
) -> List[SearchResult]:
    """
    Semantic search over posts using pgvector similarity on content embeddings.
    Uses Cohere embed-english-v3.0 for query embedding.
    """
    try:
        query_embedding = await call_cohere_embedding(payload.query)
    except Exception as exc:  # pragma: no cover - network error path
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding provider error: {exc}",
        ) from exc

    # Use Supabase RPC for vector search
    result = supabase.rpc(
        "semantic_search_posts",
        {
            "query_embedding": query_embedding,
            "search_limit": payload.limit,
        }
    ).execute()
    
    return [SearchResult(**item) for item in result.data]


@router.get("/ticker/{ticker}/sentiment")
async def get_ticker_sentiment(
    ticker: str,
    supabase: SupabaseClient,
    days: int = Query(30, ge=1, le=90, description="Number of days to look back"),
) -> Dict[str, Any]:
    """
    Get engagement-weighted sentiment for a ticker with confidence levels.
    Uses RPC function with caching for performance.
    """
    ticker = ticker.strip().upper()
    
    # Check cache first
    cache_key = f"{ticker}_{days}"
    cached = _get_cached_sentiment(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached
    
    try:
        # Call RPC function
        result = supabase.rpc(
            "get_ticker_sentiment_with_engagement",
            {
                "p_ticker": ticker,
                "p_days": days,
            }
        ).execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "ticker": ticker,
                "total_posts": 0,
                "processed_posts": 0,
                "pending_posts": 0,
                "sentiment_summary": {
                    "bullish": 0,
                    "bearish": 0,
                    "neutral": 0,
                },
                "weighted_sentiment": {
                    "bullish": 0,
                    "bearish": 0,
                    "neutral": 0,
                },
                "confidence_level": "low",
                "avg_engagement": 0,
                "top_themes": [],
                "from_cache": False,
            }
        
        data = result.data[0]
        
        # Calculate weighted percentages
        total_weight = (
            float(data.get("weighted_bullish", 0)) +
            float(data.get("weighted_bearish", 0)) +
            float(data.get("weighted_neutral", 0))
        )
        
        if total_weight > 0:
            weighted_sentiment = {
                "bullish": round((float(data.get("weighted_bullish", 0)) / total_weight) * 100, 1),
                "bearish": round((float(data.get("weighted_bearish", 0)) / total_weight) * 100, 1),
                "neutral": round((float(data.get("weighted_neutral", 0)) / total_weight) * 100, 1),
            }
        else:
            weighted_sentiment = {"bullish": 0, "bearish": 0, "neutral": 0}
        
        # Extract top themes (limit to 5)
        themes_data = data.get("top_themes", [])
        if isinstance(themes_data, list):
            top_themes = themes_data[:5]
        else:
            top_themes = []
        
        response = {
            "ticker": ticker,
            "total_posts": data.get("total_posts", 0),
            "processed_posts": data.get("processed_posts", 0),
            "pending_posts": data.get("pending_posts", 0),
            "sentiment_summary": {
                "bullish": data.get("bullish_count", 0),
                "bearish": data.get("bearish_count", 0),
                "neutral": data.get("neutral_count", 0),
            },
            "weighted_sentiment": weighted_sentiment,
            "confidence_level": data.get("confidence_level", "low"),
            "avg_engagement": round(float(data.get("avg_engagement", 0)), 2),
            "top_themes": top_themes,
            "from_cache": False,
        }
        
        # Cache the result
        _cache_sentiment(cache_key, response)
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sentiment for ticker {ticker}: {str(e)}"
        )



