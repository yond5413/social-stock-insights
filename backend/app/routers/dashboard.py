from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta

from app.schemas import FeedItem
from app.supabase_client import get_supabase_client
from app.ranking_engine import get_ranker, RankingStrategy
from app.market_signals import get_realtime_market_data

router = APIRouter(
    tags=["dashboard"],
)

@router.get("/trending", response_model=List[Dict[str, Any]])
async def get_trending_tickers(limit: int = 10):
    """
    Get trending tickers based on mention count and market activity.
    """
    supabase = get_supabase_client()
    
    # Get trending from DB (this view/function should ideally exist, but we'll query posts for now)
    # Using a simplified approach: count mentions in recent posts
    try:
        # This is a placeholder for a more complex SQL query or materialized view
        # In a real app, we'd have a 'ticker_stats' table updated by background workers
        response = supabase.rpc("get_trending_tickers", {"p_hours": 24, "p_limit": limit}).execute()
        
        trending_data = response.data if response.data else []
        
        # Enrich with "real-time" price data
        tickers = [item['ticker'] for item in trending_data]
        market_data = await get_realtime_market_data(tickers)
        
        for item in trending_data:
            ticker = item['ticker']
            if ticker in market_data:
                item['price'] = market_data[ticker]['price']
                item['volume'] = market_data[ticker]['volume']
                item['change_percent'] = market_data[ticker].get('change_percent', 0.0)
        
        return trending_data
        
    except Exception as e:
        print(f"Error getting trending tickers: {e}")
        # Fallback to empty list or mock data
        return []

@router.get("/insights", response_model=List[FeedItem])
async def get_top_insights(
    limit: int = 20,
    strategy: str = Query("balanced", description="Ranking strategy: balanced, quality_focused, timely, diverse")
):
    """
    Get top ranked insights with transparency explanations.
    """
    supabase = get_supabase_client()
    ranker = get_ranker(strategy)
    
    try:
        # Fetch recent posts that are processed
        response = supabase.table("posts").select(
            "*, profiles(username), insights(*), market_alignments(*)"
        ).eq("llm_status", "processed").order("created_at", desc=True).limit(100).execute()
        
        raw_posts = response.data if response.data else []
        
        # Transform to format expected by ranker
        formatted_posts = []
        for p in raw_posts:
            # Extract insight data if available
            insight_data = p.get("insights", [])
            insight = insight_data[0] if isinstance(insight_data, list) and len(insight_data) > 0 else {}
            
            # Extract market alignment data if available
            market_data = p.get("market_alignments", [])
            market = market_data[0] if isinstance(market_data, list) and len(market_data) > 0 else {}
            
            # Flatten structure - explicitly build to avoid overwriting post fields
            post_data = {
                "id": p["id"],  # Preserve post ID
                "user_id": p["user_id"],
                "content": p["content"],
                "tickers": p.get("tickers", []),
                "llm_status": p.get("llm_status"),
                "created_at": p["created_at"],
                "username": p["profiles"]["username"] if p.get("profiles") else "Unknown",
                "view_count": p.get("view_count", 0),
                "like_count": p.get("like_count", 0),
                "comment_count": p.get("comment_count", 0),
                "engagement_score": p.get("engagement_score", 0.0),
                # Insight fields
                "summary": insight.get("summary"),
                "quality_score": insight.get("quality_score"),
                "insight_type": insight.get("insight_type"),
                "sector": insight.get("sector"),
                "sentiment": insight.get("sentiment"),
                # Market alignment fields
                "final_score": p.get("final_score", 0),
                "author_reputation": p.get("author_reputation", 0),
            }
            formatted_posts.append(post_data)
            
        # Rank posts
        ranked_posts = ranker.rank_posts(formatted_posts)
        
        # Take top N
        top_posts = ranked_posts[:limit]
        
        # Add explanation and convert to FeedItem
        result = []
        for p in top_posts:
            explanation = ranker.explain_ranking(p)
            
            # Map to FeedItem schema
            item = FeedItem(
                id=p["id"],
                user_id=p["user_id"],
                content=p["content"],
                tickers=p["tickers"] or [],
                created_at=p["created_at"],
                llm_status=p["llm_status"],
                username=p.get("username"),
                summary=p.get("summary"),
                quality_score=p.get("quality_score"),
                final_score=p.get("final_score", 0),
                view_count=p.get("view_count", 0),
                like_count=p.get("like_count", 0),
                comment_count=p.get("comment_count", 0),
                insight_type=p.get("insight_type"),
                sector=p.get("sector"),
                author_reputation=p.get("author_reputation", 0),
                ranking_explanation=explanation
            )
            result.append(item)
            
        return result
        
    except Exception as e:
        print(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=Dict[str, Any])
