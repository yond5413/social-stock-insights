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
    username: Optional[str] = None
    summary: Optional[str] = None
    quality_score: Optional[float] = None
    final_score: float
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    engagement_score: float = 0.0
    user_has_liked: bool = False
    insight_type: Optional[str] = None
    sector: Optional[str] = None
    author_reputation: float = 0.0
    is_processing: bool = False
    author_reputation: float = 0.0
    is_processing: bool = False
    is_bookmarked: bool = False
    ranking_explanation: Optional[str] = None


class BatchTickersRequest(BaseModel):
    tickers: List[str] = Field(..., min_items=1, max_items=50, description="List of ticker symbols")


class ProfileUpdate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern="^[a-zA-Z0-9_]+$")

