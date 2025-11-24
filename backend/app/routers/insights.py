from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ..supabase_client import SupabaseClient
from ..llm import call_cohere_embedding
from ..schemas import SearchRequest, SearchResult


router = APIRouter()


@router.post("/search", response_model=List[SearchResult])
async def search_insights(
    payload: SearchRequest,
    supabase: SupabaseClient,
) -> List[SearchResult]:
    """
    Semantic search over posts using pgvector similarity on content embeddings.
    Uses Cohere embed-english-v3.0 for query embedding.
    """
    try:
        query_embedding = await call_cohere_embedding(payload.query)
    except Exception as exc:  # pragma: no cover - network error path
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding provider error: {exc}",
        ) from exc

    # Use Supabase RPC for vector search
    result = supabase.rpc(
        "semantic_search_posts",
        {
            "query_embedding": query_embedding,
            "search_limit": payload.limit,
        }
    ).execute()
    
    return [SearchResult(**item) for item in result.data]



