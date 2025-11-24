from typing import Any, Dict

from arq import cron
from arq.connections import RedisSettings

from .supabase_client import get_supabase_client
from .llm import call_openrouter_chat, call_cohere_embedding


async def process_post(ctx: Dict[str, Any], post_id: str) -> None:
    """
    Fetch a post by id, run LLM analysis, write insights, embeddings, and audit logs.
    """
    supabase = get_supabase_client()
    
    # Fetch post
    result = supabase.table("posts").select("*").eq("id", post_id).execute()
    if not result.data:
        return
    
    post = result.data[0]
    tickers = post.get("tickers") or []

    # Call LLM for tagging/summary/score
    llm_result = await call_openrouter_chat("analyze_post", post["content"], tickers)
    parsed = llm_result["parsed"]

    quality_score = parsed.get("quality_score")
    summary = parsed.get("summary")
    explanation = parsed.get("explanation")

    # Insert insights row
    supabase.table("insights").insert({
        "post_id": post["id"],
        "insight_type": parsed.get("insight_type"),
        "sector": parsed.get("sector"),
        "catalyst": parsed.get("catalyst"),
        "risk_profile": parsed.get("risk_profile"),
        "quality_score": quality_score,
        "summary": summary,
        "explanation": explanation,
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
    supabase.table("reputation").upsert({
        "user_id": post["user_id"],
        "overall_score": quality_score or 0,
    }, on_conflict="user_id").execute()
    
    # Mark post as processed
    supabase.table("posts").update({
        "llm_status": "processed"
    }).eq("id", post["id"]).execute()


async def recompute_reputation(ctx: Dict[str, Any]) -> None:
    """
    Cron job to update user reputation based on engagement.
    Uses the recompute_reputation RPC function.
    """
    supabase = get_supabase_client()
    supabase.rpc("recompute_reputation").execute()


class WorkerSettings:
    functions = [process_post, recompute_reputation]
    redis_settings = RedisSettings()
    cron_jobs = [
        cron(recompute_reputation, minute=0)
    ]


