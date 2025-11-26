"""
Market Signal Analysis and Alignment Scoring

This module tracks how well posts' predictions align with actual market movements,
enabling reputation scoring based on historical accuracy.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import yfinance as yf

from .supabase_client import get_supabase_client


async def calculate_market_alignment_score(
    post_id: str,
    ticker: str,
    predicted_sentiment: str,  # bullish, bearish, neutral
    post_created_at: datetime,
) -> Dict[str, Any]:
    """
    Compare post sentiment/prediction vs. actual price movement.
    
    Returns alignment score (0-1) and analysis of timing and accuracy.
    """
    try:
        # Get price at post time and 24 hours later
        ticker_obj = await asyncio.to_thread(yf.Ticker, ticker)
        
        def get_history():
            # Get historical data for the period
            end_date = post_created_at + timedelta(days=2)
            start_date = post_created_at - timedelta(days=1)
            return ticker_obj.history(start=start_date, end=end_date)
        
        hist = await asyncio.to_thread(get_history)
        
        if hist.empty or len(hist) < 2:
            return {
                "alignment_score": None,
                "error": "Insufficient price data"
            }
        
        # Find closest price to post time
        post_date = post_created_at.date()
        
        # Get price at or near post time
        price_at_post = None
        price_24h_later = None
        
        # Try to find the price on the post date
        if post_date in hist.index:
            price_at_post = hist.loc[post_date]['Close']
        else:
            # Use the closest available price
            price_at_post = hist.iloc[0]['Close']
        
        # Get price 24 hours later (or closest available)
        future_date = post_created_at + timedelta(days=1)
        if future_date.date() in hist.index:
            price_24h_later = hist.loc[future_date.date()]['Close']
        elif len(hist) >= 2:
            price_24h_later = hist.iloc[-1]['Close']
        
        if price_at_post is None or price_24h_later is None:
            return {
                "alignment_score": None,
                "error": "Could not determine prices"
            }
        
        # Calculate actual movement
        price_change = price_24h_later - price_at_post
        price_change_percent = (price_change / price_at_post) * 100
        
        # Determine actual direction
        if price_change_percent > 2:
            actual_direction = "up"
        elif price_change_percent < -2:
            actual_direction = "down"
        else:
            actual_direction = "neutral"
        
        # Map sentiment to predicted direction
        sentiment_to_direction = {
            "bullish": "up",
            "bearish": "down",
            "neutral": "neutral",
        }
        predicted_direction = sentiment_to_direction.get(predicted_sentiment.lower(), "neutral")
        
        # Calculate alignment score
        if predicted_direction == actual_direction:
            # Perfect alignment
            alignment_score = 1.0
            timing_accuracy = "on_time"
        elif predicted_direction == "neutral" or actual_direction == "neutral":
            # Partial credit for neutral predictions/outcomes
            alignment_score = 0.5
            timing_accuracy = "neutral"
        else:
            # Wrong direction
            alignment_score = 0.0
            timing_accuracy = "wrong"
        
        # Bonus for magnitude (if predicted big move and got big move)
        if abs(price_change_percent) > 5 and predicted_direction == actual_direction:
            alignment_score = min(1.0, alignment_score + 0.1)
            timing_accuracy = "early" if abs(price_change_percent) > 10 else "on_time"
        
        return {
            "alignment_score": alignment_score,
            "predicted_direction": predicted_direction,
            "actual_direction": actual_direction,
            "timing_accuracy": timing_accuracy,
            "price_at_post": float(price_at_post),
            "price_24h_later": float(price_24h_later),
            "price_change_percent": float(price_change_percent),
            "explanation": _generate_alignment_explanation(
                predicted_direction,
                actual_direction,
                price_change_percent,
                timing_accuracy
            )
        }
        
    except Exception as e:
        return {
            "alignment_score": None,
            "error": str(e)
        }


def _generate_alignment_explanation(
    predicted: str,
    actual: str,
    change_percent: float,
    timing: str
) -> str:
    """Generate human-readable explanation of alignment."""
    if predicted == actual:
        if timing == "early":
            return f"Correctly predicted {actual} movement. Post was early on a major trend ({change_percent:+.1f}%)."
        return f"Correctly predicted {actual} movement ({change_percent:+.1f}%)."
    elif timing == "neutral":
        return f"Predicted {predicted}, market moved {actual} with minimal change ({change_percent:+.1f}%)."
    else:
        return f"Predicted {predicted} but market moved {actual} ({change_percent:+.1f}%)."


async def update_market_alignments_batch(limit: int = 50) -> Dict[str, Any]:
    """
    Background job to update market alignment scores for recent posts.
    
    This should be run periodically (e.g., daily) to score posts after they've
    had time to be validated by market movements.
    """
    supabase = get_supabase_client()
    
    try:
        # Find posts from 24-48 hours ago that haven't been scored yet
        threshold_end = datetime.utcnow() - timedelta(hours=24)
        threshold_start = datetime.utcnow() - timedelta(hours=48)
        
        # Get posts with insights that need scoring
        posts_result = supabase.table("posts").select(
            "id, user_id, tickers, created_at"
        ).eq("llm_status", "processed").gte(
            "created_at", threshold_start.isoformat()
        ).lte(
            "created_at", threshold_end.isoformat()
        ).limit(limit).execute()
        
        if not posts_result.data:
            return {
                "message": "No posts to score",
                "scored_count": 0,
            }
        
        scored_count = 0
        
        for post in posts_result.data:
            # Get the insight for this post
            insight_result = supabase.table("insights").select(
                "sentiment"
            ).eq("post_id", post["id"]).execute()
            
            if not insight_result.data or not insight_result.data[0].get("sentiment"):
                continue
            
            sentiment = insight_result.data[0]["sentiment"]
            tickers = post.get("tickers", [])
            
            if not tickers:
                continue
            
            # Score alignment for primary ticker
            primary_ticker = tickers[0]
            post_created = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
            
            alignment_result = await calculate_market_alignment_score(
                post["id"],
                primary_ticker,
                sentiment,
                post_created
            )
            
            if alignment_result.get("alignment_score") is not None:
                # Store in market_alignments table
                supabase.table("market_alignments").insert({
                    "post_id": post["id"],
                    "user_id": post["user_id"],
                    "ticker": primary_ticker,
                    "predicted_direction": alignment_result["predicted_direction"],
                    "actual_direction": alignment_result["actual_direction"],
                    "alignment_score": alignment_result["alignment_score"],
                    "price_at_post": alignment_result["price_at_post"],
                    "price_24h_later": alignment_result["price_24h_later"],
                    "price_change_percent": alignment_result["price_change_percent"],
                    "timing_accuracy": alignment_result["timing_accuracy"],
                    "explanation": alignment_result["explanation"],
                }).execute()
                
                # Update the insight with market alignment score
                supabase.table("insights").update({
                    "market_alignment_score": alignment_result["alignment_score"],
                }).eq("post_id", post["id"]).execute()
                
                scored_count += 1
        
        return {
            "message": f"Successfully scored {scored_count} posts",
            "scored_count": scored_count,
            "total_checked": len(posts_result.data),
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "scored_count": 0,
        }


async def get_user_accuracy_stats(user_id: str) -> Dict[str, Any]:
    """
    Get historical accuracy statistics for a user.
    """
    supabase = get_supabase_client()
    
    try:
        # Get all market alignments for this user
        result = supabase.table("market_alignments").select(
            "alignment_score, ticker, timing_accuracy, created_at"
        ).eq("user_id", user_id).execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "total_predictions": 0,
                "avg_accuracy": None,
                "accuracy_by_timing": {},
                "total_tickers_analyzed": 0,
            }
        
        alignments = result.data
        scores = [a["alignment_score"] for a in alignments if a.get("alignment_score") is not None]
        
        # Group by timing
        by_timing = {}
        for alignment in alignments:
            timing = alignment.get("timing_accuracy", "unknown")
            if timing not in by_timing:
                by_timing[timing] = []
            by_timing[timing].append(alignment["alignment_score"])
        
        # Calculate averages
        timing_avgs = {
            timing: sum(scores) / len(scores) if scores else 0
            for timing, scores in by_timing.items()
        }
        
        # Unique tickers
        unique_tickers = len(set(a["ticker"] for a in alignments if a.get("ticker")))
        
        return {
            "total_predictions": len(alignments),
            "avg_accuracy": sum(scores) / len(scores) if scores else 0,
            "accuracy_by_timing": timing_avgs,
            "total_tickers_analyzed": unique_tickers,
            "best_timing": max(timing_avgs.items(), key=lambda x: x[1])[0] if timing_avgs else None,
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "total_predictions": 0,
        }

