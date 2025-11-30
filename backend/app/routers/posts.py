import asyncio
from typing import List, Dict, Any, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status, BackgroundTasks
from datetime import datetime
from pydantic import BaseModel

from ..supabase_client import SupabaseClient, get_supabase_client, CurrentUserId
from ..tasks import enqueue_post_processing

router = APIRouter()

class CreatePostRequest(BaseModel):
    content: str
    tickers: List[str] = []


# WebSocket connection manager for ticker-specific posts
class TickerConnectionManager:
    def __init__(self):
        # Map of ticker -> set of WebSocket connections
        self.ticker_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, ticker: str):
        """Connect a WebSocket to a specific ticker's updates."""
        await websocket.accept()
        ticker_upper = ticker.upper()
        if ticker_upper not in self.ticker_connections:
            self.ticker_connections[ticker_upper] = set()
        self.ticker_connections[ticker_upper].add(websocket)
    
    def disconnect(self, websocket: WebSocket, ticker: str):
        """Disconnect a WebSocket from a ticker."""
        ticker_upper = ticker.upper()
        if ticker_upper in self.ticker_connections:
            self.ticker_connections[ticker_upper].discard(websocket)
            if not self.ticker_connections[ticker_upper]:
                del self.ticker_connections[ticker_upper]
    
    async def broadcast_to_ticker(self, ticker: str, data: dict):
        """Broadcast a message to all connections for a specific ticker."""
        ticker_upper = ticker.upper()
        if ticker_upper not in self.ticker_connections:
            return
        
        disconnected = set()
        for connection in self.ticker_connections[ticker_upper]:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        self.ticker_connections[ticker_upper] -= disconnected
        if not self.ticker_connections[ticker_upper]:
            del self.ticker_connections[ticker_upper]

ticker_manager = TickerConnectionManager()


@router.post("/create")
async def create_post(
    request: CreatePostRequest,
    user_id: CurrentUserId,
    supabase: SupabaseClient,
    background_tasks: BackgroundTasks,
):
    """Create a new post."""
    try:
        # Clean tickers
        cleaned_tickers = [t.strip().upper() for t in request.tickers if t.strip()]
        
        data = {
            "user_id": user_id,
            "content": request.content,
            "tickers": cleaned_tickers,
            "llm_status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        result = supabase.table("posts").insert(data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create post")
            
        post_id = result.data[0]["id"]
        
        # Trigger background processing
        enqueue_post_processing(background_tasks, post_id)
        
        # Add computed fields for response
        response_post = result.data[0]
        response_post["is_processing"] = True
        
        return {
            "status": "success",
            "message": "Post created successfully",
            "post": response_post
        }
    except Exception as e:
        print(f"Error creating post: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating post: {str(e)}"
        )


@router.get("/by-ticker/{ticker}")
async def get_posts_by_ticker(
    ticker: str,
    supabase: SupabaseClient,
    limit: int = Query(20, ge=1, le=100, description="Number of posts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> Dict[str, Any]:
    """
    Get posts for a specific ticker, ranked by engagement.
    Returns both processed and pending posts.
    """
    ticker = ticker.strip().upper()
    
    try:
        # Call RPC function to get posts
        result = supabase.rpc(
            "get_ticker_posts_by_engagement",
            {
                "p_ticker": ticker,
                "p_limit": limit,
                "p_offset": offset,
            }
        ).execute()
        
        # Get total count for pagination
        count_result = supabase.rpc(
            "count_ticker_posts",
            {"p_ticker": ticker}
        ).execute()
        
        total_count = count_result.data if count_result.data else 0
        
        posts = []
        if result.data:
            for row in result.data:
                posts.append({
                    "id": str(row["post_id"]),
                    "user_id": str(row["user_id"]),
                    "username": row.get("username"),
                    "content": row["content"],
                    "tickers": row["tickers"],
                    "llm_status": row["llm_status"],
                    "created_at": row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else str(row["created_at"]),
                    "view_count": row["view_count"],
                    "like_count": row["like_count"],
                    "comment_count": row["comment_count"],
                    "engagement_score": float(row["engagement_score"]) if row["engagement_score"] else 0.0,
                    "summary": row.get("summary"),
                    "explanation": row.get("explanation"),
                    "sentiment": row.get("sentiment"),
                    "quality_score": float(row["quality_score"]) if row.get("quality_score") else None,
                    "final_score": float(row.get("final_score", 0)) if row.get("final_score") else 0.0,
                    "insight_type": row.get("insight_type"),
                    "sector": row.get("sector"),
                    "author_reputation": float(row["author_reputation"]) if row.get("author_reputation") else 0.0,
                    "is_processing": row["is_processing"],
                })
        
        return {
            "ticker": ticker,
            "posts": posts,
            "total": total_count,
            "limit": limit,
            "offset": offset,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching posts for ticker {ticker}: {str(e)}"
        )


@router.websocket("/ws/ticker/{ticker}")
async def ticker_posts_stream(websocket: WebSocket, ticker: str):
    """
    WebSocket endpoint for real-time updates on posts for a specific ticker.
    Sends notifications when new posts are created or existing posts are processed.
    """
    await ticker_manager.connect(websocket, ticker)
    supabase = get_supabase_client()
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": f"Connected to ticker {ticker.upper()} updates",
            "ticker": ticker.upper(),
        })
        
        # Poll for new posts every 10 seconds
        last_check = datetime.utcnow()
        
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds
            
            try:
                # Check for new posts since last check
                # Use .contains() for array column filtering (tickers is text[])
                result = supabase.table("posts").select(
                    "id, user_id, content, tickers, llm_status, created_at"
                ).contains("tickers", [ticker.upper()]).gte(
                    "created_at", last_check.isoformat()
                ).order("created_at", desc=True).limit(10).execute()
                
                if result.data:
                    for post in result.data:
                        # Send new post notification
                        await websocket.send_json({
                            "type": "new_post",
                            "ticker": ticker.upper(),
                            "post": {
                                "id": str(post["id"]),
                                "user_id": str(post["user_id"]),
                                "content": post["content"],
                                "tickers": post["tickers"],
                                "llm_status": post["llm_status"],
                                "created_at": post["created_at"].isoformat() if isinstance(post["created_at"], datetime) else str(post["created_at"]),
                            },
                        })
                    
                    last_check = datetime.utcnow()
                
                # Check for posts that changed status (processed)
                # Use .contains() for array column filtering (tickers is text[])
                processed_result = supabase.table("posts").select(
                    "id, llm_status, updated_at"
                ).contains("tickers", [ticker.upper()]).eq(
                    "llm_status", "processed"
                ).gte(
                    "updated_at", last_check.isoformat()
                ).limit(10).execute()
                
                if processed_result.data:
                    for post in processed_result.data:
                        await websocket.send_json({
                            "type": "post_processed",
                            "ticker": ticker.upper(),
                            "post_id": str(post["id"]),
                            "status": post["llm_status"],
                        })
                
            except Exception as e:
                # Log error but don't disconnect
                print(f"Error in ticker WebSocket polling: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Error checking for updates",
                })
                
    except WebSocketDisconnect:
        ticker_manager.disconnect(websocket, ticker)
    except Exception as e:
        print(f"WebSocket error for ticker {ticker}: {e}")
        ticker_manager.disconnect(websocket, ticker)


