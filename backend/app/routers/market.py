import asyncio
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
import yfinance as yf
import pandas_market_calendars as mcal

from ..supabase_client import SupabaseClient, get_supabase_client
from ..schemas import BatchTickersRequest

router = APIRouter()

# Simple in-memory cache for market data (5-minute TTL)
_market_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes

# NYSE calendar for accurate market hours
_nyse_calendar = mcal.get_calendar('NYSE')

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, data: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                disconnected.add(connection)
        # Clean up disconnected clients
        self.active_connections -= disconnected

manager = ConnectionManager()


def get_market_status() -> Dict[str, Any]:
    """Check if US stock markets are currently open using pandas_market_calendars."""
    eastern = ZoneInfo("America/New_York")
    now = datetime.now(eastern)
    today = now.date()
    
    # Get today's market schedule
    schedule = _nyse_calendar.schedule(start_date=today, end_date=today)
    
    is_trading_day = not schedule.empty
    is_open = False
    next_event = "opens"
    next_time = None
    
    if is_trading_day:
        # Get market open/close times for today
        market_open = schedule.iloc[0]['market_open'].to_pydatetime().astimezone(eastern)
        market_close = schedule.iloc[0]['market_close'].to_pydatetime().astimezone(eastern)
        
        is_open = market_open <= now <= market_close
        
        if is_open:
            next_event = "closes"
            next_time = market_close
        elif now < market_open:
            next_event = "opens"
            next_time = market_open
    
    # If market is closed or already closed today, find next trading day
    if not is_open and (not is_trading_day or now >= schedule.iloc[0]['market_close'].to_pydatetime().astimezone(eastern) if is_trading_day else True):
        # Look ahead up to 10 days to find next trading day
        future_start = today + timedelta(days=1)
        future_end = today + timedelta(days=10)
        future_schedule = _nyse_calendar.schedule(start_date=future_start, end_date=future_end)
        
        if not future_schedule.empty:
            next_open = future_schedule.iloc[0]['market_open'].to_pydatetime().astimezone(eastern)
            next_event = "opens"
            next_time = next_open
    
    return {
        "is_open": is_open,
        "next_event": next_event,
        "next_event_time": next_time.isoformat() if next_time else None,
        "current_time": now.isoformat(),
        "timezone": "America/New_York",
        "is_trading_day": is_trading_day,
    }

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
        
        # Strategy 1: fast_info (Preferred, faster)
        try:
            def get_fast_info():
                return ticker_obj.fast_info
            
            info = await asyncio.to_thread(get_fast_info)
            
            if info.last_price is None:
                 raise ValueError("No price data in fast_info")

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
                "source": "fast_info"
            }
            
        except Exception as fast_info_error:
            # Strategy 2: info (Fallback, slower but more robust for some tickers)
            print(f"fast_info failed for {ticker}, trying fallback: {fast_info_error}")
            
            def get_full_info():
                return ticker_obj.info
                
            full_info = await asyncio.to_thread(get_full_info)
            
            # Extract price from various possible fields in 'info'
            price = full_info.get('currentPrice') or full_info.get('regularMarketPrice') or full_info.get('ask')
            previous_close = full_info.get('previousClose') or full_info.get('regularMarketPreviousClose')
            
            if price is None:
                raise ValueError(f"Could not retrieve price for {ticker} from both fast_info and info")
                
            # Calculate derived values if needed
            if previous_close:
                change = price - previous_close
                change_percent = (change / previous_close) * 100
            else:
                change = 0
                change_percent = 0
                
            data = {
                "ticker": ticker,
                "price": price,
                "previous_close": previous_close or price, # Fallback if no prev close
                "change": change,
                "change_percent": change_percent,
                "volume": full_info.get('volume') or full_info.get('regularMarketVolume') or 0,
                "currency": full_info.get('currency', 'USD'),
                "market_cap": full_info.get('marketCap'),
                "fifty_two_week_high": full_info.get('fiftyTwoWeekHigh'),
                "fifty_two_week_low": full_info.get('fiftyTwoWeekLow'),
                "from_cache": False,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "info_fallback"
            }

        # Cache the result
        _cache_market_data(ticker, data)
        
        return data
    except ValueError as ve:
         # This usually means the ticker exists but has no data (delisted/invalid)
         raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        # Check if it's a 404 from yfinance internal request
        error_str = str(e)
        if "404" in error_str or "Not Found" in error_str:
             raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
        
        # Log the actual error for debugging but return a clean message
        print(f"Error fetching {ticker}: {error_str}")
        raise HTTPException(status_code=500, detail=f"Error fetching market data: {error_str}")

