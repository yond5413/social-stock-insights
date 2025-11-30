from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional

from ..supabase_client import SupabaseClient, CurrentUserId, OptionalUserId, get_supabase_client

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
        # Perform a direct search on the profiles table using ilike for case-insensitive matching
        # We search both username and email columns using an OR condition
        result = supabase.table("profiles").select(
            "id, username, email"
        ).or_(
            f"username.ilike.%{query}%,email.ilike.%{query}%"
        ).limit(limit).execute()
        
        # Calculate a basic similarity/relevance score (optional, but keeps response format consistent)
        # Since we're doing a direct DB query, we don't have vector similarity here.
        # We'll just return the matches.
        users = []
        for row in result.data:
            users.append({
                "id": row["id"],
                "username": row["username"] or row["email"].split("@")[0],
                "email": row["email"],
                "similarity": 1.0  # Placeholder since this is a keyword match
            })
            
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/{user_id}")
async def get_user_profile(
    user_id: str,
    supabase: SupabaseClient,
):
    """Get public profile of a user."""
    try:
        result = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
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


@router.post("/{user_id}/follow")
async def follow_user(
    user_id: str,
    current_user_id: CurrentUserId,
    supabase: SupabaseClient,
):
    """Follow a user."""
    try:
        # Prevent self-follow
        if user_id == current_user_id:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")
        
        # Insert follow relationship
        supabase.table("follows").insert({
            "follower_id": current_user_id,
            "following_id": user_id
        }).execute()
        
        return {"status": "success", "message": "User followed"}
    except Exception as e:
        error_str = str(e)
        if "duplicate" in error_str.lower() or "unique" in error_str.lower():
            # Already following, return success
            return {"status": "success", "message": "User already followed"}
        raise HTTPException(status_code=500, detail=f"Follow failed: {str(e)}")


@router.delete("/{user_id}/follow")
async def unfollow_user(
    user_id: str,
    current_user_id: CurrentUserId,
    supabase: SupabaseClient,
):
    """Unfollow a user."""
    try:
        # Delete follow relationship
        result = supabase.table("follows").delete().eq("follower_id", current_user_id).eq("following_id", user_id).execute()
        
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
    user_id: str,
    supabase: SupabaseClient,
    current_user_id: OptionalUserId = None,
):
    """Get user follow stats."""
    try:
        # Get followers and following counts
        followers_result = supabase.table("follows").select("follower_id").eq("following_id", user_id).execute()
        following_result = supabase.table("follows").select("following_id").eq("follower_id", user_id).execute()
        
        followers_count = len(followers_result.data) if followers_result.data else 0
        following_count = len(following_result.data) if following_result.data else 0
        
        # Check if current user is following this user
        is_following = False
        if current_user_id:
            follow_check = supabase.table("follows").select("follower_id").eq("follower_id", current_user_id).eq("following_id", user_id).execute()
            is_following = len(follow_check.data) > 0 if follow_check.data else False
        
        stats = {
            "followers_count": followers_count,
            "following_count": following_count,
            "is_following": is_following
        }
            
        # Fetch reputation
        rep_result = supabase.table("reputation").select("overall_score").eq("user_id", user_id).execute()
        if rep_result.data:
             stats["reputation"] = float(rep_result.data[0]["overall_score"])
        else:
             stats["reputation"] = 0.0
             
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")
