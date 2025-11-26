import json
import time
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx

from .config import get_settings


class InsightType(str, Enum):
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    TECHNICAL_ANALYSIS = "technical_analysis"
    MACRO_COMMENTARY = "macro_commentary"
    EARNINGS_FORECAST = "earnings_forecast"
    RISK_WARNING = "risk_warning"
    SENTIMENT_PULSE = "sentiment_pulse"
    CATALYST_ALERT = "catalyst_alert"


class CatalystType(str, Enum):
    EARNINGS = "earnings"
    MERGER = "merger"
    REGULATORY = "regulatory"
    PRODUCT_LAUNCH = "product_launch"
    EXECUTIVE_CHANGE = "executive_change"
    MARKET_SHIFT = "market_shift"
    PARTNERSHIP = "partnership"
    OTHER = "other"


class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"


class TimeHorizon(str, Enum):
    INTRADAY = "intraday"
    SHORT_TERM = "short_term"  # days to weeks
    MEDIUM_TERM = "medium_term"  # weeks to months
    LONG_TERM = "long_term"  # months to years


# Latency budget for LLM calls (milliseconds)
LATENCY_BUDGETS = {
    "analyze_post_comprehensive": 10000,  # 10 seconds
    "detect_community_trends": 15000,  # 15 seconds
    "score_market_alignment": 8000,  # 8 seconds
    "generate_explanation": 5000,  # 5 seconds
}


