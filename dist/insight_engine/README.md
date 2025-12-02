
# Social Stocks Insight Engine

This package encapsulates the LLM-driven insight processing pipeline.

## Usage

```python
from social_stocks_engine.ranking_engine import get_ranker
from social_stocks_engine.llm import call_openrouter_chat

# Rank posts
ranker = get_ranker("balanced")
ranked_posts = ranker.rank_posts(posts)
```
