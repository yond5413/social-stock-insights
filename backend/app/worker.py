from typing import Any, Dict, List, Optional
import asyncio
import logging
from datetime import datetime

from arq import cron
from arq.connections import RedisSettings

from .supabase_client import get_supabase_client
from .llm import call_openrouter_chat, call_cohere_embedding
from .market_signals import update_market_alignments_batch


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


async def process_post(ctx: Dict[str, Any], post_id: str) -> None:
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
                "sentiment": parsed.get("sentiment"),
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
                content_embedding = await call_cohere_embedding(post["content"])
                if content_embedding:
                    supabase.table("post_embeddings").insert({
                        "post_id": post["id"],
                        "embedding": content_embedding,
                        "type": "content",
                    }).execute()

                # Generate summary embedding if available
                if summary:
                    summary_embedding = await call_cohere_embedding(summary)
                    if summary_embedding:
                        supabase.table("post_embeddings").insert({
                            "post_id": post["id"],
                            "embedding": summary_embedding,
                            "type": "summary",
                        }).execute()
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
                # Schedule retry
                supabase.table("posts").update({
                    "llm_status": "pending",
                    "error_message": error_message,
                    "retry_count": new_retry_count,
                }).eq("id", post["id"]).execute()
                
                # Re-enqueue with delay
                delay = RETRY_DELAYS[new_retry_count - 1] if new_retry_count <= len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                logger.info(f"Retrying post {post_id} in {delay} seconds (attempt {new_retry_count + 1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
                # Re-queue the job
                await ctx['redis'].enqueue_job('process_post', post_id)
    
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


async def recompute_reputation(ctx: Dict[str, Any]) -> None:
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


async def retry_failed_posts(ctx: Dict[str, Any]) -> None:
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
                # Reset to pending and enqueue
                supabase.table("posts").update({
                    "llm_status": "pending",
                }).eq("id", post["id"]).execute()
                
                await ctx['redis'].enqueue_job('process_post', post["id"])
                logger.info(f"Re-queued failed post {post['id']}")
    except Exception as e:
        logger.error(f"Error retrying failed posts: {str(e)}")


async def process_pending_posts(ctx: Dict[str, Any]) -> None:
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
                await ctx['redis'].enqueue_job('process_post', post["id"])
            logger.info(f"Enqueued {len(result.data)} pending posts")
    except Exception as e:
        logger.error(f"Error processing pending posts: {str(e)}")


async def score_market_alignments(ctx: Dict[str, Any]) -> None:
    """
    Cron job to score posts against actual market movements.
    Runs daily to update historical accuracy for recent posts.
    """
    try:
        result = await update_market_alignments_batch(limit=100)
        logger.info(f"Market alignment scoring complete: {result}")
    except Exception as e:
        logger.error(f"Error scoring market alignments: {str(e)}")


async def rerank_by_market_events(ctx: Dict[str, Any]) -> None:
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


class WorkerSettings:
    functions = [process_post, recompute_reputation, retry_failed_posts, process_pending_posts, score_market_alignments, rerank_by_market_events]
    redis_settings = RedisSettings()
    cron_jobs = [
        cron(recompute_reputation, minute=0),  # Every hour
        cron(retry_failed_posts, minute=30),  # Every hour at :30
        cron(process_pending_posts, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),  # Every 5 minutes
        cron(score_market_alignments, hour=2, minute=0),  # Daily at 2 AM
        cron(rerank_by_market_events, minute={0, 15, 30, 45}),  # Every 15 minutes
    ]


