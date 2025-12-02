"""
Transparency API

Provides explanations and breakdowns of how posts are ranked, how reputation
is calculated, and access to LLM audit logs for debugging.
"""

from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..supabase_client import SupabaseClient, CurrentUserId
from ..ranking_engine import get_ranker
from ..llm import call_openrouter_chat

router = APIRouter()


@router.get("/post/{post_id}")
async def get_post_transparency(
    post_id: str,
    supabase: SupabaseClient,
    user_id: CurrentUserId,
) -> Dict[str, Any]:
    """
    Get a full breakdown of a post's ranking signals and scores.
    Shows exactly why a post is ranked the way it is.
    """
    try:
        # Get post with insights
        post_result = supabase.table("posts").select(
            "*, insights(*), profiles!posts_user_id_fkey(username)"
        ).eq("id", post_id).execute()
        
        if not post_result.data or len(post_result.data) == 0:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post_data = post_result.data[0]
        
        # Get reputation for author
        rep_result = supabase.table("reputation").select("*").eq(
            "user_id", post_data["user_id"]
        ).execute()
        
        reputation = rep_result.data[0] if rep_result.data else {}
        
        # Get engagement
        engagement_result = supabase.table("post_engagement").select(
            "type"
        ).eq("post_id", post_id).execute()
        
        like_count = sum(1 for e in engagement_result.data if e.get("type") == "like") if engagement_result.data else 0
        comment_count = sum(1 for e in engagement_result.data if e.get("type") == "comment") if engagement_result.data else 0
        
        # Get market alignment
        alignment_result = supabase.table("market_alignments").select("*").eq(
            "post_id", post_id
        ).execute()
        
        market_alignment = alignment_result.data[0] if alignment_result.data else None
        
        # Build complete post object
        complete_post = {
            **post_data,
            "quality_score": post_data.get("insights", {}).get("quality_score") if post_data.get("insights") else None,
            "confidence_level": post_data.get("insights", {}).get("confidence_level") if post_data.get("insights") else None,
            "relevance_score": post_data.get("insights", {}).get("relevance_score") if post_data.get("insights") else None,
            "market_alignment_score": post_data.get("insights", {}).get("market_alignment_score") if post_data.get("insights") else None,
            "author_reputation": reputation.get("overall_score", 0.5),
            "historical_accuracy": reputation.get("historical_accuracy", 0),
            "like_count": like_count,
            "comment_count": comment_count,
            "view_count": post_data.get("view_count", 0),
        }
        
        # Use ranker to compute signals
        ranker = get_ranker("balanced")
        ranked = ranker.rank_posts([complete_post])
        
        if not ranked:
            raise HTTPException(status_code=500, detail="Failed to compute ranking")
        
        ranked_post = ranked[0]
        
        # Generate explanation
        explanation = ranker.explain_ranking(ranked_post)
        
        return {
            "post_id": post_id,
            "final_score": ranked_post.get("final_score", 0),
            "signals": ranked_post.get("signals", {}),
            "signal_breakdown": {
                "quality": {
                    "score": ranked_post["signals"].get("quality", 0),
                    "weight": ranker.weights.get("quality", 0),
                    "weighted_contribution": ranked_post["signals"].get("quality", 0) * ranker.weights.get("quality", 0),
                    "factors": {
                        "llm_quality_score": complete_post.get("quality_score"),
                        "confidence_level": complete_post.get("confidence_level"),
                        "content_length": len(post_data.get("content", "")),
                    }
                },
                "community": {
                    "score": ranked_post["signals"].get("community", 0),
                    "weight": ranker.weights.get("community", 0),
                    "weighted_contribution": ranked_post["signals"].get("community", 0) * ranker.weights.get("community", 0),
                    "factors": {
                        "likes": like_count,
                        "comments": comment_count,
                        "views": complete_post.get("view_count", 0),
                    }
                },
                "author": {
                    "score": ranked_post["signals"].get("author", 0),
                    "weight": ranker.weights.get("author", 0),
                    "weighted_contribution": ranked_post["signals"].get("author", 0) * ranker.weights.get("author", 0),
                    "factors": {
                        "reputation": reputation.get("overall_score"),
                        "historical_accuracy": reputation.get("historical_accuracy"),
                        "post_count": reputation.get("community_impact"),
                    }
                },
                "market": {
                    "score": ranked_post["signals"].get("market", 0),
                    "weight": ranker.weights.get("market", 0),
                    "weighted_contribution": ranked_post["signals"].get("market", 0) * ranker.weights.get("market", 0),
                    "factors": {
                        "alignment_score": complete_post.get("market_alignment_score"),
                        "relevance_score": complete_post.get("relevance_score"),
                        "market_data": market_alignment,
                    }
                },
                "recency": {
                    "score": ranked_post["signals"].get("recency", 0),
                    "weight": ranker.weights.get("recency", 0),
                    "weighted_contribution": ranked_post["signals"].get("recency", 0) * ranker.weights.get("recency", 0),
                    "factors": {
                        "created_at": post_data.get("created_at"),
                        "age_hours": (datetime.utcnow() - datetime.fromisoformat(post_data["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600 if post_data.get("created_at") else None,
                    }
                },
                "diversity": {
                    "score": ranked_post["signals"].get("diversity", 0),
                    "weight": ranker.weights.get("diversity", 0),
                    "weighted_contribution": ranked_post["signals"].get("diversity", 0) * ranker.weights.get("diversity", 0),
                    "factors": {
                        "tickers": post_data.get("tickers"),
                        "sector": post_data.get("insights", {}).get("sector") if post_data.get("insights") else None,
                    }
                },
            },
            "explanation": explanation,
            "author": {
                "user_id": post_data["user_id"],
                "username": post_data.get("profiles", {}).get("username") if post_data.get("profiles") else "Unknown",
                "reputation": reputation,
            },
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting post transparency: {str(e)}")


@router.get("/user/{target_user_id}/reputation")
async def get_user_reputation_breakdown(
    target_user_id: str,
    supabase: SupabaseClient,
    user_id: CurrentUserId,  # For auth
) -> Dict[str, Any]:
    """
    Get a detailed breakdown of how a user's reputation is calculated.
    """
    try:
        # Get reputation
        rep_result = supabase.table("reputation").select("*").eq(
            "user_id", target_user_id
        ).execute()
        
        if not rep_result.data or len(rep_result.data) == 0:
            raise HTTPException(status_code=404, detail="User reputation not found")
        
        reputation = rep_result.data[0]
        
        # Get user's posts and insights
        posts_result = supabase.table("posts").select(
            "id, created_at, insights(quality_score)"
        ).eq("user_id", target_user_id).execute()
        
        # Get market alignments
        alignments_result = supabase.table("market_alignments").select(
            "alignment_score, timing_accuracy"
        ).eq("user_id", target_user_id).execute()
        
        # Get engagement
        engagement_result = supabase.rpc("get_user_engagement_stats", {
            "p_user_id": target_user_id
        }).execute()
        
        # Get sector expertise
        sector_result = supabase.rpc("get_user_sector_expertise", {
            "p_user_id": target_user_id
        }).execute()
        
        # Calculate component scores
        post_count = len(posts_result.data) if posts_result.data else 0
        quality_scores = [p.get("insights", {}).get("quality_score") for p in posts_result.data if p.get("insights") and p.get("insights").get("quality_score")] if posts_result.data else []
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        alignment_scores = [a["alignment_score"] for a in alignments_result.data if a.get("alignment_score")] if alignments_result.data else []
        avg_alignment = sum(alignment_scores) / len(alignment_scores) if alignment_scores else None
        
        return {
            "user_id": target_user_id,
            "overall_score": float(reputation["overall_score"]) if reputation.get("overall_score") else 0,
            "components": {
                "quality": {
                    "contribution": 0.4,
                    "avg_quality_score": avg_quality,
                    "post_count": post_count,
                    "description": "Based on LLM quality assessments of posts"
                },
                "historical_accuracy": {
                    "contribution": 0.3,
                    "score": float(reputation["historical_accuracy"]) if reputation.get("historical_accuracy") else 0,
                    "prediction_count": len(alignment_scores),
                    "avg_alignment": avg_alignment,
                    "description": "Based on how well predictions aligned with market movements"
                },
                "engagement": {
                    "contribution": 0.2,
                    "score": float(reputation["engagement_score"]) if reputation.get("engagement_score") else 0,
                    "stats": engagement_result.data[0] if engagement_result.data else {},
                    "description": "Based on community interactions (likes, comments)"
                },
                "consistency": {
                    "contribution": 0.1,
                    "score": float(reputation["consistency_score"]) if reputation.get("consistency_score") else 0,
                    "recent_posts": post_count,
                    "description": "Based on posting frequency and regularity"
                },
            },
            "sector_expertise": sector_result.data if sector_result.data else [],
            "updated_at": reputation.get("updated_at"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting reputation breakdown: {str(e)}")


@router.get("/llm-audit/{post_id}")
async def get_llm_audit_logs(
    post_id: str,
    supabase: SupabaseClient,
    user_id: CurrentUserId,
) -> List[Dict[str, Any]]:
    """
    Get LLM processing logs for a post (for debugging and transparency).
    Shows what the LLM analyzed and how long it took.
    """
    try:
        result = supabase.table("llm_audit_logs").select("*").eq(
            "post_id", post_id
        ).order("created_at", desc=True).execute()
        
        if not result.data:
            return []
        
        # Remove sensitive data from output
        cleaned_logs = []
        for log in result.data:
            cleaned_logs.append({
                "id": log["id"],
                "task_type": log.get("task_type"),
                "model": log.get("model"),
                "latency_ms": log.get("latency_ms"),
                "created_at": log.get("created_at"),
                "input_summary": {
                    "content_length": len(log.get("input", {}).get("content", "")) if log.get("input") else 0,
                    "tickers": log.get("input", {}).get("tickers") if log.get("input") else [],
                },
                "output_summary": {
                    "insight_type": log.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")[:100] if log.get("output") else None,
                }
            })
        
        return cleaned_logs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching LLM audit logs: {str(e)}")


@router.post("/explain-ranking")
async def explain_feed_ranking(
    supabase: SupabaseClient,
    user_id: CurrentUserId,
    strategy: str = "balanced",
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Get an explanation of current feed ranking with examples.
    Useful for understanding why certain posts appear in the feed.
    """
    try:
        # Get recent feed posts
        feed_result = supabase.rpc(
            "get_personalized_feed",
            {
                "p_user_id": user_id,
                "p_limit": limit,
                "p_offset": 0,
            }
        ).execute()
        
        if not feed_result.data:
            return {
                "message": "No posts in feed",
                "examples": [],
            }
        
        # Use ranker to score
        ranker = get_ranker(strategy)
        ranked_posts = ranker.rank_posts(feed_result.data)
        
        # Generate explanations for top posts
        examples = []
        for post in ranked_posts[:limit]:
            explanation = ranker.explain_ranking(post)
            examples.append({
                "post_id": post["id"],
                "content_preview": post.get("content", "")[:150] + "..." if post.get("content") else "",
                "final_score": post.get("final_score"),
                "explanation": explanation,
                "top_signals": sorted(
                    post.get("signals", {}).items(),
                    key=lambda x: x[1] * ranker.weights.get(x[0], 0),
                    reverse=True
                )[:3],
            })
        
        return {
            "strategy": strategy,
            "strategy_weights": ranker.weights,
            "examples": examples,
            "description": f"Feed ranked using '{strategy}' strategy, which weighs signals as shown above.",
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error explaining ranking: {str(e)}")





