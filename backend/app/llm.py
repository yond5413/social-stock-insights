import json
import time
from typing import Any, Dict

import httpx

from .config import get_settings


async def call_openrouter_chat(
    task_type: str,
    post_content: str,
    tickers: list[str],
) -> Dict[str, Any]:
    """
    Call OpenRouter to get tagging, sentiment, summary, quality score and explanation.
    Returns a parsed JSON dict with expected keys.
    """
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    system_prompt = (
        "You are an assistant that analyzes stock market posts.\n"
        "Return a STRICT JSON object with keys:\n"
        "insight_type, sector, catalyst, risk_profile, quality_score (0-1 float), "
        "summary, explanation, sentiment.\n"
        "Do not include any extra text outside the JSON."
    )
    user_prompt = (
        f"Task: {task_type} for a stock insight post.\n"
        f"Tickers mentioned: {', '.join(tickers) if tickers else 'none'}\n"
        f"Post content:\n{post_content}"
    )

    payload = {
        "model": settings.openrouter_model_tagging,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    start = time.perf_counter()
    async with httpx.AsyncClient(base_url=settings.openrouter_base_url, timeout=60.0) as client:
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



