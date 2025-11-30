from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

from .config import get_settings


_client: Client | None = None
bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_supabase_client() -> Client:
    """
    Get a singleton Supabase client instance.
    Uses the service role key for backend operations.
    """
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
        )
    return _client


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    supabase: Client = Depends(get_supabase_client),
) -> str:
    """
    Extract and verify the Supabase user from the JWT token.
    Uses Supabase's built-in auth verification instead of manual JWT handling.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    try:
        # Verify the JWT token using Supabase auth
        user = supabase.auth.get_user(credentials.credentials)
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )
        return user.user.id
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {exc}",
        ) from exc


# Type alias for dependency injection
SupabaseClient = Annotated[Client, Depends(get_supabase_client)]
CurrentUserId = Annotated[str, Depends(get_current_user_id)]




