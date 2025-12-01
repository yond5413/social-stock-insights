from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from ..supabase_client import SupabaseClient

router = APIRouter()


@router.get("/db-stats")
async def get_db_stats(supabase: SupabaseClient) -> Dict[str, Any]:
    """
    Get database statistics including post counts, processing stats, and user metrics.
    Uses the platform_stats view for efficient querying.
    """
    try:
        result = supabase.table("platform_stats").select("*").execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to fetch platform stats")
        
        stats = result.data[0]
        
        # Calculate processing rate
        total_posts = stats.get("total_posts", 0)
        processed = stats.get("processed_posts", 0)
        processing_rate = (processed / total_posts * 100) if total_posts > 0 else 0
        
        return {
            "posts": {
                "total": stats.get("total_posts", 0),
                "pending": stats.get("pending_posts", 0),
                "processed": stats.get("processed_posts", 0),
                "failed": stats.get("failed_posts", 0),
                "processing_rate_percent": round(processing_rate, 2),
            },
            "users": {
                "total": stats.get("total_users", 0),
            },
            "insights": {
                "total": stats.get("total_insights", 0),
                "avg_quality_score": float(stats.get("avg_quality_score", 0)) if stats.get("avg_quality_score") else None,
            },
            "llm": {
                "avg_latency_24h_ms": float(stats.get("avg_llm_latency_24h", 0)) if stats.get("avg_llm_latency_24h") else None,
                "calls_last_hour": stats.get("llm_calls_last_hour", 0),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@router.get("/health")
async def health_check(supabase: SupabaseClient) -> Dict[str, Any]:
    """
    Comprehensive health check including database connectivity and system status.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check database connectivity
    try:
        result = supabase.table("posts").select("id").limit(1).execute()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
    
    # Check for stuck pending posts (older than 10 minutes)
    try:
        result = supabase.rpc("check_stuck_posts", {}).execute()
        stuck_count = len(result.data) if result.data else 0
        
        if stuck_count > 10:
            health_status["status"] = "degraded"
            health_status["checks"]["worker"] = {
                "status": "degraded",
                "message": f"{stuck_count} posts stuck in pending status",
                "stuck_posts": stuck_count
            }
        else:
            health_status["checks"]["worker"] = {
                "status": "healthy",
                "message": "Worker processing normally",
                "stuck_posts": stuck_count
            }
    except Exception as e:
        # If function doesn't exist yet, skip this check
        health_status["checks"]["worker"] = {
            "status": "unknown",
            "message": "Worker status check unavailable"
        }
    
    return health_status


@router.get("/worker-status")
async def get_worker_status(supabase: SupabaseClient) -> Dict[str, Any]:
    """
    Get worker processing queue status and statistics.
    """
    try:
        # Get pending posts with age
        pending_result = supabase.rpc("get_pending_posts_stats", {}).execute()
        
        # Get recent processing stats
        recent_processed = supabase.table("posts").select("id, created_at, updated_at").eq(
            "llm_status", "processed"
        ).order("updated_at", desc=True).limit(10).execute()
        
        # Calculate average processing time for recent posts
        processing_times = []
        if recent_processed.data:
            for post in recent_processed.data:
                if post.get("created_at") and post.get("updated_at"):
                    created = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00"))
                    updated = datetime.fromisoformat(post["updated_at"].replace("Z", "+00:00"))
                    processing_time = (updated - created).total_seconds()
                    processing_times.append(processing_time)
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else None
        
        return {
            "queue": {
                "pending_count": len(pending_result.data) if pending_result.data else 0,
                "oldest_pending": pending_result.data[0] if pending_result.data else None,
            },
            "performance": {
                "avg_processing_time_seconds": round(avg_processing_time, 2) if avg_processing_time else None,
                "recent_processed_count": len(recent_processed.data) if recent_processed.data else 0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching worker status: {str(e)}")


@router.get("/recent-errors")
async def get_recent_errors(
    supabase: SupabaseClient,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Get recent failed posts with error messages for debugging.
    """
    try:
        result = supabase.table("posts").select(
            "id, content, tickers, error_message, retry_count, created_at, updated_at"
        ).eq("llm_status", "failed").order("updated_at", desc=True).limit(limit).execute()
        
        return result.data if result.data else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching errors: {str(e)}")




