from typing import Any, Dict, List
import asyncio
import logging
from datetime import datetime

import yfinance as yf
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .supabase_client import get_supabase_client
from .llm import call_openrouter_chat, call_cohere_embedding
from .market_signals import update_market_alignments_batch
from datetime import timedelta


# Set up logging
logger = logging.getLogger(__name__)


MAX_RETRIES = 3
RETRY_DELAYS = [10, 60, 300]  # 10 seconds, 1 minute, 5 minutes


# Moderation keywords and patterns
MODERATION_CONFIG = {
    "low_quality_indicators": [
        "guaranteed profit", "100% return", "can't lose", "get rich quick",
        "financial advice", "not financial advice", "trust me bro",
    ],
    "spam_patterns": [
        "join my discord", "dm me for", "follow for more", "link in bio",
    ],
    "min_content_length": 20,
    "max_ticker_ratio": 0.5,  # Ratio of tickers to words
}


# Global scheduler instance
scheduler = AsyncIOScheduler()


def check_content_moderation(content: str, tickers: List[str], parsed_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basic content moderation check for post quality and appropriateness.
    Returns moderation result with flags and adjusted quality score.
    """
    flags: List[str] = []
    quality_adjustment = 0.0
    
    content_lower = content.lower()
    words = content.split()
    
    # Check minimum content length
    if len(content) < MODERATION_CONFIG["min_content_length"]:
        flags.append("too_short")
        quality_adjustment -= 0.2
    
    # Check for low-quality indicators
    for indicator in MODERATION_CONFIG["low_quality_indicators"]:
        if indicator in content_lower:
            flags.append(f"low_quality:{indicator[:20]}")
            quality_adjustment -= 0.1
    
    # Check for spam patterns
    for pattern in MODERATION_CONFIG["spam_patterns"]:
        if pattern in content_lower:
            flags.append(f"spam:{pattern[:20]}")
            quality_adjustment -= 0.3
    
    # Check ticker-to-content ratio (prevent ticker spam)
    if len(words) > 0 and len(tickers) > 0:
        ticker_ratio = len(tickers) / len(words)
        if ticker_ratio > MODERATION_CONFIG["max_ticker_ratio"]:
            flags.append("ticker_spam")
            quality_adjustment -= 0.2
    
    # Check LLM-generated flags if present
    llm_flags = parsed_result.get("moderation_flags", [])
    if llm_flags:
        flags.extend(llm_flags)
    
    # Determine moderation status
    if any("spam" in f for f in flags):
        status = "flagged"
    elif len(flags) > 3:
        status = "review_needed"
    elif quality_adjustment < -0.3:
        status = "low_quality"
    else:
        status = "approved"
    
    return {
        "status": status,
        "flags": flags,
        "quality_adjustment": max(-0.5, quality_adjustment),  # Cap adjustment
    }


async def update_user_reputation_aggregated(
    supabase,
    user_id: str,
    new_quality_score: float,
    moderation_status: str
) -> None:
    """
    Update user reputation with weighted aggregation instead of simple overwrite.
    Uses rolling average based on post count with decay for older posts.
    """
    try:
        # Fetch current reputation
        rep_result = supabase.table("reputation").select("*").eq("user_id", user_id).execute()
        
        # Get user's post count and average quality
        posts_result = supabase.table("posts").select(
            "id"
        ).eq("user_id", user_id).eq("llm_status", "processed").execute()
        
        post_count = len(posts_result.data) if posts_result.data else 1
        
        # Calculate engagement score from post_engagement
        engagement_result = supabase.table("post_engagement").select(
            "type"
        ).in_("post_id", [p["id"] for p in (posts_result.data or [])]).execute()
        
        engagement_score = 0.0
        if engagement_result.data:
            likes = sum(1 for e in engagement_result.data if e["type"] == "like")
            dislikes = sum(1 for e in engagement_result.data if e["type"] == "dislike")
            comments = sum(1 for e in engagement_result.data if e["type"] == "comment")
            engagement_score = min(1.0, (likes * 0.1 + comments * 0.2 - dislikes * 0.1) / max(post_count, 1))
        
        if rep_result.data:
            # Existing reputation - calculate weighted average
            current_rep = rep_result.data[0]
            current_score = float(current_rep.get("overall_score", 0.5))
            
            # Weighted average: give more weight to historical score as post count increases
            # This prevents single posts from dramatically changing reputation
            weight_factor = min(0.8, post_count / (post_count + 5))  # Caps at 80% weight for history
            new_overall = (current_score * weight_factor) + (new_quality_score * (1 - weight_factor))
            
            # Apply moderation penalty
            if moderation_status in ["flagged", "low_quality"]:
                new_overall *= 0.9  # 10% penalty
            
            # Calculate consistency score (how consistent are quality scores)
            consistency_score = current_rep.get("consistency_score", 0.5)
            score_diff = abs(new_quality_score - current_score)
            new_consistency = (consistency_score * 0.7) + ((1 - score_diff) * 0.3)
            
            supabase.table("reputation").update({
                "overall_score": round(new_overall, 4),
                "engagement_score": round(engagement_score, 4),
                "consistency_score": round(new_consistency, 4),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("user_id", user_id).execute()
            
        else:
            # New user - initialize reputation
            initial_score = new_quality_score
            if moderation_status in ["flagged", "low_quality"]:
                initial_score *= 0.9
                
            supabase.table("reputation").insert({
                "user_id": user_id,
                "overall_score": round(initial_score, 4),
                "engagement_score": 0.0,
                "consistency_score": 0.5,
                "historical_accuracy": 0.0,
                "community_impact": 0.0,
            }).execute()
        
        logger.info(f"Updated reputation for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error updating reputation for user {user_id}: {e}")


async def process_post(post_id: str) -> None:
    """
    Fetch a post by id, run LLM analysis, write insights, embeddings, and audit logs.
    Includes comprehensive error handling and retry logic.
    """
    supabase = get_supabase_client()
    
    try:
        # Fetch post
        result = supabase.table("posts").select("*").eq("id", post_id).execute()
        if not result.data:
            logger.warning(f"Post {post_id} not found")
            return
        
        post = result.data[0]
        
        # Check if already processed
        if post.get("llm_status") == "processed":
            logger.info(f"Post {post_id} already processed, skipping")
            return
        
        tickers = post.get("tickers") or []
        retry_count = post.get("retry_count", 0)

        try:
            # Call LLM for comprehensive analysis
            llm_result = await call_openrouter_chat("analyze_post_comprehensive", post["content"], tickers)
            parsed = llm_result["parsed"]

            quality_score = parsed.get("quality_score", 0.5)
            summary = parsed.get("summary")
            explanation = parsed.get("explanation")
            sentiment = parsed.get("sentiment", "neutral")
            
            # Run content moderation check
            moderation_result = check_content_moderation(post["content"], tickers, parsed)
            
            # Adjust quality score based on moderation
            adjusted_quality = max(0.0, min(1.0, quality_score + moderation_result["quality_adjustment"]))
            
            logger.info(f"Post {post_id} moderation: {moderation_result['status']}, flags: {moderation_result['flags']}")

            # Insert insights row with enhanced semantic tags
            supabase.table("insights").insert({
                "post_id": post["id"],
                "insight_type": parsed.get("insight_type"),
                "sector": parsed.get("sector"),
                "sub_sector": parsed.get("sub_sector"),
                "catalyst": parsed.get("catalyst"),
                "risk_profile": parsed.get("risk_profile"),
                "time_horizon": parsed.get("time_horizon"),
                "quality_score": adjusted_quality,
                "confidence_level": parsed.get("confidence_level"),
                "relevance_score": parsed.get("relevance_score"),
                "summary": summary,
                "explanation": explanation,
                "sentiment": sentiment,
                "key_points": parsed.get("key_points"),
                "potential_catalysts": parsed.get("potential_catalysts"),
                "risk_factors": parsed.get("risk_factors"),
            }).execute()

            # Insert LLM audit log with moderation info
            supabase.table("llm_audit_logs").insert({
                "post_id": post["id"],
                "task_type": "process_post",
                "input": {"content": post["content"], "tickers": tickers},
                "output": {
                    **llm_result.get("raw", {}),
                    "moderation": moderation_result,
                    "latency_exceeded": llm_result.get("latency_exceeded", False),
                    "validation_failed": llm_result.get("validation_failed", False),
                },
                "model": llm_result["model"],
                "latency_ms": llm_result["latency_ms"],
            }).execute()

            # Generate embeddings for content using Cohere (only if not flagged as spam)
            if moderation_result["status"] != "flagged":
                try:
                    content_embedding = await call_cohere_embedding(post["content"])
                    if content_embedding:
                        # Verify embedding dimension matches expected (1024 for Cohere)
                        if len(content_embedding) != 1024:
                            logger.warning(f"Unexpected embedding dimension: {len(content_embedding)} (expected 1024) for post {post_id}")
                        else:
                            supabase.table("post_embeddings").insert({
                                "post_id": post["id"],
                                "embedding": content_embedding,
                                "type": "content",
                            }).execute()
                            logger.debug(f"Inserted content embedding for post {post_id}")
                except Exception as e:
                    logger.error(f"Error inserting content embedding for post {post_id}: {e}")

                # Generate summary embedding if available
                if summary:
                    try:
                        summary_embedding = await call_cohere_embedding(summary)
                        if summary_embedding:
                            if len(summary_embedding) != 1024:
                                logger.warning(f"Unexpected summary embedding dimension: {len(summary_embedding)} (expected 1024) for post {post_id}")
                            else:
                                supabase.table("post_embeddings").insert({
                                    "post_id": post["id"],
                                    "embedding": summary_embedding,
                                    "type": "summary",
                                }).execute()
                                logger.debug(f"Inserted summary embedding for post {post_id}")
                    except Exception as e:
                        logger.error(f"Error inserting summary embedding for post {post_id}: {e}")
            else:
                logger.warning(f"Skipping embeddings for flagged post {post_id}")

            # Update reputation using aggregated calculation
            if adjusted_quality is not None:
                await update_user_reputation_aggregated(
                    supabase,
                    post["user_id"],
                    adjusted_quality,
                    moderation_result["status"]
                )
            
            # Create user_predictions entries for each ticker mentioned
            if tickers and sentiment:
                try:
                    # Map sentiment to predicted direction
                    sentiment_to_direction = {
                        "bullish": "up",
                        "bearish": "down",
                        "neutral": "neutral",
                    }
                    predicted_direction = sentiment_to_direction.get(sentiment.lower(), "neutral")
                    confidence = parsed.get("confidence_level", 0.5)
                    
                    # Create prediction for each ticker in the post
                    for ticker in tickers[:5]:  # Limit to first 5 tickers to avoid spam
                        try:
                            supabase.table("user_predictions").insert({
                                "post_id": post["id"],
                                "user_id": post["user_id"],
                                "ticker": ticker.upper(),
                                "predicted_direction": predicted_direction,
                                "confidence": float(confidence) if confidence is not None else 0.5,
                                "outcome": "pending",  # Will be verified later by market_alignments
                            }).execute()
                            logger.debug(f"Created prediction for {ticker} in post {post_id}")
                        except Exception as pred_error:
                            # Handle duplicate key errors gracefully (if prediction already exists)
                            if "duplicate" not in str(pred_error).lower():
                                logger.warning(f"Error creating prediction for {ticker}: {pred_error}")
                except Exception as e:
                    logger.warning(f"Error creating user predictions for post {post_id}: {e}")
            
            # Mark post as processed
            supabase.table("posts").update({
                "llm_status": "processed",
                "error_message": None,
            }).eq("id", post["id"]).execute()
            
            logger.info(f"Successfully processed post {post_id}")
            
        except Exception as e:
            error_message = f"Error processing post: {str(e)}"
            logger.error(error_message)
            
            # Increment retry count
            new_retry_count = retry_count + 1
            
            if new_retry_count >= MAX_RETRIES:
                # Mark as failed after max retries
                supabase.table("posts").update({
                    "llm_status": "failed",
                    "error_message": error_message,
                    "retry_count": new_retry_count,
                }).eq("id", post["id"]).execute()
                logger.error(f"Post {post_id} failed after {MAX_RETRIES} retries")
            else:
                # Schedule retry with delay using asyncio
                supabase.table("posts").update({
                    "llm_status": "pending",
                    "error_message": error_message,
                    "retry_count": new_retry_count,
                }).eq("id", post["id"]).execute()
                
                delay = RETRY_DELAYS[new_retry_count - 1] if new_retry_count <= len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                logger.info(f"Retrying post {post_id} in {delay} seconds (attempt {new_retry_count + 1}/{MAX_RETRIES})")
                
                # Schedule retry using asyncio
                async def delayed_retry():
                    await asyncio.sleep(delay)
                    await process_post(post_id)
                
                asyncio.create_task(delayed_retry())
    
    except Exception as e:
        # Catastrophic error
        logger.error(f"Catastrophic error processing post {post_id}: {str(e)}")
        try:
            supabase.table("posts").update({
                "llm_status": "failed",
                "error_message": f"Catastrophic error: {str(e)}",
            }).eq("id", post_id).execute()
        except:
            pass  # Best effort


async def recompute_reputation() -> None:
    """
    Cron job to update user reputation based on engagement.
    Uses the recompute_reputation RPC function.
    """
    supabase = get_supabase_client()
    try:
        supabase.rpc("recompute_reputation").execute()
        logger.info("Successfully recomputed reputation scores")
    except Exception as e:
        logger.error(f"Error recomputing reputation: {str(e)}")


async def retry_failed_posts() -> None:
    """
    Cron job to retry failed posts that might have been due to temporary issues.
    Only retries posts that failed less than 24 hours ago.
    """
    supabase = get_supabase_client()
    try:
        # Find recent failed posts with low retry counts
        result = supabase.table("posts").select("id, retry_count").eq(
            "llm_status", "failed"
        ).lt("retry_count", MAX_RETRIES).execute()
        
        if result.data:
            for post in result.data:
                # Reset to pending
                supabase.table("posts").update({
                    "llm_status": "pending",
                }).eq("id", post["id"]).execute()
                
                # Process using asyncio.create_task
                asyncio.create_task(process_post(post["id"]))
                logger.info(f"Re-queued failed post {post['id']}")
    except Exception as e:
        logger.error(f"Error retrying failed posts: {str(e)}")


async def process_pending_posts() -> None:
    """
    Cron job to process any pending posts that might have been missed.
    Runs every 5 minutes to catch stragglers.
    """
    supabase = get_supabase_client()
    try:
        # Find pending posts
        result = supabase.table("posts").select("id").eq(
            "llm_status", "pending"
        ).order("created_at", desc=False).limit(10).execute()
        
        if result.data:
            for post in result.data:
                asyncio.create_task(process_post(post["id"]))
            logger.info(f"Enqueued {len(result.data)} pending posts")
    except Exception as e:
        logger.error(f"Error processing pending posts: {str(e)}")


async def score_market_alignments() -> None:
    """
    Cron job to score posts against actual market movements.
    Runs daily to update historical accuracy for recent posts.
    """
    try:
        result = await update_market_alignments_batch(limit=100)
        logger.info(f"Market alignment scoring complete: {result}")
    except Exception as e:
        logger.error(f"Error scoring market alignments: {str(e)}")


async def snapshot_market_data() -> None:
    """
    Cron job to snapshot market data for trending tickers.
    Stores OHLC data in market_snapshots table for historical tracking.
    """
    supabase = get_supabase_client()
    try:
        # Get trending tickers from the last 24 hours
        result = supabase.rpc("get_trending_tickers", {
            "p_hours": 24,
            "p_limit": 50,  # Snapshot top 50 trending tickers
        }).execute()
        
        if not result.data:
            # Fallback to popular tickers if no trending data
            tickers = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "GOOGL", "AMZN", "META", "PLTR", "COIN"]
        else:
            tickers = [row["ticker"] for row in result.data]
        
        snapshot_count = 0
        
        async def snapshot_ticker(ticker: str) -> bool:
            """Snapshot a single ticker's market data."""
            try:
                ticker_obj = await asyncio.to_thread(yf.Ticker, ticker)
                
                def get_history():
                    # Get today's data (1 day, 1 minute intervals for intraday)
                    hist = ticker_obj.history(period="1d", interval="1m")
                    if hist.empty:
                        # Fallback to daily data
                        hist = ticker_obj.history(period="5d", interval="1d")
                    return hist
                
                hist = await asyncio.to_thread(get_history)
                
                if hist.empty:
                    logger.warning(f"No market data available for {ticker}")
                    return False
                
                # Get the most recent row
                latest = hist.iloc[-1]
                
                # Get current price from fast_info as fallback
                try:
                    fast_info = await asyncio.to_thread(lambda: ticker_obj.fast_info)
                    current_price = fast_info.last_price if fast_info.last_price else float(latest["Close"])
                except:
                    current_price = float(latest["Close"])
                
                # Insert snapshot
                supabase.table("market_snapshots").insert({
                    "ticker": ticker,
                    "price": float(current_price),
                    "volume": float(latest["Volume"]) if "Volume" in latest else None,
                    "open": float(latest["Open"]) if "Open" in latest else None,
                    "high": float(latest["High"]) if "High" in latest else None,
                    "low": float(latest["Low"]) if "Low" in latest else None,
                    "close": float(latest["Close"]) if "Close" in latest else None,
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "yfinance_snapshot",
                }).execute()
                
                return True
            except Exception as e:
                logger.error(f"Error snapshotting {ticker}: {e}")
                return False
        
        # Snapshot all tickers in parallel (limit concurrency)
        tasks = [snapshot_ticker(ticker) for ticker in tickers[:30]]  # Limit to 30 to avoid rate limits
        results = await asyncio.gather(*tasks, return_exceptions=True)
        snapshot_count = sum(1 for r in results if r is True)
        
        logger.info(f"Successfully snapshotted {snapshot_count}/{len(tickers)} tickers")
        
    except Exception as e:
        logger.error(f"Error snapshotting market data: {str(e)}")


async def detect_trends_automatically() -> None:
    """
    Scheduled job to automatically detect trends from recent posts.
    Runs periodically to identify emerging patterns and store them in trends/post_trends tables.
    """
    supabase = get_supabase_client()
    try:
        # Use 24h time window for trend detection
        time_window = "24h"
        hours = 24
        min_posts = 5
        threshold = datetime.utcnow() - timedelta(hours=hours)
        
        # Fetch recent processed posts
        posts_result = supabase.table("posts").select(
            "id, content, tickers, created_at"
        ).eq("llm_status", "processed").gte(
            "created_at", threshold.isoformat()
        ).order("created_at", desc=True).limit(100).execute()
        
        if not posts_result.data or len(posts_result.data) < min_posts:
            logger.info(f"Not enough posts for trend detection: {len(posts_result.data) if posts_result.data else 0} posts")
            return
        
        # Prepare posts for LLM analysis
        posts_content = []
        post_ids = []
        all_tickers = set()
        
        for post in posts_result.data[:50]:  # Limit to avoid token limits
            posts_content.append(post["content"][:500])  # Truncate long posts
            post_ids.append(post["id"])
            if post.get("tickers"):
                all_tickers.update(post["tickers"])
        
        # Call LLM for trend detection
        combined_context = f"Recent posts from the last {time_window}:\n\n" + "\n---\n".join(posts_content)
        
        llm_result = await call_openrouter_chat(
            "detect_community_trends",
            combined_context,
            list(all_tickers)
        )
        
        parsed = llm_result["parsed"]
        detected_trends = parsed.get("trends", [])
        
        if not detected_trends:
            logger.info("No trends detected by LLM")
            return
        
        # Store detected trends in database and link to posts
        created_trends = []
        for trend_data in detected_trends:
            # Calculate expiration (trends expire based on time window)
            expires_at = datetime.utcnow() + timedelta(hours=hours * 2)
            
            trend_insert = {
                "trend_type": trend_data.get("trend_type", "community"),
                "ticker": trend_data.get("supporting_tickers", [None])[0] if trend_data.get("supporting_tickers") else None,
                "sector": trend_data.get("sector"),
                "description": trend_data.get("description", ""),
                "confidence": trend_data.get("confidence", 0.5),
                "sentiment_direction": trend_data.get("sentiment_direction"),
                "time_window": time_window,
                "key_themes": trend_data.get("key_themes", []),
                "supporting_post_ids": post_ids[:10],  # Sample of supporting posts
                "expires_at": expires_at.isoformat(),
            }
            
            try:
                result = supabase.table("trends").insert(trend_insert).execute()
                if result.data:
                    trend_id = result.data[0]["id"]
                    created_trends.append(trend_id)
                    
                    # Link posts to this trend via post_trends junction table
                    # Use a sample of relevant posts (those mentioning the trend's ticker or sector)
                    relevant_post_ids = post_ids[:20]  # Limit to avoid too many inserts
                    
                    for post_id in relevant_post_ids:
                        try:
                            # Calculate relevance score (simplified - could be improved)
                            relevance_score = 0.7  # Default relevance
                            
                            supabase.table("post_trends").insert({
                                "post_id": post_id,
                                "trend_id": trend_id,
                                "relevance_score": relevance_score,
                            }).execute()
                        except Exception as link_error:
                            # Handle duplicate key errors gracefully
                            if "duplicate" not in str(link_error).lower():
                                logger.warning(f"Error linking post {post_id} to trend {trend_id}: {link_error}")
            except Exception as trend_error:
                logger.error(f"Error creating trend: {trend_error}")
        
        logger.info(f"Successfully detected and stored {len(created_trends)} trends")
        
    except Exception as e:
        logger.error(f"Error in automatic trend detection: {str(e)}")


async def rerank_by_market_events() -> None:
    """
    Dynamic re-ranking based on current market events.
    Boosts relevance of posts about tickers with significant recent activity.
    """
    supabase = get_supabase_client()
    try:
        # Get recent market snapshots to identify active tickers
        # For now, we'll just boost relevance scores for recent posts
        # A full implementation would integrate with real-time market data
        
        # Find posts from the last 24 hours about trending tickers
        result = supabase.rpc("get_trending_tickers", {
            "p_hours": 24,
            "p_limit": 20,
        }).execute()
        
        if result.data:
            trending_tickers = [row["ticker"] for row in result.data]
            
            # Boost relevance scores for insights about these tickers
            for ticker in trending_tickers:
                # Get posts for this ticker
                posts_result = supabase.table("posts").select("id").contains("tickers", [ticker]).execute()
                if posts_result.data:
                    post_ids = [p["id"] for p in posts_result.data]
                    # Get current insights and boost their scores
                    insights_result = supabase.table("insights").select(
                        "id, relevance_score"
                    ).in_("post_id", post_ids).execute()
                    
                    for insight in (insights_result.data or []):
                        current_score = insight.get("relevance_score", 0.5) or 0.5
                        boosted_score = min(1.0, current_score * 1.2)
                        supabase.table("insights").update({
                            "relevance_score": boosted_score
                        }).eq("id", insight["id"]).execute()
            
            logger.info(f"Boosted relevance for {len(trending_tickers)} trending tickers")
    except Exception as e:
        logger.error(f"Error in dynamic re-ranking: {str(e)}")


def get_processing_stats() -> Dict[str, Any]:
    """
    Get worker processing statistics.
    Can be called from admin endpoints.
    """
    supabase = get_supabase_client()
    try:
        result = supabase.table("platform_stats").select("*").execute()
        if result.data:
            return result.data[0]
        return {}
    except Exception as e:
        return {"error": str(e)}


def start_scheduler() -> None:
    """
    Initialize and start the APScheduler with all cron jobs.
    """
    # Cron job: recompute reputation every hour at minute 0
    scheduler.add_job(
        recompute_reputation,
        'cron',
        minute=0,
        id='recompute_reputation',
        replace_existing=True
    )
    
    # Cron job: retry failed posts every hour at minute 30
    scheduler.add_job(
        retry_failed_posts,
        'cron',
        minute=30,
        id='retry_failed_posts',
        replace_existing=True
    )
    
    # Cron job: process pending posts every 5 minutes
    scheduler.add_job(
        process_pending_posts,
        'cron',
        minute='*/5',
        id='process_pending_posts',
        replace_existing=True
    )
    
    # Cron job: score market alignments daily at 2 AM
    scheduler.add_job(
        score_market_alignments,
        'cron',
        hour=2,
        minute=0,
        id='score_market_alignments',
        replace_existing=True
    )
    
    # Cron job: rerank by market events every 15 minutes
    scheduler.add_job(
        rerank_by_market_events,
        'cron',
        minute='*/15',
        id='rerank_by_market_events',
        replace_existing=True
    )
    
    # Cron job: snapshot market data every 30 minutes
    scheduler.add_job(
        snapshot_market_data,
        'cron',
        minute='*/30',
        id='snapshot_market_data',
        replace_existing=True
    )
    
    # Cron job: detect trends automatically every 6 hours
    scheduler.add_job(
        detect_trends_automatically,
        'cron',
        hour='*/6',
        minute=0,
        id='detect_trends_automatically',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler started with all cron jobs")


def shutdown_scheduler() -> None:
    """
    Gracefully shutdown the scheduler.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shut down")

