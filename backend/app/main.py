import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import insights, feed, market, users, admin, trends, transparency, chat, posts
from .scheduler import start_scheduler, shutdown_scheduler


def load_popular_tickers() -> list[str]:
    """Load popular tickers from config file."""
    config_path = Path(__file__).parent / "popular_tickers.json"
    try:
        with open(config_path) as f:
            data = json.load(f)
            # Return priority tickers for cache warming
            return data.get("priority_tickers", [])
    except Exception:
        # Fallback to basic list if file not found
        return ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "GOOGL", "AMZN", "META"]


async def warm_ticker_cache():
    """Pre-warm cache for popular tickers on startup."""
    import yfinance as yf
    from datetime import datetime
    
    tickers = load_popular_tickers()
    print(f"🔥 Warming cache for {len(tickers)} popular tickers...")
    
    async def fetch_and_cache(symbol: str):
        try:
            ticker_obj = await asyncio.to_thread(yf.Ticker, symbol)
            info = await asyncio.to_thread(lambda: ticker_obj.fast_info)
            
            if info.last_price is not None:
                data = {
                    "ticker": symbol,
                    "price": info.last_price,
                    "previous_close": info.previous_close,
                    "change": info.last_price - info.previous_close,
                    "change_percent": ((info.last_price - info.previous_close) / info.previous_close) * 100,
                    "volume": info.last_volume,
                    "currency": info.currency,
                    "from_cache": False,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                # Store in market router's cache
                market._cache_market_data(symbol, data)
                return True
        except Exception as e:
            print(f"  ⚠️ Failed to cache {symbol}: {e}")
        return False
    
    # Fetch in parallel with concurrency limit
    results = await asyncio.gather(*[fetch_and_cache(t) for t in tickers])
    cached = sum(1 for r in results if r)
    print(f"✅ Cached {cached}/{len(tickers)} tickers")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: warm the cache and start scheduler
    await warm_ticker_cache()
    start_scheduler()
    yield
    # Shutdown: stop scheduler
    shutdown_scheduler()


app = FastAPI(title="Social Stocks Insights API", lifespan=lifespan)

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add allowed origins from env
import os
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    origins.extend([origin.strip() for origin in env_origins.split(",")])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


app.include_router(insights.router, prefix="/insights", tags=["insights"])
app.include_router(feed.router, prefix="/feed", tags=["feed"])
app.include_router(market.router, prefix="/market", tags=["market"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(trends.router, prefix="/trends", tags=["trends"])
app.include_router(transparency.router, prefix="/transparency", tags=["transparency"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(posts.router, prefix="/posts", tags=["posts"])
