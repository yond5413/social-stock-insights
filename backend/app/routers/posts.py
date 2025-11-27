from typing import List, Dict, Any, Optional, Set
import re
from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect

from ..supabase_client import SupabaseClient, CurrentUserId
from ..schemas import Post, PostCreate


router = APIRouter()

# WebSocket connection manager for ticker-specific updates
class TickerConnectionManager:
    def __init__(self):
        # Map ticker -> set of websocket connections
        self.ticker_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, ticker: str):
        await websocket.accept()
        ticker = ticker.upper()
        if ticker not in self.ticker_connections:
            self.ticker_connections[ticker] = set()
        self.ticker_connections[ticker].add(websocket)
    
    def disconnect(self, websocket: WebSocket, ticker: str):
        ticker = ticker.upper()
        if ticker in self.ticker_connections:
            self.ticker_connections[ticker].discard(websocket)
            # Clean up empty sets
            if not self.ticker_connections[ticker]:
                del self.ticker_connections[ticker]
    
    async def broadcast_to_ticker(self, ticker: str, data: dict):
        """Broadcast data to all connections watching a specific ticker"""
        ticker = ticker.upper()
        if ticker not in self.ticker_connections:
            return
        
        disconnected = set()
        for connection in self.ticker_connections[ticker]:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        self.ticker_connections[ticker] -= disconnected

ticker_ws_manager = TickerConnectionManager()

# Simple in-memory cache for ticker posts (2-minute TTL)
_ticker_posts_cache: Dict[str, Dict[str, Any]] = {}
TICKER_POSTS_CACHE_TTL_SECONDS = 120  # 2 minutes


