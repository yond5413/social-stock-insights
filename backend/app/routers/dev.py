from fastapi import APIRouter, Depends

from ..supabase_client import SupabaseClient

router = APIRouter()

@router.post("/seed")
async def seed_data(supabase: SupabaseClient):
    """
    Seed the database with dummy data for testing.
    """
    # Note: You may need to create the profiles first or ensure they exist
    # For now, we'll use a dummy user ID that should exist in your Supabase auth
    dummy_user_id = "00000000-0000-0000-0000-000000000000"
    
    # Insert dummy profile
    supabase.table("profiles").upsert({
        "id": dummy_user_id,
        "username": "stockwizard",
    }, on_conflict="id").execute()

    # Insert dummy posts
    posts_data = [
        {
            "user_id": dummy_user_id,
            "content": "NVDA looks strong at support, expecting a bounce soon.",
            "tickers": ["NVDA"],
            "raw_sentiment": 0.8,
            "llm_status": "processed",
        },
        {
            "user_id": dummy_user_id,
            "content": "TSLA facing headwinds with recent production numbers.",
            "tickers": ["TSLA"],
            "raw_sentiment": -0.5,
            "llm_status": "processed",
        },
        {
            "user_id": dummy_user_id,
            "content": "AAPL earnings coming up, volatility expected.",
            "tickers": ["AAPL"],
            "raw_sentiment": 0.2,
            "llm_status": "processed",
        },
    ]
    
    insights_data = [
        {"summary": "NVDA showing strong bullish signals at key support level.", "quality_score": 0.85},
        {"summary": "Bearish outlook on TSLA due to production concerns.", "quality_score": 0.75},
        {"summary": "Neutral to bullish stance on AAPL ahead of earnings.", "quality_score": 0.80},
    ]

    # Insert posts
    result = supabase.table("posts").insert(posts_data).execute()
    
    # Insert insights for each post
    if result.data:
        for i, post in enumerate(result.data):
            supabase.table("insights").insert({
                "post_id": post["id"],
                "summary": insights_data[i]["summary"],
                "quality_score": insights_data[i]["quality_score"],
            }).execute()

    return {"status": "seeded", "posts_created": len(result.data) if result.data else 0}


