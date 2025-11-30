import asyncio
from typing import List, Dict, Any, Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from datetime import datetime

from ..supabase_client import SupabaseClient, get_supabase_client

router = APIRouter()

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
    Search posts using semantic search.
    """
    try:
        # Get embedding for the query (using the same model as ingestion)
        # Note: In a real production app, we'd generate the embedding here.
        # For now, we'll assume the client might send it or we rely on a text-based fallback
        # if the RPC supports it. 
        # WAIT - The RPC expects an embedding vector.
        # We need to generate the embedding first.
        # Let's check if we have an embedding function available.
        
        # Checking llm.py for embedding generation...
        from ..llm import generate_embedding
        
        query_embedding = await generate_embedding(query)
        
        result = supabase.rpc(
            "semantic_search_posts",
            {
                "query_embedding": query_embedding,
                "search_limit": limit,
            }
        ).execute()
        
        posts = []
        if result.data:
            for row in result.data:
                posts.append({
                    "id": str(row["id"]),
                    "user_id": str(row["user_id"]),
                    "content": row["content"],
                    "tickers": row["tickers"],
                    "llm_status": row["llm_status"],
                    "created_at": row["created_at"],
                    "similarity": row["similarity"],
                })
        
        return posts
        
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching posts: {str(e)}"
        )
