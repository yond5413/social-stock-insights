"""
Chat Router - AI-powered stock market assistant with real-time data context.
"""
import re
import asyncio
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

import httpx
import yfinance as yf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..supabase_client import SupabaseClient
from ..config import get_settings


router = APIRouter()


# Common ticker patterns for extraction
TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b(?=\s+stock|\s+shares|\s+price)')


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's message")
    conversation_history: List[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation"
    )
    tickers: List[str] = Field(
        default_factory=list,
        description="Explicitly mentioned tickers (optional, will auto-detect if empty)"
    )


class TickerContext(BaseModel):
    ticker: str
    price: Optional[float] = None
    change_percent: Optional[float] = None
    sentiment: str = "neutral"
    post_count: int = 0
    recent_themes: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    tickers_context: List[TickerContext] = Field(default_factory=list)
    sources_count: int = 0


def extract_tickers(text: str) -> List[str]:
    """Extract stock tickers from text."""
    # Find $TICKER patterns
    dollar_tickers = re.findall(r'\$([A-Z]{1,5})\b', text.upper())
    
    # Find common stock-related patterns
    stock_patterns = re.findall(r'\b([A-Z]{2,5})\b(?=\s+(?:stock|shares|price|calls|puts|options))', text.upper())
    
    # Combine and deduplicate
    all_tickers = list(set(dollar_tickers + stock_patterns))
    
    # Filter out common words that might be mistaken for tickers
    common_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD', 
                    'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'HAS', 'HIS', 'HOW', 'ITS', 'MAY',
                    'NEW', 'NOW', 'OLD', 'SEE', 'WAY', 'WHO', 'BOY', 'DID', 'GET', 'HIM',
                    'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE', 'BUY', 'SELL', 'HOLD', 'LONG',
                    'SHORT', 'CALL', 'PUTS', 'HIGH', 'LOW', 'UP', 'DOWN', 'API', 'USD', 'ETF'}
    
    return [t for t in all_tickers if t not in common_words]


