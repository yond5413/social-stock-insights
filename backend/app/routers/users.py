from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Any, Dict, Optional

from ..supabase_client import SupabaseClient, CurrentUserId

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
    Creates or updates user record in the database.
    """
    # Verify the user_id matches the authenticated user
    if request.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")
    
    try:
        # Check if user exists
        result = supabase.table("users").select("*").eq("id", current_user_id).execute()
        
        user_data = {
            "id": current_user_id,
            "email": request.email,
            "username": request.email.split("@")[0] if request.email else f"user_{current_user_id[:8]}",
        }
        
        if result.data:
            # Update existing user
            supabase.table("users").update(user_data).eq("id", current_user_id).execute()
        else:
            # Insert new user
            supabase.table("users").insert(user_data).execute()
        
        return {
            "status": "success",
            "message": "User synced successfully",
            "user_id": current_user_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync user: {str(e)}"
        )


@router.get("/me")
async def get_current_user(
    current_user_id: CurrentUserId,
    supabase: SupabaseClient,
):
    """Get current authenticated user's profile."""
    try:
        result = supabase.table("users").select("*").eq("id", current_user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch user: {str(e)}"
        )