def _get_cached_or_none(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached ticker posts if not expired."""
    cached = _ticker_posts_cache.get(cache_key)
    if cached and (datetime.utcnow() - cached["cached_at"]).total_seconds() < TICKER_POSTS_CACHE_TTL_SECONDS:
        return cached["data"]
    return None


def _cache_ticker_posts(cache_key: str, data: Dict[str, Any]) -> None:
    """Cache ticker posts with timestamp."""
    _ticker_posts_cache[cache_key] = {
        "data": data,
        "cached_at": datetime.utcnow()
    }


def validate_ticker(ticker: str) -> str:
    """Validate and normalize a ticker symbol."""
    ticker = ticker.strip().upper()
    # Basic validation: 1-5 characters, alphanumeric
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        raise ValueError(f"Invalid ticker format: {ticker}")
    return ticker


def validate_post_content(content: str) -> None:
    """Validate post content for quality and spam prevention."""
    if len(content) < 10:
        raise ValueError("Post content too short (minimum 10 characters)")
    if len(content) > 10000:
        raise ValueError("Post content too long (maximum 10,000 characters)")
    
    # Check for spam patterns (very basic)
    spam_patterns = [
        r'(http|https)://[^\s]+' * 5,  # Too many URLs
        r'(.)\1{10,}',  # Repeated characters
    ]
    for pattern in spam_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            raise ValueError("Post content appears to be spam")


@router.post("/create", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    supabase: SupabaseClient,
    user_id: CurrentUserId,
) -> Post:
    """
    Create a new post with validation for content and tickers.
    Returns the post with estimated processing time.
    """
    try:
        # Validate content
        validate_post_content(payload.content)
        
        # Validate and normalize tickers
        normalized_tickers = []
        for ticker in payload.tickers:
            try:
                normalized_ticker = validate_ticker(ticker)
                normalized_tickers.append(normalized_ticker)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e),
                )
        
        # Remove duplicates while preserving order
        normalized_tickers = list(dict.fromkeys(normalized_tickers))
        
        # Limit number of tickers per post
        if len(normalized_tickers) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 tickers per post",
            )
        
        # Insert the post
        result = supabase.table("posts").insert({
            "user_id": user_id,
            "content": payload.content,
            "tickers": normalized_tickers,
            "llm_status": "pending",
        }).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create post",
            )
        
        post_data = result.data[0]
        return Post(
            id=str(post_data["id"]),
            user_id=str(post_data["user_id"]),
            content=post_data["content"],
            tickers=post_data["tickers"],
            llm_status=post_data["llm_status"],
            created_at=post_data["created_at"],
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # If we get a foreign key constraint error, the profile might not exist
        if "foreign key" in str(e).lower() or "violates" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User profile not found. Please ensure you're properly authenticated.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create post: {str(e)}",
        )


@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: str,
    supabase: SupabaseClient,
    user_id: CurrentUserId,
) -> Post:
    """Get a specific post by ID."""
    result = supabase.table("posts").select("*").eq("id", post_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    post_data = result.data[0]
    return Post(
        id=str(post_data["id"]),
        user_id=str(post_data["user_id"]),
        content=post_data["content"],
        tickers=post_data["tickers"],
        llm_status=post_data.get("llm_status"),
        created_at=post_data["created_at"],
    )


@router.get("/{post_id}/status")
async def get_post_status(
    post_id: str,
    supabase: SupabaseClient,
    user_id: CurrentUserId,
) -> Dict[str, Any]:
    """
    Get the processing status of a post including queue position and estimated completion time.
    """
    result = supabase.table("posts").select(
        "id, llm_status, created_at, updated_at, error_message, retry_count"
    ).eq("id", post_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    post = result.data[0]
    status_info = {
        "post_id": post["id"],
        "status": post["llm_status"],
        "created_at": post["created_at"],
        "updated_at": post.get("updated_at"),
    }
    
    if post["llm_status"] == "pending":
        # Get queue position
        queue_result = supabase.table("posts").select("id").eq(
            "llm_status", "pending"
        ).lte("created_at", post["created_at"]).execute()
        
        queue_position = len(queue_result.data) if queue_result.data else 1
        status_info["queue_position"] = queue_position
        status_info["estimated_wait_seconds"] = queue_position * 30  # Rough estimate
        
    elif post["llm_status"] == "failed":
        status_info["error_message"] = post.get("error_message")
        status_info["retry_count"] = post.get("retry_count", 0)
    
    return status_info


@router.get("/by-ticker/{ticker}")
async def get_posts_by_ticker(
    ticker: str,
    supabase: SupabaseClient,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """
    Get posts mentioning a specific ticker with their insights.
    Returns posts ranked by engagement with sentiment aggregation.
    Uses RPC function with fallback to direct query.
    """
    # Normalize ticker
    ticker = ticker.strip().upper()
    
    # Basic ticker validation
    if not re.match(r'^[A-Z]{1,5}$', ticker):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ticker format: {ticker}"
        )
    
    # Check cache first
    cache_key = f"ticker_posts_{ticker}_{limit}_{offset}"
    cached = _get_cached_or_none(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached
    
    try:
        # Try RPC function first (preferred method)
        try:
            posts_result = supabase.rpc(
                "get_ticker_posts_by_engagement",
                {
                    "p_ticker": ticker,
                    "p_limit": limit,
                    "p_offset": offset,
                }
            ).execute()
            
            # Get total count using dedicated function
            count_result = supabase.rpc(
                "count_ticker_posts",
                {"p_ticker": ticker}
            ).execute()
            
            total_count = count_result.data if count_result.data else 0
            
            enriched_posts = []
            sentiment_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
            
            for post in (posts_result.data or []):
                sentiment = post.get("sentiment", "neutral") or "neutral"
                
                # Count sentiments (only for processed posts)
                if not post.get("is_processing", False) and sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1
                
                enriched_posts.append({
                    "id": post["post_id"],
                    "user_id": post["user_id"],
                    "content": post["content"],
                    "tickers": post["tickers"],
                    "llm_status": post["llm_status"],
                    "created_at": post["created_at"],
                    "view_count": post.get("view_count", 0),
                    "like_count": post.get("like_count", 0),
                    "comment_count": post.get("comment_count", 0),
                    "engagement_score": float(post.get("engagement_score", 0)),
                    "summary": post.get("summary"),
                    "explanation": post.get("explanation"),
                    "sentiment": sentiment,
                    "quality_score": post.get("quality_score"),
                    "insight_type": post.get("insight_type"),
                    "sector": post.get("sector"),
                    "author_reputation": post.get("author_reputation", 0),
                    "is_processing": post.get("is_processing", False),
                })
            
            result = {
                "ticker": ticker,
                "posts": enriched_posts,
                "total_count": total_count,
                "sentiment_summary": sentiment_counts,
                "has_more": offset + limit < total_count,
                "from_cache": False,
            }
            
            # Cache the result
            _cache_ticker_posts(cache_key, result)
            return result
            
        except Exception as rpc_error:
            # Fallback to direct query if RPC fails
            print(f"RPC function failed for {ticker}, using fallback: {rpc_error}")
            
            # Get posts containing this ticker (ALL posts, not just processed)
            posts_result = supabase.table("posts").select(
                "id, user_id, content, tickers, llm_status, created_at, view_count"
            ).contains("tickers", [ticker]).order(
                "created_at", desc=True
            ).range(offset, offset + limit - 1).execute()
            
            if not posts_result.data:
                return {
                    "ticker": ticker,
                    "posts": [],
                    "total_count": 0,
                    "sentiment_summary": {
                        "bullish": 0,
                        "bearish": 0,
                        "neutral": 0,
                    },
                    "has_more": False,
                    "from_cache": False,
                }
            
            post_ids = [p["id"] for p in posts_result.data]
            
            # Get insights for these posts
            insights_result = supabase.table("insights").select(
                "post_id, summary, explanation, sentiment, quality_score, insight_type, sector"
            ).in_("post_id", post_ids).execute()
            
            # Map insights by post_id
            insights_map = {i["post_id"]: i for i in (insights_result.data or [])}
            
            # Build enriched posts
            enriched_posts = []
            sentiment_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
            
            for post in posts_result.data:
                insight = insights_map.get(post["id"], {})
                sentiment = insight.get("sentiment", "neutral") or "neutral"
                is_processing = post["llm_status"] != "processed"
                
                # Count sentiments (only for processed posts)
                if not is_processing and sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1
                
                enriched_posts.append({
                    "id": post["id"],
                    "user_id": post["user_id"],
                    "content": post["content"],
                    "tickers": post["tickers"],
                    "llm_status": post["llm_status"],
                    "created_at": post["created_at"],
                    "view_count": post.get("view_count", 0),
                    "like_count": 0,  # Not available in fallback
                    "comment_count": 0,  # Not available in fallback
                    "engagement_score": 0,  # Not available in fallback
                    "summary": insight.get("summary"),
                    "explanation": insight.get("explanation"),
                    "sentiment": sentiment,
                    "quality_score": insight.get("quality_score"),
                    "insight_type": insight.get("insight_type"),
                    "sector": insight.get("sector"),
                    "author_reputation": 0,  # Not available in fallback
                    "is_processing": is_processing,
                })
            
            # Get total count for pagination
            count_result = supabase.table("posts").select(
                "id", count="exact"
            ).contains("tickers", [ticker]).execute()
            
            total_count = count_result.count if hasattr(count_result, 'count') else len(posts_result.data)
            
            result = {
                "ticker": ticker,
                "posts": enriched_posts,
                "total_count": total_count,
                "sentiment_summary": sentiment_counts,
                "has_more": offset + limit < total_count,
                "from_cache": False,
            }
            
            # Cache the fallback result too
            _cache_ticker_posts(cache_key, result)
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching posts for ticker {ticker}: {str(e)}"
        )


@router.websocket("/ws/ticker/{ticker}")
async def ticker_websocket(websocket: WebSocket, ticker: str):
    """
    WebSocket endpoint for real-time updates on ticker posts.
    Clients connect and receive notifications when new posts for the ticker are created/processed.
    """
    ticker = ticker.upper()
    await ticker_ws_manager.connect(websocket, ticker)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "ticker": ticker,
            "message": f"Connected to updates for {ticker}",
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        # Keep connection alive and wait for messages (or just keep alive)
        while True:
            # Wait for any client messages (like ping/pong)
            try:
                # Set a timeout to periodically check connection
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                
                # Echo back any ping messages
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({
                    "type": "keepalive",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
    except WebSocketDisconnect:
        ticker_ws_manager.disconnect(websocket, ticker)
    except Exception:
        ticker_ws_manager.disconnect(websocket, ticker)


# Helper function to broadcast post updates (can be called from other parts of the app)
async def broadcast_post_update(tickers: List[str], post_id: str, event_type: str):
    """
    Broadcast a post update to all WebSocket clients watching the relevant tickers.
    
    Args:
        tickers: List of ticker symbols mentioned in the post
        post_id: The ID of the post
        event_type: Type of event ('new_post', 'post_processed', etc.)
    """
    for ticker in tickers:
        await ticker_ws_manager.broadcast_to_ticker(
            ticker,
            {
                "type": event_type,
                "ticker": ticker.upper(),
                "post_id": post_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