@router.get("/trending")
async def get_trending(supabase: SupabaseClient):
    """
    Get trending tickers based on mention count in the last 24 hours.
    Enriched with current market data.
    """
    # 1. Get top mentioned tickers in last 24h using RPC function
    # 1. Get top mentioned tickers from Materialized View (cached)
    result = supabase.table("trending_tickers_mv").select("ticker, post_count").limit(10).execute()
    
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


@router.get("/status")
async def market_status():
    """
    Get current market status (open/closed) based on NYSE/NASDAQ hours.
    Markets are open 9:30 AM - 4:00 PM ET, Monday-Friday, excluding holidays.
    """
    return get_market_status()


@router.get("/search")
async def search_tickers_endpoint(
    supabase: SupabaseClient,
    q: str = Query(..., description="Search query for ticker symbol or company name")
) -> List[Dict[str, Any]]:
    """
    Search for tickers by symbol or company name.
    Returns up to 10 matches ranked by similarity.
    """
    if not q or len(q.strip()) == 0:
        return []
    
    try:
        # Call the search_tickers RPC function
        result = supabase.rpc("search_tickers", {"query_text": q.upper()}).execute()
        
        return result.data if result.data else []
    except Exception as e:
        print(f"Error searching tickers: {str(e)}")
        return []


# Cache for historical data (longer TTL since it changes less frequently)
_history_cache: Dict[str, Dict[str, Any]] = {}
HISTORY_CACHE_TTL_SECONDS = 900  # 15 minutes


def _get_period_days(period: str) -> int:
    """Convert period string to days."""
    period_map = {
        "1D": 1,
        "1W": 7,
        "1M": 30,
        "3M": 90,
    }
    return period_map.get(period, 30)


