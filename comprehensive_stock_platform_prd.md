# Stock Insights Social Platform - Comprehensive PRD

## Project Overview

A social-driven platform for sharing **stock analyses, trading ideas, and market insights**. Users can post content, react, and discover high-quality signals. An **LLM-driven backend** will ingest posts, generate semantic tags, summarize insights, rank posts for personalization, and provide transparency explanations.

This PRD is informed by a detailed discussion covering **MVP architecture with Cursor/Neon Postgres**, **Cohere embeddings**, batch LLM processing, WebSocket-based real-time feeds, vector DB considerations, and a comprehensive database schema.

---

## Goals

1. **Social Engagement**
   - Users can post insights, comment, react, and follow tickers/sectors.
2. **Insight Intelligence**
   - LLM ingests posts + market data to:
     - Generate semantic tags (sector, catalyst, risk profile)
     - Score insight quality
     - Summarize content
     - Provide natural-language explanations
3. **Personalized Feeds**
   - Rank posts using:
     - LLM scoring (quality, risk, type)
     - User reputation (overall, sector/ticker expertise)
     - Community sentiment (engagement, thumbs up/down)
     - Market context (price movement, volume spikes, earnings surprises, event probability from Kalshi/Polymarket)
4. **Transparency & Audit**
   - LLM reasoning logs for each ranked post, storing input, output, model used, latency, and explanation
5. **Reusable Backend**
   - Export insight pipeline as a **FastAPI backend or Python package** for batch analytics or real-time feeds

---

## Core Features

### 1. Frontend
- **Tech:** Next.js / React, Vercel
- Features:
  - Personalized feed & trending tickers
  - Post composer & reactions
  - User profiles
  - Real-time updates using **WebSockets** or **Server-Sent Events (SSE)**
  - Realtime hooks for feed updates triggered by ranking engine

### 2. Backend / API
- **Tech:** FastAPI
- Responsibilities:
  - Auth & session management via **Clerk**
  - Post ingestion & validation
  - Normalization of ticker symbols and post content
  - Queueing of LLM tasks
  - Feed ranking calculation
  - User reputation calculation
  - Background task orchestration using **ARQ / Redis**

### 3. Insight Processing Pipeline
- Functions:
  - **Embeddings generation** using **Cohere `embed-english-v3.0`**
    - Supports batch processing (16–32 posts per call)
    - Optional multiple embeddings per post: content, summary
    - Stored in Postgres `pgvector`
  - **Semantic tagging**: sector, catalyst, risk profile
  - **Insight classification**: fundamental, technical, macro, earnings, risk warning
  - **Quality scoring**: LLM + historical accuracy, ensemble of post features
  - **Summaries & explanations**
- **Batching** reduces LLM API calls and latency

### 4. Feed Ranking Engine
- Personalized ranking based on:
  - LLM-assigned post quality scores
  - User reputation scores
  - Community engagement / sentiment metrics
  - Market context (realtime price, volume, earnings, event probability)
  - Diversity controls to avoid feed redundancy
- Precomputed scores stored in `feed_ranking` table for fast fetch
- Runs asynchronously via queue to avoid blocking ingestion

### 5. User Reputation Engine
- Tracks:
  - Overall score (0-1 normalized)
  - Sector/ticker expertise (`JSONB` mapping)
  - Historical accuracy (% correct insights)
  - Community impact (engagement, reactions)
- Updated asynchronously after post evaluation

### 6. Data Layer
- **Postgres (Neon)** for structured storage, **pgvector** for embeddings
- Tables include:
  - `users`, `posts`, `post_embeddings`, `insights`, `reputation`, `market_snapshots`, `post_engagement`, `llm_audit_logs`
- Optional tables:
  - `feed_ranking` (precomputed personalized scores)
  - `related_insights` (post similarity clusters)
  - `earnings_events` (future earnings and surprises)
  - `tags` (user- or LLM-generated)

