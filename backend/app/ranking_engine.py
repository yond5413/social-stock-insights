"""
Ensemble Ranking Engine

Multi-signal ranking system that combines quality, community, author, market, 
recency, and diversity signals to produce optimal feed rankings.
"""

import math
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from enum import Enum


class RankingStrategy(str, Enum):
    BALANCED = "balanced"
    QUALITY_FOCUSED = "quality_focused"
    TIMELY = "timely"
    DIVERSE = "diverse"
    PERSONALIZED = "personalized"


# Signal weights for different strategies
STRATEGY_WEIGHTS = {
    RankingStrategy.BALANCED: {
        "quality": 0.25,
        "community": 0.20,
        "author": 0.20,
        "market": 0.15,
        "recency": 0.15,
        "diversity": 0.05,
    },
    RankingStrategy.QUALITY_FOCUSED: {
        "quality": 0.40,
        "community": 0.10,
        "author": 0.30,
        "market": 0.10,
        "recency": 0.05,
        "diversity": 0.05,
    },
    RankingStrategy.TIMELY: {
        "quality": 0.15,
        "community": 0.15,
        "author": 0.10,
        "market": 0.30,
        "recency": 0.25,
        "diversity": 0.05,
    },
    RankingStrategy.DIVERSE: {
        "quality": 0.20,
        "community": 0.15,
        "author": 0.15,
        "market": 0.10,
        "recency": 0.15,
        "diversity": 0.25,
    },
}


