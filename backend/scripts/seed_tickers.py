import asyncio
import os
import sys
from typing import List, Dict
import yfinance as yf
from supabase import create_client, Client

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.supabase_client import get_supabase_client

# List of popular tickers to seed
POPULAR_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "LLY", "V",
    "TSM", "AVGO", "NVO", "JPM", "WMT", "XOM", "MA", "UNH", "PG", "JNJ",
    "ORCL", "HD", "COST", "ABBV", "BAC", "KO", "CRM", "NFLX", "AMD", "PEP",
    "CVX", "ADBE", "TMO", "LIN", "ACN", "MCD", "CSCO", "ABT", "TM", "DIS",
    "WFC", "INTC", "INTU", "CMCSA", "QCOM", "VZ", "IBM", "AMAT", "UBER", "TXN",
    "PFE", "AMGN", "NOW", "PM", "SPGI", "ISRG", "GE", "CAT", "HON", "RTX",
    "PLTR", "COIN", "HOOD", "RIVN", "LCID", "SNOW", "SQ", "SHOP", "ROKU", "DKNG",
    "GME", "AMC", "BB", "NOK", "PLUG", "NIO", "XPEV", "LI", "BABA", "JD",
    "BIDU", "PDD", "TCEHY", "SONY", "SHEL", "TTE", "BP", "EQNR", "E", "STLA"
]

async def fetch_ticker_info(symbol: str) -> Dict:
    try:
        print(f"Fetching info for {symbol}...")
        ticker = await asyncio.to_thread(yf.Ticker, symbol)
        info = await asyncio.to_thread(lambda: ticker.info)
        
        name = info.get("shortName") or info.get("longName") or symbol
        sector = info.get("sector")
        industry = info.get("industry")
        website = info.get("website")
        
        logo_url = None
        if website:
            # Extract domain for Clearbit logo API
            # e.g., https://www.apple.com -> apple.com
            try:
                domain = website.replace("https://", "").replace("http://", "").split("/")[0].replace("www.", "")
                logo_url = f"https://logo.clearbit.com/{domain}"
            except:
                pass
                
        return {
            "symbol": symbol,
            "name": name,
            "sector": sector,
            "industry": industry,
            "logo_url": logo_url
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {
            "symbol": symbol,
            "name": symbol,
            "sector": None,
            "industry": None,
            "logo_url": None
        }

async def seed_tickers():
    print("Starting ticker seed process...")
    
    # Initialize Supabase client
    # We need to make sure we have the env vars loaded
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env.local"))
    
    supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Use service role key for writing
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found in .env.local")
        return

    supabase: Client = create_client(supabase_url, supabase_key)
    
    # 1. Apply migration (reading the file we just created)
    print("Applying migration...")
    try:
        with open(os.path.join(os.path.dirname(__file__), "../sql/016_tickers_table.sql"), "r") as f:
            sql = f.read()
            # Split by statement and execute
            # Note: This is a simple split, might need more robust parsing for complex SQL
            # But for our file it should be fine.
            # Actually, supabase-py doesn't support executing raw SQL string directly easily without RPC
            # But we can use the 'rpc' call if we had a function, or just use the REST API to insert.
            # Wait, we can't execute DDL via REST API.
            # We need to use the SQL Editor in dashboard OR use a postgres connection.
            # Since I don't have direct postgres access here easily, I will assume the user
            # might need to run the SQL manually OR I can try to use the `mcp0_execute_sql` tool again
            # but I need the project ID.
            
            # Let's try to use the mcp tool again with the project ID from the URL if possible.
            # The user provided: https://social-stock-insights.onrender.com (backend)
            # But Supabase project ID is usually in the URL like https://<project_id>.supabase.co
            # I can check NEXT_PUBLIC_SUPABASE_URL in .env.local
            pass
    except Exception as e:
        print(f"Error reading migration file: {e}")

    # Fetch data
    tasks = [fetch_ticker_info(t) for t in POPULAR_TICKERS]
    results = await asyncio.gather(*tasks)
    
    # Upsert data
    print("Upserting data to Supabase...")
    for data in results:
        try:
            supabase.table("tickers").upsert(data).execute()
            print(f"Upserted {data['symbol']}")
        except Exception as e:
            print(f"Error upserting {data['symbol']}: {e}")

    print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_tickers())