@router.get("/history/{ticker}")
async def get_ticker_history(
    ticker: str,
    supabase: SupabaseClient,
    period: str = Query("1M", description="Time period: 1D, 1W, 1M, 3M"),
) -> Dict[str, Any]:
    """
    Get historical price data combined with aggregated sentiment for charting.
    Returns price points with sentiment overlay data.
    """
    ticker = ticker.upper()
    cache_key = f"{ticker}_{period}"
    
    # Check cache first
    cached = _history_cache.get(cache_key)
    if cached and (datetime.utcnow() - cached["cached_at"]).total_seconds() < HISTORY_CACHE_TTL_SECONDS:
        return cached["data"]
    
    try:
        # Fetch price history from yfinance
        ticker_obj = await asyncio.to_thread(yf.Ticker, ticker)
        
        # Map period to yfinance parameters
        period_map = {
            "1D": ("1d", "5m"),    # 1 day, 5-minute intervals
            "1W": ("5d", "30m"),   # 5 days, 30-minute intervals
            "1M": ("1mo", "1d"),   # 1 month, daily
            "3M": ("3mo", "1d"),   # 3 months, daily
        }
        yf_period, yf_interval = period_map.get(period, ("1mo", "1d"))
        
        def fetch_history():
            return ticker_obj.history(period=yf_period, interval=yf_interval)
        
        hist = await asyncio.to_thread(fetch_history)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {ticker}")
        
        # Convert price data to list of dicts
        prices = []
        for idx, row in hist.iterrows():
            prices.append({
                "date": idx.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            })
        
        # Fetch sentiment data from posts/insights for the period
        days = _get_period_days(period)
        threshold = datetime.utcnow() - timedelta(days=days)
        
        # Query posts mentioning this ticker with their insights
        posts_result = supabase.table("posts").select(
            "id, created_at, tickers"
        ).contains("tickers", [ticker]).gte(
            "created_at", threshold.isoformat()
        ).order("created_at", desc=False).execute()
        
        # Get insights for these posts to extract sentiment
        sentiment_data = []
        sentiment_by_date: Dict[str, Dict[str, Any]] = {}
        
        if posts_result.data:
            post_ids = [post["id"] for post in posts_result.data]
            
            # Fetch insights for these posts
            insights_result = supabase.table("insights").select(
                "post_id, sentiment, quality_score, created_at"
            ).in_("post_id", post_ids).execute()
            
            # Map insights by post_id
            insights_map = {i["post_id"]: i for i in (insights_result.data or [])}
            
            # Aggregate sentiment by date
            for post in posts_result.data:
                post_date = post["created_at"][:10]  # Extract YYYY-MM-DD
                insight = insights_map.get(post["id"], {})
                sentiment = insight.get("sentiment", "neutral")
                
                if post_date not in sentiment_by_date:
                    sentiment_by_date[post_date] = {
                        "bullish": 0,
                        "bearish": 0,
                        "neutral": 0,
                        "total": 0,
                    }
                
                sentiment_by_date[post_date][sentiment] = sentiment_by_date[post_date].get(sentiment, 0) + 1
                sentiment_by_date[post_date]["total"] += 1
            
            # Convert to sentiment score (-1 to 1)
            for date_str, counts in sentiment_by_date.items():
                total = counts["total"]
                if total > 0:
                    # Sentiment score: (bullish - bearish) / total
                    score = (counts["bullish"] - counts["bearish"]) / total
                    sentiment_data.append({
                        "date": date_str,
                        "score": round(score, 2),
                        "bullish_count": counts["bullish"],
                        "bearish_count": counts["bearish"],
                        "neutral_count": counts["neutral"],
                        "post_count": total,
                    })
        
        # Sort sentiment data by date
        sentiment_data.sort(key=lambda x: x["date"])
        
        # Calculate overall sentiment
        total_bullish = sum(s["bullish_count"] for s in sentiment_data)
        total_bearish = sum(s["bearish_count"] for s in sentiment_data)
        total_posts = sum(s["post_count"] for s in sentiment_data)
        
        overall_sentiment = "neutral"
        if total_posts > 0:
            ratio = (total_bullish - total_bearish) / total_posts
            if ratio > 0.2:
                overall_sentiment = "bullish"
            elif ratio < -0.2:
                overall_sentiment = "bearish"
        
        result = {
            "ticker": ticker,
            "period": period,
            "prices": prices,
            "sentiment": sentiment_data,
            "overall_sentiment": overall_sentiment,
            "total_posts": total_posts,
            "price_change_percent": ((prices[-1]["close"] - prices[0]["close"]) / prices[0]["close"] * 100) if len(prices) > 1 else 0,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Cache the result
        _history_cache[cache_key] = {
            "data": result,
            "cached_at": datetime.utcnow(),
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history for {ticker}: {str(e)}")


@router.websocket("/ws/stream")
async def market_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time market data streaming.
    Broadcasts trending market data every 30 seconds.
    """
    await manager.connect(websocket)
    supabase = get_supabase_client()
    
    try:
        while True:
            # Fetch trending data using existing logic
            try:

                # 1. Get top mentioned tickers from Materialized View (cached)
                result = supabase.table("trending_tickers_mv").select("ticker, post_count").limit(10).execute()
                
                trending_tickers = [row["ticker"] for row in result.data] if result.data else []
                
                if not trending_tickers:
                    trending_tickers = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "COIN"]
                
                async def fetch_one(symbol: str) -> Optional[Dict[str, Any]]:
                    try:
                        t = await asyncio.to_thread(yf.Ticker, symbol)
                        info = await asyncio.to_thread(lambda: t.fast_info)
                        
                        if info.last_price is None:
                            return None
                        
                        return {
                            "ticker": symbol,
                            "price": info.last_price,
                            "change_percent": ((info.last_price - info.previous_close) / info.previous_close) * 100,
                            "volume": info.last_volume,
                            "mentions": next((row["post_count"] for row in result.data if row["ticker"] == symbol), 0)
                        }
                    except Exception:
                        return None
                
                tasks = [fetch_one(t) for t in trending_tickers]
                results = await asyncio.gather(*tasks)
                market_data = [r for r in results if r is not None]
                
                # Send data to this client
                await websocket.send_json({
                    "type": "market_update",
                    "data": market_data,
                    "status": get_market_status(),
                    "timestamp": datetime.utcnow().isoformat(),
                })
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
            
            # Wait 30 seconds before next update
            await asyncio.sleep(30)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