@router.get("/search")
async def search_posts(
    supabase: SupabaseClient,
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Number of results to return"),
) -> List[Dict[str, Any]]:
    """
    Search posts using hybrid search (semantic + keyword).
    Combines vector similarity search with full-text keyword matching.
    """
    try:
        # Generate embedding for the query using Cohere API
        from ..llm import call_cohere_embedding_for_search
        
        query_embedding = await call_cohere_embedding_for_search(query)
        
        if query_embedding is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate embedding for query. Please try again."
            )

        result = supabase.rpc(
            "hybrid_search_posts",
            {
                "query_text": query,
                "query_embedding": query_embedding,
                "match_threshold": 0.3,  # Lower threshold to include more semantic results since we rank them
                "search_limit": limit,
            }
        ).execute()
        
        posts = []
        if result.data:
            for row in result.data:
                # Handle potential missing columns if RPC changed or if returning partial data
                posts.append({
                    "id": str(row.get("id")),
                    "user_id": str(row.get("user_id")),
                    "content": row.get("content"),
                    "tickers": row.get("tickers", []),
                    "llm_status": row.get("llm_status"),
                    "created_at": row.get("created_at"),
                    "similarity": row.get("similarity", 0.0),
                })
        
        return posts
        
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching posts: {str(e)}"
        )


@router.get("/user/{user_id}")
async def get_user_posts(
    user_id: str,
    supabase: SupabaseClient,
    limit: int = Query(20, ge=1, le=50, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> List[Dict[str, Any]]:
    """
    Get posts for a specific user.
    """
    try:
        # Fetch posts directly from the table
        result = supabase.table("posts").select("*").eq("user_id", user_id).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        
        # Get username from profile
        profile_result = supabase.table("profiles").select("id, username").eq("id", user_id).execute()
        username = None
        if profile_result.data:
            username = profile_result.data[0].get("username") or f"user_{user_id[:8]}"
        
        posts = []
        if result.data:
            for row in result.data:
                posts.append({
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "username": username,
                    "content": row["content"],
                    "tickers": row.get("tickers", []),
                    "llm_status": row.get("llm_status"),
                    "created_at": row["created_at"],
                    "view_count": row.get("view_count", 0),
                    "like_count": row.get("like_count", 0),
                    "comment_count": row.get("comment_count", 0),
                    "engagement_score": float(row.get("engagement_score", 0)) if row.get("engagement_score") else 0.0,
                    "summary": row.get("summary"),
                    "explanation": row.get("explanation"),
                    "sentiment": row.get("sentiment"),
                    "quality_score": float(row["quality_score"]) if row.get("quality_score") else None,
                    "final_score": float(row.get("final_score", 0)) if row.get("final_score") else 0.0,
                    "insight_type": row.get("insight_type"),
                    "sector": row.get("sector"),
                    "author_reputation": float(row.get("author_reputation", 0)) if row.get("author_reputation") else 0.0,
                    "is_processing": row.get("is_processing", False),
                })
        
        return posts

    except Exception as e:
        print(f"Error fetching user posts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching user posts: {str(e)}"
        )
