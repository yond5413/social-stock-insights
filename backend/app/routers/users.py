from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional

from ..supabase_client import SupabaseClient, CurrentUserId, get_supabase_client

router = APIRouter()


class UserSyncRequest(BaseModel):
    email: Optional[EmailStr] = None
    user_id: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/sync")
async def sync_user(
    request: UserSyncRequest,
    current_user_id: CurrentUserId,
    supabase: SupabaseClient,
):
    """
    Sync user profile from frontend authentication.
    Updates profile record in the database if additional data is provided.
    Note: Profile should already exist via the auth trigger.
    """
    # Verify the user_id matches the authenticated user
    if request.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")
    
    try:
        # Check if profile exists
        result = supabase.table("profiles").select("*").eq("id", current_user_id).execute()
        
        user_data = {
            "id": current_user_id,
            "email": request.email,
            "username": request.email.split("@")[0] if request.email else f"user_{current_user_id[:8]}",
        }
        
        if result.data:
            # Update existing profile
            supabase.table("profiles").update(user_data).eq("id", current_user_id).execute()
        else:
            # Insert new profile (fallback if trigger didn't fire)
            supabase.table("profiles").insert(user_data).execute()
        
        return {
            "status": "success",
            "message": "User profile synced successfully",
            "user_id": current_user_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync user profile: {str(e)}"
        )


@router.get("/me")
async def get_current_user(
    current_user_id: CurrentUserId,
    supabase: SupabaseClient,
):
    """Get current authenticated user's profile."""
    try:
        result = supabase.table("profiles").select("*").eq("id", current_user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch profile: {str(e)}"
        )



@router.get("/search")
async def search_users(
    supabase: SupabaseClient,
    query: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    """Search for users by username or email."""
    try:
        result = supabase.rpc(
            "search_users",
            {
                "search_query": query,
                "max_results": limit,
            }
        ).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/{user_id}/follow")
async def follow_user(
    supabase: SupabaseClient,
    user_id: str,
):
    """Follow a user."""
    try:
        supabase.rpc("follow_user", {"target_user_id": user_id}).execute()
        return {"status": "success", "message": "User followed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Follow failed: {str(e)}")


@router.delete("/{user_id}/follow")
async def unfollow_user(
    supabase: SupabaseClient,
    user_id: str,
):
    """Unfollow a user."""
    try:
        supabase.rpc("unfollow_user", {"target_user_id": user_id}).execute()
        return {"status": "success", "message": "User unfollowed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unfollow failed: {str(e)}")


@router.get("/{user_id}/followers")
async def get_followers(
    supabase: SupabaseClient,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
):
    """Get users following a specific user."""
    try:
        result = supabase.rpc(
            "get_user_followers",
            {
                "target_user_id": user_id,
                "limit_val": limit,
                "offset_val": offset,
            }
        ).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch followers: {str(e)}")


@router.get("/{user_id}/following")
async def get_following(
    supabase: SupabaseClient,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
):
    """Get users that a specific user is following."""
    try:
        result = supabase.rpc(
            "get_user_following",
            {
                "target_user_id": user_id,
                "limit_val": limit,
                "offset_val": offset,
            }
        ).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch following: {str(e)}")


@router.get("/{user_id}/stats")
async def get_user_stats(
    supabase: SupabaseClient,
    user_id: str,
):
    """Get user follow stats."""
    try:
        result = supabase.rpc(
            "get_user_follow_stats",
            {"target_user_id": user_id}
        ).execute()
        
        if not result.data:
            return {"followers_count": 0, "following_count": 0, "is_following": False}
            
        return result.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
