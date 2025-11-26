import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
import yfinance as yf

from ..supabase_client import SupabaseClient
from ..schemas import BatchTickersRequest

router = APIRouter()

# Simple in-memory cache for market data (5-minute TTL)
_market_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

def _get_cached_or_none(ticker: str) -> Optional[Dict[str, Any]]:
    """Get cached market data if not expired."""
    cached = _market_cache.get(ticker)
    if cached and (datetime.utcnow() - cached["cached_at"]).total_seconds() < CACHE_TTL_SECONDS:
        return cached["data"]
    return None


def _cache_market_data(ticker: str, data: Dict[str, Any]) -> None:
    """Cache market data with timestamp."""
    _market_cache[ticker] = {
        "data": data,
        "cached_at": datetime.utcnow()
    }


@router.get("/snapshot/{ticker}")
async def get_snapshot(ticker: str):
    """
    Get real-time snapshot of a ticker using yfinance with caching.
    Data is cached for 5 minutes to reduce API calls.
    """
    ticker = ticker.upper()
    
    # Check cache first
    cached_data = _get_cached_or_none(ticker)
    if cached_data:
        cached_data["from_cache"] = True
        return cached_data
    
    try:
        # Run yfinance in a thread to avoid blocking the event loop
        ticker_obj = await asyncio.to_thread(yf.Ticker, ticker)
        
        # fast_info provides quick access to latest price data
        def get_info():
            return ticker_obj.fast_info

        info = await asyncio.to_thread(get_info)
        
        if info.last_price is None:
             raise ValueError("No price data found")

        data = {
            "ticker": ticker,
            "price": info.last_price,
            "previous_close": info.previous_close,
            "change": info.last_price - info.previous_close,
            "change_percent": ((info.last_price - info.previous_close) / info.previous_close) * 100,
            "volume": info.last_volume,
            "currency": info.currency,
            "market_cap": getattr(info, "market_cap", None),
            "fifty_two_week_high": getattr(info, "year_high", None),
            "fifty_two_week_low": getattr(info, "year_low", None),
            "from_cache": False,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Cache the result
        _cache_market_data(ticker, data)
        
        return data
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Ticker not found or error fetching data: {str(e)}")

@router.get("/trending")
async def get_trending(supabase: SupabaseClient):
    """
    Get trending tickers based on mention count in the last 24 hours.
    Enriched with current market data.
    """
    # 1. Get top mentioned tickers in last 24h using RPC function
    result = supabase.rpc(
        "get_trending_tickers",
        {
            "p_hours": 24,
            "p_limit": 10,
        }
    ).execute()
    
    trending_tickers = [row["ticker"] for row in result.data] if result.data else []
    
    # If not enough data, fallback to some popular stocks
    if not trending_tickers:
        trending_tickers = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "COIN"]
    
    # 2. Fetch data for them in parallel
    async def fetch_one(symbol: str) -> Optional[Dict[str, Any]]:
        try:
            t = await asyncio.to_thread(yf.Ticker, symbol)
            
            def get_data():
                return t.fast_info
                
            info = await asyncio.to_thread(get_data)
            
            if info.last_price is None:
                return None
                
            return {
                "ticker": symbol,
                "price": info.last_price,
                "change_percent": ((info.last_price - info.previous_close) / info.previous_close) * 100,
                "volume": info.last_volume,
                "mentions": next((row["count"] for row in result.data if row["ticker"] == symbol), 0)
            }
        except:
            return None

    tasks = [fetch_one(t) for t in trending_tickers]
    results = await asyncio.gather(*tasks)
    
    return [r for r in results if r is not None]


@router.post("/batch")
async def get_batch_snapshots(
    request: BatchTickersRequest,
    supabase: SupabaseClient,
) -> List[Dict[str, Any]]:
    """
    Fetch market data for multiple tickers efficiently in parallel.
    Useful for getting data for a portfolio or watchlist.
    """
    # Normalize tickers
    tickers = [t.upper() for t in request.tickers]
    
    async def fetch_one_with_cache(symbol: str) -> Optional[Dict[str, Any]]:
        # Check cache first
        cached = _get_cached_or_none(symbol)
        if cached:
            return cached
        
        try:
            t = await asyncio.to_thread(yf.Ticker, symbol)
            
            def get_data():
                return t.fast_info
                
            info = await asyncio.to_thread(get_data)
            
            if info.last_price is None:
                return None
                
            data = {
                "ticker": symbol,
                "price": info.last_price,
                "change_percent": ((info.last_price - info.previous_close) / info.previous_close) * 100,
                "volume": info.last_volume,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            _cache_market_data(symbol, data)
            return data
        except:
            return None
    
    tasks = [fetch_one_with_cache(t) for t in tickers]
    results = await asyncio.gather(*tasks)
    
    return [r for r in results if r is not None]


@router.get("/events")
async def get_market_events(
    supabase: SupabaseClient,
    hours: int = Query(24, description="Look back this many hours"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """
    Get recent market events: volume spikes, significant price movements.
    Useful for identifying which stocks are seeing unusual activity.
    """
    try:
        threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Get posts with recent activity
        posts_result = supabase.table("posts").select(
            "tickers, created_at"
        ).eq("llm_status", "processed").gte(
            "created_at", threshold.isoformat()
        ).execute()
        
        if not posts_result.data:
            return {
                "events": [],
                "time_window_hours": hours,
            }
        
        # Count ticker mentions
        ticker_counts = {}
        for post in posts_result.data:
            if post.get("tickers"):
                for ticker in post["tickers"]:
                    ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        # Get top mentioned tickers
        top_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        # Fetch current market data for top tickers
        events = []
        for ticker, mention_count in top_tickers[:20]:  # Limit to avoid too many API calls
            try:
                snapshot = await get_snapshot(ticker)
                
                # Classify as event if significant movement or high mentions
                is_event = False
                event_type = []
                
                if abs(snapshot["change_percent"]) > 5:
                    is_event = True
                    event_type.append("large_move")
                
                if mention_count > 3:
                    is_event = True
                    event_type.append("high_mentions")
                
                if is_event:
                    events.append({
                        "ticker": ticker,
                        "event_types": event_type,
                        "mention_count": mention_count,
                        "price": snapshot["price"],
                        "change_percent": snapshot["change_percent"],
                        "volume": snapshot["volume"],
                    })
            except:
                continue  # Skip tickers with errors
        
        return {
            "events": events,
            "time_window_hours": hours,
            "total_events": len(events),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching market events: {str(e)}")


@router.get("/calendar/{ticker}")
async def get_ticker_calendar(
    ticker: str,
) -> Dict[str, Any]:
    """
    Get upcoming events for a ticker (earnings, splits, etc.).
    Note: This is a simplified version; a production version would use a dedicated API.
    """
    ticker = ticker.upper()
    
    try:
        t = await asyncio.to_thread(yf.Ticker, ticker)
        
        def get_calendar():
            return t.calendar if hasattr(t, 'calendar') else None
        
        calendar = await asyncio.to_thread(get_calendar)
        
        # Try to get earnings dates
        def get_earnings_dates():
            try:
                return t.earnings_dates if hasattr(t, 'earnings_dates') else None
            except:
                return None
        
        earnings_dates = await asyncio.to_thread(get_earnings_dates)
        
        return {
            "ticker": ticker,
            "calendar": calendar.to_dict() if calendar is not None and hasattr(calendar, 'to_dict') else None,
            "has_upcoming_earnings": earnings_dates is not None,
            "note": "Calendar data availability depends on the data provider",
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Calendar data not available: {str(e)}")

