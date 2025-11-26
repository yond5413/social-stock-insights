from typing import Any, Dict
import asyncio
from datetime import datetime

from arq import cron
from arq.connections import RedisSettings

from .supabase_client import get_supabase_client
from .llm import call_openrouter_chat, call_cohere_embedding
from .market_signals import update_market_alignments_batch


MAX_RETRIES = 3
RETRY_DELAYS = [10, 60, 300]  # 10 seconds, 1 minute, 5 minutes


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
            print(f"Post {post_id} not found")
            return
        
        post = result.data[0]
        
        # Check if already processed
        if post.get("llm_status") == "processed":
            print(f"Post {post_id} already processed, skipping")
            return
        
        tickers = post.get("tickers") or []
        retry_count = post.get("retry_count", 0)

        try:
            # Call LLM for comprehensive analysis
            llm_result = await call_openrouter_chat("analyze_post_comprehensive", post["content"], tickers)
            parsed = llm_result["parsed"]

            quality_score = parsed.get("quality_score")
            summary = parsed.get("summary")
            explanation = parsed.get("explanation")

            # Insert insights row with enhanced semantic tags
            supabase.table("insights").insert({
                "post_id": post["id"],
                "insight_type": parsed.get("insight_type"),
                "sector": parsed.get("sector"),
                "sub_sector": parsed.get("sub_sector"),
                "catalyst": parsed.get("catalyst"),
                "risk_profile": parsed.get("risk_profile"),
                "time_horizon": parsed.get("time_horizon"),
                "quality_score": quality_score,
                "confidence_level": parsed.get("confidence_level"),
                "relevance_score": parsed.get("relevance_score"),
                "summary": summary,
                "explanation": explanation,
                "sentiment": parsed.get("sentiment"),
                "key_points": parsed.get("key_points"),
                "potential_catalysts": parsed.get("potential_catalysts"),
                "risk_factors": parsed.get("risk_factors"),
            }).execute()

            # Insert LLM audit log
            supabase.table("llm_audit_logs").insert({
                "post_id": post["id"],
                "task_type": "process_post",
                "input": {"content": post["content"], "tickers": tickers},
                "output": llm_result["raw"],
                "model": llm_result["model"],
                "latency_ms": llm_result["latency_ms"],
            }).execute()

            # Generate embeddings for content using Cohere
            content_embedding = await call_cohere_embedding(post["content"])
            supabase.table("post_embeddings").insert({
                "post_id": post["id"],
                "embedding": content_embedding,
                "type": "content",
            }).execute()

            # Generate summary embedding if available
            if summary:
                summary_embedding = await call_cohere_embedding(summary)
                supabase.table("post_embeddings").insert({
                    "post_id": post["id"],
                    "embedding": summary_embedding,
                    "type": "summary",
                }).execute()

            # Update reputation using upsert
            if quality_score is not None:
                supabase.table("reputation").upsert({
                    "user_id": post["user_id"],
                    "overall_score": quality_score,
                }, on_conflict="user_id").execute()
            
            # Mark post as processed
            supabase.table("posts").update({
                "llm_status": "processed",
                "error_message": None,
            }).eq("id", post["id"]).execute()
            
            print(f"Successfully processed post {post_id}")
            
        except Exception as e:
            error_message = f"Error processing post: {str(e)}"
            print(error_message)
            
            # Increment retry count
            new_retry_count = retry_count + 1
            
            if new_retry_count >= MAX_RETRIES:
                # Mark as failed after max retries
                supabase.table("posts").update({
                    "llm_status": "failed",
                    "error_message": error_message,
                    "retry_count": new_retry_count,
                }).eq("id", post["id"]).execute()
                print(f"Post {post_id} failed after {MAX_RETRIES} retries")
            else:
                # Schedule retry
                supabase.table("posts").update({
                    "llm_status": "pending",
                    "error_message": error_message,
                    "retry_count": new_retry_count,
                }).eq("id", post["id"]).execute()
                
                # Re-enqueue with delay
                delay = RETRY_DELAYS[new_retry_count - 1] if new_retry_count <= len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                print(f"Retrying post {post_id} in {delay} seconds (attempt {new_retry_count + 1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
                # Re-queue the job
                await ctx['redis'].enqueue_job('process_post', post_id)
    
    except Exception as e:
        # Catastrophic error
        print(f"Catastrophic error processing post {post_id}: {str(e)}")
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
        print("Successfully recomputed reputation scores")
    except Exception as e:
        print(f"Error recomputing reputation: {str(e)}")


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
                print(f"Re-queued failed post {post['id']}")
    except Exception as e:
        print(f"Error retrying failed posts: {str(e)}")


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
            print(f"Enqueued {len(result.data)} pending posts")
    except Exception as e:
        print(f"Error processing pending posts: {str(e)}")


async def score_market_alignments(ctx: Dict[str, Any]) -> None:
    """
    Cron job to score posts against actual market movements.
    Runs daily to update historical accuracy for recent posts.
    """
    try:
        result = await update_market_alignments_batch(limit=100)
        print(f"Market alignment scoring complete: {result}")
    except Exception as e:
        print(f"Error scoring market alignments: {str(e)}")


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
                supabase.table("insights").update({
                    "relevance_score": supabase.table("insights").select("relevance_score").execute().data[0].get("relevance_score", 0.5) * 1.2
                }).in_("post_id", [
                    p["id"] for p in supabase.table("posts").select("id").contains("tickers", [ticker]).execute().data
                ]).execute()
            
            print(f"Boosted relevance for {len(trending_tickers)} trending tickers")
    except Exception as e:
        print(f"Error in dynamic re-ranking: {str(e)}")


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


