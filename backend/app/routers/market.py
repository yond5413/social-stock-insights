import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
import yfinance as yf

from ..supabase_client import SupabaseClient

router = APIRouter()

@router.get("/snapshot/{ticker}")
async def get_snapshot(ticker: str):
    """
    Get real-time snapshot of a ticker using yfinance.
    """
    try:
        # Run yfinance in a thread to avoid blocking the event loop
        ticker_obj = await asyncio.to_thread(yf.Ticker, ticker)
        
        # fast_info provides quick access to latest price data
        def get_info():
            return ticker_obj.fast_info

        info = await asyncio.to_thread(get_info)
        
        if info.last_price is None:
             raise ValueError("No price data found")

        return {
            "ticker": ticker.upper(),
            "price": info.last_price,
            "previous_close": info.previous_close,
            "change": info.last_price - info.previous_close,
            "change_percent": ((info.last_price - info.previous_close) / info.previous_close) * 100,
            "volume": info.last_volume,
            "currency": info.currency
        }
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