class EnsembleRanker:
    """
    Multi-signal ranking engine with configurable strategies.
    """
    
    def __init__(self, strategy: RankingStrategy = RankingStrategy.BALANCED):
        self.strategy = strategy
        self.weights = STRATEGY_WEIGHTS.get(strategy, STRATEGY_WEIGHTS[RankingStrategy.BALANCED])
    
    def rank_posts(
        self,
        posts: List[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of posts using the ensemble scoring method.
        
        Returns the posts with computed scores and explanations.
        """
        if not posts:
            return []
        
        # Compute signals for each post
        scored_posts = []
        seen_tickers: Set[str] = set()
        seen_sectors: Set[str] = set()
        
        for post in posts:
            signals = self._compute_signals(
                post,
                seen_tickers,
                seen_sectors,
                user_preferences
            )
            
            # Calculate final score
            final_score = self._aggregate_signals(signals)
            
            # Update diversity tracking
            if post.get("tickers"):
                seen_tickers.update(post["tickers"])
            if post.get("sector"):
                seen_sectors.add(post["sector"])
            
            scored_posts.append({
                **post,
                "final_score": final_score,
                "signals": signals,
            })
        
        # Sort by final score
        scored_posts.sort(key=lambda x: x["final_score"], reverse=True)
        
        return scored_posts
    
    def _compute_signals(
        self,
        post: Dict[str, Any],
        seen_tickers: Set[str],
        seen_sectors: Set[str],
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """Compute individual signal scores for a post."""
        
        # Quality signals
        quality_score = self._compute_quality_signal(post)
        
        # Community signals
        community_score = self._compute_community_signal(post)
        
        # Author signals
        author_score = self._compute_author_signal(post)
        
        # Market signals
        market_score = self._compute_market_signal(post)
        
        # Recency signals
        recency_score = self._compute_recency_signal(post)
        
        # Diversity signals
        diversity_score = self._compute_diversity_signal(
            post,
            seen_tickers,
            seen_sectors
        )
        
        return {
            "quality": quality_score,
            "community": community_score,
            "author": author_score,
            "market": market_score,
            "recency": recency_score,
            "diversity": diversity_score,
        }
    
    def _compute_quality_signal(self, post: Dict[str, Any]) -> float:
        """
        Quality signal based on LLM quality score, confidence, and content features.
        """
        base_score = post.get("quality_score", 0.5)
        confidence = post.get("confidence_level", 0.5)
        
        # Bonus for high-confidence insights
        confidence_bonus = 0.1 if confidence > 0.8 else 0
        
        # Bonus for detailed content
        content_length = len(post.get("content", ""))
        length_bonus = 0.05 if 200 < content_length < 2000 else 0
        
        # Bonus for having key points and catalysts
        detail_bonus = 0.05 if post.get("key_points") and post.get("potential_catalysts") else 0
        
        return min(1.0, base_score + confidence_bonus + length_bonus + detail_bonus)
    
    def _compute_community_signal(self, post: Dict[str, Any]) -> float:
        """
        Community signal based on engagement (likes, comments, views).
        """
        like_count = post.get("like_count", 0)
        comment_count = post.get("comment_count", 0)
        view_count = post.get("view_count", 0)
        
        # Normalize scores (diminishing returns)
        like_score = min(1.0, math.log1p(like_count) / 5)
        comment_score = min(1.0, math.log1p(comment_count) / 3)
        view_score = min(1.0, math.log1p(view_count) / 10)
        
        # Weighted combination
        return (like_score * 0.5) + (comment_score * 0.3) + (view_score * 0.2)
    
    def _compute_author_signal(self, post: Dict[str, Any]) -> float:
        """
        Author signal based on reputation, historical accuracy, and expertise.
        """
        reputation = post.get("author_reputation", 0.5)
        historical_accuracy = post.get("historical_accuracy", 0.5)
        
        # Bonus for sector expertise
        sector_expertise = post.get("sector_expertise_score", 0)
        expertise_bonus = 0.1 if sector_expertise > 0.7 else 0
        
        # Weighted combination
        base = (reputation * 0.5) + (historical_accuracy * 0.5)
        return min(1.0, base + expertise_bonus)
    
    def _compute_market_signal(self, post: Dict[str, Any]) -> float:
        """
        Market signal based on alignment score, ticker momentum, and relevance.
        """
        alignment_score = post.get("market_alignment_score", 0.5)
        relevance_score = post.get("relevance_score", 0.5)
        
        # Bonus for posts about trending tickers
        is_trending = post.get("is_trending_ticker", False)
        trending_bonus = 0.15 if is_trending else 0
        
        # Weighted combination
        base = (alignment_score * 0.5) + (relevance_score * 0.5)
        return min(1.0, base + trending_bonus)
    
    def _compute_recency_signal(self, post: Dict[str, Any]) -> float:
        """
        Recency signal with exponential time decay.
        """
        created_at_str = post.get("created_at")
        if not created_at_str:
            return 0.5
        
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return 0.5
        
        age_hours = (datetime.utcnow().replace(tzinfo=created_at.tzinfo) - created_at).total_seconds() / 3600
        
        # Configurable half-life based on strategy
        if self.strategy == RankingStrategy.TIMELY:
            half_life = 12  # 12 hours
        elif self.strategy == RankingStrategy.QUALITY_FOCUSED:
            half_life = 72  # 3 days
        else:
            half_life = 24  # 1 day
        
        # Exponential decay
        decay_score = math.exp(-age_hours / half_life)
        
        return max(0.1, decay_score)  # Minimum score of 0.1
    
    def _compute_diversity_signal(
        self,
        post: Dict[str, Any],
        seen_tickers: Set[str],
        seen_sectors: Set[str],
    ) -> float:
        """
        Diversity signal to ensure variety in feed.
        Penalizes posts about already-seen tickers and sectors.
        """
        score = 1.0
        
        # Check ticker overlap
        post_tickers = set(post.get("tickers", []))
        if post_tickers and seen_tickers:
            overlap = len(post_tickers & seen_tickers) / len(post_tickers)
            score *= (1 - overlap * 0.5)  # Reduce by up to 50%
        
        # Check sector overlap
        post_sector = post.get("sector")
        if post_sector and post_sector in seen_sectors:
            score *= 0.7  # 30% penalty for repeated sector
        
        # Check insight type diversity
        insight_type = post.get("insight_type")
        if insight_type:
            # Could track seen insight types, but keeping it simple for now
            pass
        
        return max(0.3, score)  # Minimum diversity score of 0.3
    
    def _aggregate_signals(self, signals: Dict[str, float]) -> float:
        """
        Aggregate individual signals into final score using weighted sum.
        """
        final_score = 0.0
        
        for signal_name, signal_value in signals.items():
            weight = self.weights.get(signal_name, 0)
            final_score += signal_value * weight
        
        return final_score
    
    def explain_ranking(self, post: Dict[str, Any]) -> str:
        """
        Generate a natural language explanation of why a post was ranked highly.
        """
        signals = post.get("signals", {})
        top_signals = sorted(
            [(name, value * self.weights.get(name, 0)) for name, value in signals.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        explanations = []
        
        for signal_name, weighted_value in top_signals:
            if signal_name == "quality" and weighted_value > 0.15:
                quality = post.get("quality_score", 0)
                explanations.append(f"high-quality analysis (score: {quality:.2f})")
            elif signal_name == "author" and weighted_value > 0.15:
                rep = post.get("author_reputation", 0)
                acc = post.get("historical_accuracy", 0)
                explanations.append(f"experienced author (reputation: {rep:.2f}, accuracy: {acc:.2f})")
            elif signal_name == "market" and weighted_value > 0.10:
                explanations.append("strong market alignment and relevance")
            elif signal_name == "recency" and weighted_value > 0.10:
                explanations.append("timely and recent insight")
            elif signal_name == "community" and weighted_value > 0.10:
                likes = post.get("like_count", 0)
                explanations.append(f"high community engagement ({likes} likes)")
        
        if not explanations:
            explanations.append("balanced across multiple factors")
        
        # Build explanation string
        base = "This post is recommended because it has "
        if len(explanations) == 1:
            base += explanations[0]
        elif len(explanations) == 2:
            base += explanations[0] + " and " + explanations[1]
        else:
            base += ", ".join(explanations[:-1]) + ", and " + explanations[-1]
        
        base += "."
        
        return base


def get_ranker(strategy: str = "balanced") -> EnsembleRanker:
    """
    Factory function to get a ranker with the specified strategy.
    """
    try:
        strategy_enum = RankingStrategy(strategy)
    except ValueError:
        strategy_enum = RankingStrategy.BALANCED
    
    return EnsembleRanker(strategy=strategy_enum)

