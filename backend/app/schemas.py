from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PostCreate(BaseModel):
    content: str = Field(..., min_length=1)
    tickers: List[str] = Field(default_factory=list)


class Post(BaseModel):
    id: str
    user_id: str
    content: str
    tickers: List[str]
    llm_status: Optional[str] = None
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class SearchResult(Post):
    similarity: float


class FeedItem(Post):
    summary: Optional[str] = None
    quality_score: Optional[float] = None
    final_score: float


class BatchTickersRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=1, max_items=50, description="List of ticker symbols")