async def get_system_stats():
    """
    Get aggregated system statistics from real database data with change percentages.
    """
    supabase = get_supabase_client()
    
    try:
        # Get active users count (distinct users who have created posts)
        try:
            # Try RPC first, fallback to direct query
            users_result = supabase.rpc("count_active_users").execute()
            active_users = users_result.data if users_result.data else 0
        except:
            # Direct query: count distinct users who have created posts
            posts_with_users = supabase.table("posts").select("user_id").execute()
            if posts_with_users.data:
                unique_users = len(set(p["user_id"] for p in posts_with_users.data if p.get("user_id")))
                active_users = unique_users
            else:
                active_users = 0
        
        # Get active users from 30 days ago for comparison
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        try:
            old_posts = supabase.table("posts").select("user_id").lt("created_at", thirty_days_ago).execute()
            if old_posts.data:
                old_unique_users = len(set(p["user_id"] for p in old_posts.data if p.get("user_id")))
            else:
                old_unique_users = 0
        except:
            old_unique_users = 0
        
        # Calculate active users change percentage
        if old_unique_users > 0:
            active_users_change = ((active_users - old_unique_users) / old_unique_users) * 100
        else:
            active_users_change = 0.0 if active_users == 0 else 100.0
        
        # Get total insights generated (processed posts count)
        insights_result = supabase.table("posts").select("id", count="exact").eq("llm_status", "processed").execute()
        insights_generated = insights_result.count if insights_result.count else 0
        
        # Get insights from 1 hour ago for comparison
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        try:
            old_insights_result = supabase.table("posts").select("id", count="exact").eq("llm_status", "processed").lt("created_at", one_hour_ago).execute()
            old_insights = old_insights_result.count if old_insights_result.count else 0
        except:
            old_insights = 0
        
        # Calculate insights change (absolute difference, not percentage)
        insights_change = insights_generated - old_insights
        
        # Get average historical_accuracy from reputation table (not quality_score)
        accuracy_result = supabase.table("reputation").select("historical_accuracy").execute()
        if accuracy_result.data and len(accuracy_result.data) > 0:
            accuracies = [float(a["historical_accuracy"]) for a in accuracy_result.data if a.get("historical_accuracy") is not None]
            avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0
        else:
            avg_accuracy = 0.0
        
        # Calculate accuracy change by comparing recent market alignments vs older ones
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        try:
            # Get average accuracy from alignments created in last 7 days
            recent_alignments = supabase.table("market_alignments").select("alignment_score").gte("created_at", seven_days_ago).execute()
            if recent_alignments.data and len(recent_alignments.data) > 0:
                recent_scores = [float(a["alignment_score"]) for a in recent_alignments.data if a.get("alignment_score") is not None]
                recent_avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0.0
            else:
                recent_avg = 0.0
            
            # Get average accuracy from alignments older than 7 days
            old_alignments = supabase.table("market_alignments").select("alignment_score").lt("created_at", seven_days_ago).execute()
            if old_alignments.data and len(old_alignments.data) > 0:
                old_scores = [float(a["alignment_score"]) for a in old_alignments.data if a.get("alignment_score") is not None]
                old_avg = sum(old_scores) / len(old_scores) if old_scores else 0.0
            else:
                old_avg = 0.0
            
            # Calculate change percentage
            if old_avg > 0:
                accuracy_change = ((recent_avg - old_avg) / old_avg) * 100
            else:
                accuracy_change = 0.0 if recent_avg == 0 else 100.0
        except Exception as e:
            print(f"Error calculating accuracy change: {e}")
            accuracy_change = 0.0
        
        # Get top sector from processed posts
        sector_result = supabase.table("insights").select("sector").execute()
        if sector_result.data:
            sector_counts = {}
            for item in sector_result.data:
                sector = item.get("sector")
                if sector:
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
            top_sector = max(sector_counts, key=sector_counts.get) if sector_counts else "Technology"
        else:
            top_sector = "Technology"
        
        return {
            "active_users": active_users,
            "active_users_change": round(active_users_change, 1),
            "insights_generated": insights_generated,
            "insights_change": insights_change,
            "avg_accuracy": avg_accuracy,
            "accuracy_change": round(accuracy_change, 1),
            "top_sector": top_sector
        }
    except Exception as e:
        print(f"Error getting system stats: {e}")
        # Fallback to basic counts if RPC function doesn't exist
        try:
            posts_with_users = supabase.table("posts").select("user_id").execute()
            if posts_with_users.data:
                unique_users = len(set(p["user_id"] for p in posts_with_users.data if p.get("user_id")))
            else:
                unique_users = 0
            
            posts_count = supabase.table("posts").select("id", count="exact").execute().count or 0
            return {
                "active_users": unique_users,
                "active_users_change": 0.0,
                "insights_generated": posts_count,
                "insights_change": 0,
                "avg_accuracy": 0.0,
                "accuracy_change": 0.0,
                "top_sector": "Technology"
            }
        except:
            return {
                "active_users": 0,
                "active_users_change": 0.0,
                "insights_generated": 0,
                "insights_change": 0,
                "avg_accuracy": 0.0,
                "accuracy_change": 0.0,
                "top_sector": "Technology"
            }