### 7. Market Data Integration
- Sources:
  - **Kalshi**: event prices, volatility expectations
  - **Polymarket**: crowd-sourced event probability feed
  - **yfinance**: real-time quotes, volume, OHLC, earnings calendar
- Used by LLM for insight context and feed ranking
- Async enrichment via queue

### 8. LLM Layer
- **OpenRouter** or similar
- Tasks:
  - Embeddings generation
  - Insight classification
  - Summarization & natural-language explanation
  - Quality and risk scoring
- Batch processing for multiple posts
- Audit logs store input, output, model, latency, and reasoning

### 9. Queue / Async Processing
- **ARQ / Redis** for:
  - LLM task execution
  - Market data ingestion and enrichment
  - Feed ranking recalculation
- Decouples ingestion from downstream processing to improve responsiveness

### 10. Real-Time Feed Updates
- Clients subscribe to WebSocket channels per ticker/user
- Feed updates pushed when:
  - New posts processed
  - Rankings updated due to LLM or market changes
- Reduces frontend polling and improves UX

---

## Database Schema Highlights

**Tables and Key Columns:**

1. `users`: id, username, email, profile_image, premium flag, timestamps
2. `posts`: id, user_id, content, ticker array, LLM status, timestamps
3. `post_embeddings`: post_id, embedding vector(1024), type (content/summary), batch_id, created_at
4. `insights`: id, post_id, insight_type, sector, catalyst, risk_profile, quality_score, summary, explanation, created_at
5. `reputation`: user_id, overall_score, sector_expertise JSONB, historical_accuracy, community_impact, updated_at
6. `market_snapshots`: id, ticker, price, volume, open, high, low, close, timestamp, source
7. `post_engagement`: post_id, user_id, type (like/comment), comment, created_at
8. `llm_audit_logs`: id, post_id, task_type, input JSONB, output JSONB, model, latency_ms, created_at
9. Optional: `feed_ranking`, `related_insights`, `earnings_events`, `tags`

**Vector Search Index:**
```sql
CREATE INDEX idx_post_embedding 
ON post_embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
```

**Additional Technical Considerations:**
- Multiple embeddings per post (content vs summary)
- Related posts / clustering for personalization
- Market signals linked to posts/insights
- Engagement metrics captured for feed ranking
- Audit logs enable full traceability of LLM reasoning

---

## MVP Considerations
- Cohere `embed-english-v3.0` for semantic embeddings
- Postgres + pgvector for embeddings storage
- Batch LLM calls to minimize API latency and cost
- Async queue (ARQ/Redis) for task decoupling
- Focus on feed, trending tickers, user reputation, LLM summaries & insights
- Premium/paywall ignored for initial version

---

## Architecture Flow (Simplified)

```
[Frontend (Next.js)]
      │
      ▼
[Ingestion Service] → [Queue (ARQ/Redis)] → [LLM Processing Pipeline] → [Postgres + Vector Embeddings]
      │                                                     │
      │                                                     ▼
      └--------------------------------> [Ranking Engine] ───> [Frontend via WebSocket]
```

- Async processing ensures low-latency ingestion
- Embeddings, insights, and ranking scores stored in DB
- Market data feeds enrich LLM reasoning asynchronously

---

## Future Enhancements
- Large-scale vector DB (Pinecone / Milvus) for high-volume embeddings
- Reinforcement learning from user engagement
- Historical post & LLM versioning for auditing
- User feedback loops for improved ranking
- Analytics dashboards (premium tier)
- Multi-model ensemble for scoring insights

---

## Additional Context from Discussion
- Postgres (Neon) selected for MVP vector storage
- Cohere embeddings used for semantic similarity & insight ranking
- Async batch LLM processing (16–32 posts per batch) for efficiency
- WebSocket real-time feed updates integrated with ranking engine
- Feed ranking decoupled from ingestion to improve UX
- Database schema includes posts, embeddings, insights, reputation, market snapshots, post engagement, and audit logs
- Design allows future migration to specialized vector DBs and multi-model LLM ensembles

