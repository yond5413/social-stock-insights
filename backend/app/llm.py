import json
import time
import logging
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from pydantic import BaseModel, Field, validator

from .config import get_settings


# Set up logging
logger = logging.getLogger(__name__)


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


class Sentiment(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


# Pydantic models for LLM response validation
class ComprehensiveAnalysisResponse(BaseModel):
    """Schema for comprehensive post analysis LLM response."""
    insight_type: str = Field(default="sentiment_pulse")
    sector: Optional[str] = Field(default="General")
    sub_sector: Optional[str] = Field(default=None)
    catalyst: str = Field(default="other")
    risk_profile: str = Field(default="moderate")
    time_horizon: str = Field(default="short_term")
    quality_score: float = Field(default=0.5, ge=0, le=1)
    confidence_level: float = Field(default=0.5, ge=0, le=1)
    relevance_score: float = Field(default=0.5, ge=0, le=1)
    summary: str = Field(default="No summary available")
    explanation: Optional[str] = Field(default=None)
    sentiment: str = Field(default="neutral")
    key_points: List[str] = Field(default_factory=list)
    potential_catalysts: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    moderation_flags: List[str] = Field(default_factory=list)

    @validator('quality_score', 'confidence_level', 'relevance_score', pre=True)
    def clamp_scores(cls, v):
        if v is None:
            return 0.5
        try:
            v = float(v)
            return max(0.0, min(1.0, v))
        except (ValueError, TypeError):
            return 0.5

    @validator('sentiment', pre=True)
    def normalize_sentiment(cls, v):
        if v is None:
            return "neutral"
        v_lower = str(v).lower()
        if v_lower in ["bullish", "positive", "up", "buy"]:
            return "bullish"
        elif v_lower in ["bearish", "negative", "down", "sell"]:
            return "bearish"
        return "neutral"


class MarketAlignmentResponse(BaseModel):
    """Schema for market alignment scoring LLM response."""
    alignment_score: float = Field(default=0.5, ge=0, le=1)
    predicted_direction: str = Field(default="neutral")
    actual_direction: str = Field(default="neutral")
    timing_accuracy: str = Field(default="unknown")
    explanation: str = Field(default="No explanation available")

    @validator('alignment_score', pre=True)
    def clamp_score(cls, v):
        if v is None:
            return 0.5
        try:
            v = float(v)
            return max(0.0, min(1.0, v))
        except (ValueError, TypeError):
            return 0.5


class ExplanationResponse(BaseModel):
    """Schema for ranking explanation LLM response."""
    explanation: str = Field(default="This post was recommended based on its relevance.")
    key_factors: List[str] = Field(default_factory=list)
    confidence: str = Field(default="medium")


# Latency budget for LLM calls (milliseconds)
LATENCY_BUDGETS = {
    "analyze_post_comprehensive": 30000,  # 30 seconds for Grok
    "detect_community_trends": 45000,  # 45 seconds
    "score_market_alignment": 20000,  # 20 seconds
    "generate_explanation": 15000,  # 15 seconds
}


def validate_llm_response(parsed: Dict[str, Any], task_type: str) -> Dict[str, Any]:
    """
    Validate and normalize LLM response using Pydantic models.
    Returns validated dict with fallback defaults for missing/invalid fields.
    """
    try:
        if task_type == "analyze_post_comprehensive":
            validated = ComprehensiveAnalysisResponse(**parsed)
            return validated.dict()
        elif task_type == "score_market_alignment":
            validated = MarketAlignmentResponse(**parsed)
            return validated.dict()
        elif task_type == "generate_explanation":
            validated = ExplanationResponse(**parsed)
            return validated.dict()
        else:
            # For unknown task types, return as-is with basic defaults
            return parsed
    except Exception as e:
        logger.warning(f"LLM response validation failed for {task_type}: {e}")
        # Return default response based on task type
        if task_type == "analyze_post_comprehensive":
            return ComprehensiveAnalysisResponse().dict()
        elif task_type == "score_market_alignment":
            return MarketAlignmentResponse().dict()
        elif task_type == "generate_explanation":
            return ExplanationResponse().dict()
        return parsed


async def call_openrouter_chat(
    task_type: str,
    post_content: str,
    tickers: list[str],
    additional_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call OpenRouter with comprehensive prompting for stock market analysis.
    Supports multiple task types with specialized prompts.
    Includes schema validation and latency monitoring.
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
    
    # Apply latency budget timeout (convert ms to seconds)
    latency_budget_ms = LATENCY_BUDGETS.get(task_type, 60000)
    timeout = latency_budget_ms / 1000.0
    
    start = time.perf_counter()
    latency_exceeded = False
    validation_failed = False
    
    try:
        async with httpx.AsyncClient(base_url=settings.openrouter_base_url, timeout=timeout) as client:
            resp = await client.post("/chat/completions", headers=headers, json=payload)
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        # Check if latency exceeded budget (even if successful)
        if latency_ms > latency_budget_ms:
            latency_exceeded = True
            logger.warning(
                f"LLM latency exceeded budget: {latency_ms}ms > {latency_budget_ms}ms for {task_type}"
            )

        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM JSON response for {task_type}")
            parsed = {"raw_response": content}
            validation_failed = True

        # Validate and normalize the response using Pydantic
        validated_parsed = validate_llm_response(parsed, task_type)

        return {
            "parsed": validated_parsed,
            "raw": data,
            "latency_ms": latency_ms,
            "model": settings.openrouter_model_tagging,
            "latency_exceeded": latency_exceeded,
            "validation_failed": validation_failed,
        }
        
    except httpx.TimeoutException:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"LLM timeout after {latency_ms}ms for {task_type}")
        
        # Return validated default response on timeout
        default_response = validate_llm_response({}, task_type)
        default_response["error"] = "timeout"
        default_response["summary"] = post_content[:200] if "summary" in default_response else post_content[:200]
        
        return {
            "parsed": default_response,
            "raw": {},
            "latency_ms": latency_ms,
            "model": settings.openrouter_model_tagging,
            "latency_exceeded": True,
            "validation_failed": False,
            "error": "timeout",
        }
        
    except httpx.HTTPStatusError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"LLM HTTP error {e.response.status_code} for {task_type}: {e}")
        
        default_response = validate_llm_response({}, task_type)
        default_response["error"] = f"http_error_{e.response.status_code}"
        
        return {
            "parsed": default_response,
            "raw": {},
            "latency_ms": latency_ms,
            "model": settings.openrouter_model_tagging,
            "latency_exceeded": False,
            "validation_failed": False,
            "error": f"http_error_{e.response.status_code}",
        }
        
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"Unexpected LLM error for {task_type}: {e}")
        
        default_response = validate_llm_response({}, task_type)
        default_response["error"] = str(e)
        
        return {
            "parsed": default_response,
            "raw": {},
            "latency_ms": latency_ms,
            "model": settings.openrouter_model_tagging,
            "latency_exceeded": False,
            "validation_failed": False,
            "error": str(e),
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


class EmbeddingError(Exception):
    """Custom exception for embedding failures."""
    pass


async def call_cohere_embedding(text: str) -> Optional[List[float]]:
    """
    Call Cohere embeddings API using embed-english-v3.0 model.
    Returns a 1024-dimensional embedding vector, or None on failure.
    
    Handles:
    - Network failures
    - API quota exhaustion
    - Invalid responses
    """
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.cohere_api_key}",
        "Content-Type": "application/json",
    }

    # Truncate very long texts to avoid API limits
    max_text_length = 8000  # Cohere's limit is ~8192 tokens
    truncated_text = text[:max_text_length] if len(text) > max_text_length else text

    payload = {
        "model": "embed-english-v3.0",
        "texts": [truncated_text],
        "input_type": "search_document",
    }

    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(base_url="https://api.cohere.ai", timeout=30.0) as client:
            resp = await client.post("/v1/embed", headers=headers, json=payload)
        
        latency_ms = int((time.perf_counter() - start) * 1000)
        
        # Handle rate limiting
        if resp.status_code == 429:
            logger.warning(f"Cohere API rate limited (latency: {latency_ms}ms)")
            return None
        
        # Handle quota exhaustion
        if resp.status_code == 402:
            logger.error("Cohere API quota exhausted")
            return None
        
        resp.raise_for_status()
        data = resp.json()
        
        if "embeddings" not in data or not data["embeddings"]:
            logger.error(f"Invalid Cohere response: missing embeddings (latency: {latency_ms}ms)")
            return None
        
        embedding = data["embeddings"][0]
        
        # Validate embedding dimension
        if len(embedding) != 1024:
            logger.warning(f"Unexpected embedding dimension: {len(embedding)} (expected 1024)")
        
        logger.debug(f"Cohere embedding successful (latency: {latency_ms}ms)")
        return embedding
        
    except httpx.TimeoutException:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"Cohere API timeout after {latency_ms}ms")
        return None
        
    except httpx.HTTPStatusError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"Cohere API HTTP error {e.response.status_code} after {latency_ms}ms: {e}")
        return None
        
    except httpx.RequestError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"Cohere API network error after {latency_ms}ms: {e}")
        return None
        
    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        logger.error(f"Unexpected Cohere API error after {latency_ms}ms: {e}")
        return None


async def call_cohere_embedding_for_search(text: str) -> Optional[List[float]]:
    """
    Call Cohere embeddings API for search queries.
    Uses 'search_query' input type for better semantic search results.
    """
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.cohere_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "embed-english-v3.0",
        "texts": [text[:8000]],
        "input_type": "search_query",
    }

    try:
        async with httpx.AsyncClient(base_url="https://api.cohere.ai", timeout=30.0) as client:
            resp = await client.post("/v1/embed", headers=headers, json=payload)
        
        if resp.status_code in [429, 402]:
            logger.warning(f"Cohere API unavailable: {resp.status_code}")
            return None
            
        resp.raise_for_status()
        data = resp.json()
        
        if "embeddings" not in data or not data["embeddings"]:
            return None
            
        return data["embeddings"][0]
        
    except Exception as e:
        logger.error(f"Cohere search embedding error: {e}")
        return None



