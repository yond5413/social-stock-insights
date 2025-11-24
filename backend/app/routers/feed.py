from typing import List

from fastapi import APIRouter, Depends

from ..supabase_client import SupabaseClient, CurrentUserId
from ..schemas import FeedItem


router = APIRouter()


@router.get("/", response_model=List[FeedItem])
async def get_feed(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    limit: int = 20,
    offset: int = 0,
) -> List[FeedItem]:
    """
    Personalized feed ranked by quality score, reputation, and engagement.
    Uses the get_personalized_feed RPC function for better performance.
    """
    result = supabase.rpc(
        "get_personalized_feed",
        {
            "p_user_id": user_id,
            "p_limit": limit,
            "p_offset": offset,
        }
    ).execute()
    
    return [FeedItem(**item) for item in result.data]