async def fetch_ticker_data(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch real-time data for a ticker."""
    try:
        ticker_obj = await asyncio.to_thread(yf.Ticker, ticker)
        
        def get_info():
            return ticker_obj.fast_info
        
        info = await asyncio.to_thread(get_info)
        
        if info.last_price is None:
            return None
        
        return {
            "ticker": ticker,
            "price": info.last_price,
            "previous_close": info.previous_close,
            "change_percent": ((info.last_price - info.previous_close) / info.previous_close * 100) if info.previous_close else 0,
            "volume": info.last_volume,
        }
    except Exception:
        return None


async def fetch_community_sentiment(
    ticker: str,
    supabase: SupabaseClient,
    days: int = 7
) -> Dict[str, Any]:
    """Fetch community sentiment for a ticker from recent posts."""
    threshold = datetime.utcnow() - timedelta(days=days)
    
    try:
        # Get posts mentioning this ticker
        posts_result = supabase.table("posts").select(
            "id, content, created_at"
        ).contains("tickers", [ticker]).gte(
            "created_at", threshold.isoformat()
        ).limit(20).execute()
        
        if not posts_result.data:
            return {
                "sentiment": "neutral",
                "post_count": 0,
                "themes": [],
                "sample_posts": [],
            }
        
        post_ids = [p["id"] for p in posts_result.data]
        
        # Get insights for sentiment
        insights_result = supabase.table("insights").select(
            "post_id, sentiment, key_points, summary"
        ).in_("post_id", post_ids).execute()
        
        # Aggregate sentiment
        sentiments = {"bullish": 0, "bearish": 0, "neutral": 0}
        themes = []
        
        for insight in (insights_result.data or []):
            sent = insight.get("sentiment", "neutral")
            sentiments[sent] = sentiments.get(sent, 0) + 1
            
            if insight.get("key_points"):
                themes.extend(insight["key_points"][:2])
        
        # Determine overall sentiment
        total = sum(sentiments.values())
        if total > 0:
            if sentiments["bullish"] > sentiments["bearish"] * 1.5:
                overall = "bullish"
            elif sentiments["bearish"] > sentiments["bullish"] * 1.5:
                overall = "bearish"
            else:
                overall = "mixed"
        else:
            overall = "neutral"
        
        return {
            "sentiment": overall,
            "post_count": len(posts_result.data),
            "themes": list(set(themes))[:5],
            "sample_posts": [p["content"][:200] for p in posts_result.data[:3]],
            "sentiment_breakdown": sentiments,
        }
    except Exception:
        return {
            "sentiment": "neutral",
            "post_count": 0,
            "themes": [],
            "sample_posts": [],
        }


def _get_chat_system_prompt() -> str:
    """System prompt for the stock chat assistant."""
    return """You are an expert stock market analyst assistant. You help users understand market trends, 
analyze stocks, and interpret community sentiment.

You have access to:
1. Real-time price data for mentioned stocks
2. Community sentiment from user posts and discussions
3. Historical price context

Guidelines:
- Be concise but informative
- Always mention specific data points when available (price, % change, sentiment)
- Acknowledge uncertainty when data is limited
- Never provide financial advice or specific buy/sell recommendations
- Focus on analysis and education
- Reference community sentiment when relevant
- Use the provided context to ground your responses in real data

When discussing stocks:
- Mention current price and recent change if available
- Summarize community sentiment (bullish/bearish/mixed)
- Highlight key themes from recent discussions
- Provide balanced analysis considering multiple perspectives"""


@router.post("/ask", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    supabase: SupabaseClient,
) -> ChatResponse:
    """
    Chat with the stock market assistant.
    Provides responses enriched with real-time data and community sentiment.
    """
    settings = get_settings()
    
    # Extract tickers from message if not provided
    tickers = request.tickers if request.tickers else extract_tickers(request.message)
    tickers = [t.upper() for t in tickers][:5]  # Limit to 5 tickers
    
    # Fetch context for each ticker in parallel
    ticker_contexts: List[TickerContext] = []
    context_data: Dict[str, Any] = {}
    
    if tickers:
        # Parallel fetch of market data and sentiment
        market_tasks = [fetch_ticker_data(t) for t in tickers]
        sentiment_tasks = [fetch_community_sentiment(t, supabase) for t in tickers]
        
        market_results = await asyncio.gather(*market_tasks)
        sentiment_results = await asyncio.gather(*sentiment_tasks)
        
        for i, ticker in enumerate(tickers):
            market_data = market_results[i]
            sentiment_data = sentiment_results[i]
            
            ctx = TickerContext(
                ticker=ticker,
                price=market_data["price"] if market_data else None,
                change_percent=market_data["change_percent"] if market_data else None,
                sentiment=sentiment_data["sentiment"],
                post_count=sentiment_data["post_count"],
                recent_themes=sentiment_data.get("themes", []),
            )
            ticker_contexts.append(ctx)
            
            context_data[ticker] = {
                "market": market_data,
                "sentiment": sentiment_data,
            }
    
    # Build context string for LLM
    context_str = ""
    if context_data:
        context_str = "\n\n--- REAL-TIME CONTEXT ---\n"
        for ticker, data in context_data.items():
            context_str += f"\n${ticker}:\n"
            if data["market"]:
                m = data["market"]
                context_str += f"  Price: ${m['price']:.2f} ({m['change_percent']:+.2f}%)\n"
                context_str += f"  Volume: {m['volume']:,}\n"
            else:
                context_str += "  Market data: unavailable\n"
            
            s = data["sentiment"]
            context_str += f"  Community Sentiment: {s['sentiment']} ({s['post_count']} posts)\n"
            if s.get("themes"):
                context_str += f"  Key Themes: {', '.join(s['themes'][:3])}\n"
            if s.get("sample_posts"):
                context_str += f"  Recent discussions:\n"
                for post in s["sample_posts"][:2]:
                    context_str += f"    - \"{post[:100]}...\"\n"
    
    # Build messages for OpenRouter
    messages = [
        {"role": "system", "content": _get_chat_system_prompt()},
    ]
    
    # Add conversation history
    for msg in request.conversation_history[-10:]:  # Last 10 messages
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add current message with context
    user_message = request.message
    if context_str:
        user_message += context_str
    
    messages.append({"role": "user", "content": user_message})
    
    # Call OpenRouter
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": settings.openrouter_model_tagging,
        "messages": messages,
        "max_tokens": 1000,
    }
    
    try:
        async with httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            timeout=30.0
        ) as client:
            resp = await client.post("/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            
            data = resp.json()
            assistant_response = data["choices"][0]["message"]["content"]
            
            return ChatResponse(
                response=assistant_response,
                tickers_context=ticker_contexts,
                sources_count=sum(ctx.post_count for ctx in ticker_contexts),
            )
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request timed out. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )


@router.get("/context/{ticker}")
async def get_ticker_context(
    ticker: str,
    supabase: SupabaseClient,
) -> Dict[str, Any]:
    """
    Get comprehensive context for a ticker without asking a question.
    Useful for pre-populating chat context.
    """
    ticker = ticker.upper()
    
    # Fetch market data
    market_data = await fetch_ticker_data(ticker)
    
    # Fetch sentiment
    sentiment_data = await fetch_community_sentiment(ticker, supabase, days=7)
    
    return {
        "ticker": ticker,
        "market": market_data,
        "community": sentiment_data,
        "timestamp": datetime.utcnow().isoformat(),
    }

