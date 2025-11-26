from typing import List, Dict, Any
import re

from fastapi import APIRouter, Depends, HTTPException, status

from ..supabase_client import SupabaseClient, CurrentUserId
from ..schemas import Post, PostCreate


router = APIRouter()


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