async def call_openrouter_chat(
    task_type: str,
    post_content: str,
    tickers: list[str],
    additional_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call OpenRouter with comprehensive prompting for stock market analysis.
    Supports multiple task types with specialized prompts.
    """
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    # Build system and user prompts based on task type
    if task_type == "analyze_post_comprehensive":
        system_prompt = _get_comprehensive_analysis_prompt()
    elif task_type == "detect_community_trends":
        system_prompt = _get_trend_detection_prompt()
    elif task_type == "score_market_alignment":
        system_prompt = _get_market_alignment_prompt()
    elif task_type == "generate_explanation":
        system_prompt = _get_explanation_prompt()
    else:
        # Fallback to basic prompt
        system_prompt = (
            "You are an assistant that analyzes stock market posts.\n"
            "Return a STRICT JSON object with relevant analysis fields.\n"
            "Do not include any extra text outside the JSON."
        )
    
    user_prompt = (
        f"Task: {task_type}\n"
        f"Tickers mentioned: {', '.join(tickers) if tickers else 'none'}\n"
        f"Post content:\n{post_content}"
    )
    
    if additional_context:
        user_prompt += f"\n\nAdditional context:\n{json.dumps(additional_context, indent=2)}"

    payload = {
        "model": settings.openrouter_model_tagging,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }
    
    # Apply latency budget timeout
    timeout = LATENCY_BUDGETS.get(task_type, 60.0) / 1000.0
    
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(base_url=settings.openrouter_base_url, timeout=timeout) as client:
            resp = await client.post("/chat/completions", headers=headers, json=payload)
        latency_ms = int((time.perf_counter() - start) * 1000)

        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: wrap raw content
            parsed = {"raw_response": content}

        return {
            "parsed": parsed,
            "raw": data,
            "latency_ms": latency_ms,
            "model": settings.openrouter_model_tagging,
        }
    except httpx.TimeoutException:
        # Fallback response on timeout
        return {
            "parsed": {
                "error": "timeout",
                "quality_score": 0.5,
                "summary": post_content[:200],
            },
            "raw": {},
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "model": settings.openrouter_model_tagging,
        }


def _get_comprehensive_analysis_prompt() -> str:
    """Get the system prompt for comprehensive post analysis."""
    return f"""You are an expert financial analyst specializing in stock market insights.

Analyze the given stock market post and return a JSON object with the following structure:

{{
  "insight_type": "<one of: {', '.join([t.value for t in InsightType])}>,
  "sector": "<primary sector, e.g., Technology, Healthcare, Finance>",
  "sub_sector": "<more specific industry, e.g., Cloud Computing, Biotechnology>",
  "catalyst": "<one of: {', '.join([c.value for c in CatalystType])}>,
  "risk_profile": "<one of: {', '.join([r.value for r in RiskProfile])}>,
  "time_horizon": "<one of: {', '.join([t.value for t in TimeHorizon])}>,
  "quality_score": <float 0-1 indicating post quality and informativeness>,
  "confidence_level": <float 0-1 indicating your confidence in this analysis>,
  "relevance_score": <float 0-1 indicating how timely and relevant this post is>,
  "summary": "<concise 1-2 sentence summary of key insight>",
  "explanation": "<brief explanation of why this post matters>",
  "sentiment": "<bullish, bearish, or neutral>",
  "key_points": ["<point 1>", "<point 2>", ...],
  "potential_catalysts": ["<catalyst 1>", "<catalyst 2>", ...],
  "risk_factors": ["<risk 1>", "<risk 2>", ...]
}}

Quality score should consider:
- Specificity and actionability of information
- Presence of data, numbers, or concrete evidence
- Clarity of reasoning and logic
- Depth of analysis

Relevance score should consider:
- Timeliness (is this about current events?)
- Importance of the tickers/sectors involved
- Uniqueness of insight (not just common knowledge)"""


def _get_trend_detection_prompt() -> str:
    """Get the system prompt for trend detection."""
    return """You are a trend analyst identifying emerging patterns in stock market discussions.

Analyze the given posts and identify common themes, sentiment shifts, and emerging trends.

Return a JSON object:
{{
  "trends": [
    {{
      "trend_type": "<market, community, sector, ticker>",
      "description": "<brief description of the trend>",
      "confidence": <float 0-1>,
      "supporting_tickers": ["TICKER1", "TICKER2", ...],
      "sentiment_direction": "<bullish, bearish, mixed>",
      "key_themes": ["<theme 1>", "<theme 2>", ...]
    }}
  ],
  "overall_sentiment": "<market sentiment across all posts>",
  "emerging_sectors": ["<sector 1>", "<sector 2>", ...]
}}"""


def _get_market_alignment_prompt() -> str:
    """Get the system prompt for market alignment scoring."""
    return """You are a market analyst comparing post sentiment with actual market movements.

Given a post and market data, assess how well the post's prediction/sentiment aligns with reality.

Return a JSON object:
{{
  "alignment_score": <float 0-1, where 1 = perfect alignment>,
  "predicted_direction": "<up, down, neutral>",
  "actual_direction": "<up, down, neutral>",
  "timing_accuracy": "<early, on_time, late, wrong>",
  "explanation": "<brief explanation of alignment or misalignment>"
}}"""


def _get_explanation_prompt() -> str:
    """Get the system prompt for generating ranking explanations."""
    return """You are a helpful assistant explaining why certain posts are recommended to users.

Generate a natural, conversational explanation of why a post is ranked highly.

Return a JSON object:
{{
  "explanation": "<2-3 sentence natural language explanation>",
  "key_factors": ["<factor 1>", "<factor 2>", "<factor 3>"],
  "confidence": "<high, medium, low>"
}}

Example: "This post is recommended because it provides high-quality fundamental analysis (score: 0.89) on NVDA from an author with 85% historical accuracy in the technology sector. The post aligns well with recent earnings data and market momentum."
"""


async def call_cohere_embedding(text: str) -> list[float]:
    """
    Call Cohere embeddings API using embed-english-v3.0 model.
    Returns a 1024-dimensional embedding vector.
    """
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.cohere_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "embed-english-v3.0",
        "texts": [text],
        "input_type": "search_document",  # For storing in database
    }

    async with httpx.AsyncClient(base_url="https://api.cohere.ai", timeout=60.0) as client:
        resp = await client.post("/v1/embed", headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"][0]



