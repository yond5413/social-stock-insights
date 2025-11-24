from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..supabase_client import SupabaseClient, CurrentUserId
from ..schemas import Post, PostCreate


router = APIRouter()


@router.post("/create", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    supabase: SupabaseClient,
    user_id: CurrentUserId,
) -> Post:
    # Ensure a profile row exists for this user id
    supabase.table("profiles").upsert({
        "id": user_id,
        "username": f"user-{user_id[:8]}",
    }, on_conflict="id").execute()

    # Insert the post
    result = supabase.table("posts").insert({
        "user_id": user_id,
        "content": payload.content,
        "tickers": payload.tickers,
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


@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: str,
    supabase: SupabaseClient,
    user_id: CurrentUserId,
) -> Post:
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


