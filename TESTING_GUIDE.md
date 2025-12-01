# Testing Guide for Social Stocks Insights Platform

## Quick Start Testing

### 1. Verify Database Setup

Check that all migrations have been applied:

```bash
# Using Supabase MCP (built-in)
# The platform automatically verifies tables on startup
```

Expected tables:
- `posts`, `profiles`, `insights`, `post_embeddings`
- `trends`, `post_trends`, `market_alignments`
- `user_predictions`, `reputation`, `post_engagement`
- `llm_audit_logs`, `market_snapshots`

### 2. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Test health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-26T...",
  "checks": {
    "database": {"status": "healthy", "message": "Database connection successful"},
    "worker": {"status": "healthy", "message": "Worker processing normally", "stuck_posts": 0}
  }
}
```

### 3. Start the Worker (Optional for Full Testing)

```bash
cd backend
arq app.worker.WorkerSettings
```

The worker will:
- Process pending posts every 5 minutes
- Retry failed posts every hour
- Recompute reputation every hour
- Score market alignments daily at 2 AM
- Rerank by market events every 15 minutes

### 4. Start the Frontend

```bash
cd frontend
npm run dev
```

Visit: `http://localhost:3000`

---

## Feature Testing Checklist

### ✅ Phase 0: Database Foundation

**Test Admin Endpoints:**

```bash
# Get database statistics
curl http://localhost:8000/admin/db-stats

# Expected: JSON with posts, users, insights counts
```

```bash
# Get system health
curl http://localhost:8000/admin/health

# Expected: Health status with database and worker checks
```

```bash
# Get worker status
curl http://localhost:8000/admin/worker-status

# Expected: Queue depth and processing statistics
```

**Test Post Creation:**

```bash
# Create a post (requires auth token)
curl -X POST http://localhost:8000/posts/create \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "NVDA showing strong momentum ahead of earnings. Cloud revenue expected to surge 30% QoQ. Buying the dip.",
    "tickers": ["NVDA", "AMD"]
  }'

# Expected: Post created with llm_status: "pending"
```

```bash
# Check post processing status
curl http://localhost:8000/posts/{post_id}/status \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: Status info with queue position
```

---

### ✅ Phase 1: Enhanced LLM Pipeline & Semantic Tagging

**Verify LLM Processing:**

Once the worker processes a post, check the insights:

```sql
SELECT p.id, p.content, i.insight_type, i.sector, i.sub_sector, 
       i.catalyst, i.risk_profile, i.time_horizon, i.quality_score,
       i.confidence_level, i.relevance_score, i.sentiment
FROM posts p
JOIN insights i ON p.id = i.post_id
WHERE p.llm_status = 'processed'
LIMIT 5;
```

Expected fields:
- `insight_type`: fundamental_analysis, technical_analysis, etc.
- `sector`: Technology, Healthcare, Finance, etc.
- `catalyst`: earnings, merger, regulatory, etc.
- `sentiment`: bullish, bearish, neutral

**Test Trend Detection:**

```bash
# Detect trends manually
curl -X POST "http://localhost:8000/trends/detect?time_window=24h&min_posts=3" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: List of detected trends with confidence scores
```

```bash
# Get market trends
curl http://localhost:8000/trends/market

# Expected: Active market trends
```

```bash
# Get trends for a specific ticker
curl http://localhost:8000/trends/tickers/NVDA

# Expected: NVDA-specific trends
```

---

### ✅ Phase 2: Live Market Data Integration

**Test Market Endpoints:**

```bash
# Get ticker snapshot
curl http://localhost:8000/market/snapshot/NVDA

# Expected: Real-time price, change %, volume, market cap
```

```bash
# Batch fetch multiple tickers
curl -X POST http://localhost:8000/market/batch \
  -H "Content-Type: application/json" \
  -d '["NVDA", "AAPL", "TSLA", "AMD", "GOOGL"]'

# Expected: Array of ticker data
```

```bash
# Get market events (volume spikes, big moves)
curl "http://localhost:8000/market/events?hours=24&limit=20"

# Expected: List of significant market events
```

**Verify Market Alignment Scoring:**

After 24-48 hours, the worker will score posts against actual market movements:

```sql
SELECT ma.post_id, ma.ticker, ma.predicted_direction, 
       ma.actual_direction, ma.alignment_score, 
       ma.price_change_percent, ma.timing_accuracy
FROM market_alignments ma
ORDER BY ma.created_at DESC
LIMIT 10;
```

---

### ✅ Phase 3: Ensemble Ranking Engine

**Test Feed Endpoints:**

```bash
# Get balanced feed
curl "http://localhost:8000/feed?strategy=balanced&limit=20" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: Posts ranked by balanced strategy
```

```bash
# Get quality-focused feed
curl "http://localhost:8000/feed?strategy=quality_focused&limit=20" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: High-quality posts prioritized
```

```bash
# Get timely feed
curl "http://localhost:8000/feed/timely?limit=20" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: Recent, market-aligned posts prioritized
```

**Verify Reputation System:**

```sql
SELECT r.user_id, r.overall_score, r.historical_accuracy,
       r.engagement_score, r.consistency_score,
       COUNT(p.id) as post_count
FROM reputation r
LEFT JOIN posts p ON r.user_id = p.user_id
GROUP BY r.user_id, r.overall_score, r.historical_accuracy, 
         r.engagement_score, r.consistency_score
ORDER BY r.overall_score DESC;
```

---

### ✅ Phase 4: Transparency & Explainability

**Test Transparency Endpoints:**

```bash
# Get post ranking breakdown
curl "http://localhost:8000/transparency/post/{post_id}" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: Full signal breakdown with explanation
```

```bash
# Get user reputation breakdown
curl "http://localhost:8000/transparency/user/{user_id}/reputation" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: Detailed reputation components
```

```bash
# Get LLM audit logs
curl "http://localhost:8000/transparency/llm-audit/{post_id}" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: LLM processing logs with latency
```

```bash
# Explain feed ranking
curl -X POST "http://localhost:8000/transparency/explain-ranking?strategy=balanced&limit=5" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT"

# Expected: Strategy weights and example explanations
```

---

### ✅ Phase 5: Enhanced Dashboard UI

**Frontend Testing:**

1. **Visit Homepage** (`http://localhost:3000`)
   - Should show feed with posts
   - Posts should display quality scores
   - AI Insight sections should be expandable
   - Ticker badges should be clickable

2. **Create a Post**
   - Click "Create Post" button
   - Enter content with tickers
   - Submit and verify it appears in feed

3. **Visit Trending Page** (`http://localhost:3000/trending`)
   - Should show trending tickers
   - Each ticker should show price, change %, volume
   - Cards should be interactive with hover effects

4. **Visit Profile Page** (`http://localhost:3000/profile`)
   - Should show user's reputation
   - Should display recent posts
   - Should show stats

---

## End-to-End Testing Flow

### Complete User Journey

1. **Sign In (Anonymous)**
   ```
   Frontend → Supabase Auth → Creates user profile
   ```

2. **Create Post**
   ```
   User creates post → POST /posts/create → Stored with llm_status: "pending"
   ```

3. **Worker Processes Post**
   ```
   Worker picks up post → Calls LLM → Generates insights → Creates embeddings
   → Updates reputation → Marks as "processed"
   ```

4. **Post Appears in Feed**
   ```
   User refreshes feed → GET /feed → Ensemble ranker scores posts
   → Returns ranked feed with explanations
   ```

5. **Market Alignment Scoring (24h later)**
   ```
   Cron job runs → Fetches market data → Compares prediction vs. reality
   → Updates market_alignments table → Updates reputation
   ```

6. **Trend Detection**
   ```
   Cron job or manual trigger → Analyzes recent posts
   → Calls LLM to detect patterns → Stores in trends table
   ```

---

## Performance Benchmarks

### Expected Latencies

| Operation | Expected Latency |
|-----------|-----------------|
| POST creation | < 200ms |
| LLM processing (comprehensive) | 5-10 seconds |
| Feed retrieval (20 posts) | < 500ms |
| Market snapshot (cached) | < 100ms |
| Market snapshot (uncached) | 1-2 seconds |
| Trend detection (50 posts) | 10-15 seconds |
| Transparency breakdown | < 300ms |

### Database Query Performance

Check slow queries:
```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC
LIMIT 20;
```

---

## Debugging Common Issues

### Issue: Posts Stuck in "Pending"

**Diagnosis:**
```bash
curl http://localhost:8000/admin/worker-status
```

**Solutions:**
1. Check worker is running: `arq app.worker.WorkerSettings`
2. Check Redis is running
3. Check for error logs in worker output
4. Check `/admin/recent-errors` for failed posts

### Issue: Low Quality Scores

**Diagnosis:**
Check LLM audit logs to see what the LLM is returning:
```sql
SELECT task_type, model, latency_ms, output
FROM llm_audit_logs
ORDER BY created_at DESC
LIMIT 5;
```

**Solutions:**
1. Verify OpenRouter API key is valid
2. Check model availability
3. Review prompt engineering in `llm.py`

### Issue: Market Data Not Updating

**Diagnosis:**
```bash
# Check market cache
curl http://localhost:8000/market/snapshot/NVDA
# Look for "from_cache": true/false
```

**Solutions:**
1. Check yfinance is working: `python -c "import yfinance as yf; print(yf.Ticker('NVDA').fast_info.last_price)"`
2. Clear cache and retry
3. Check for rate limiting from Yahoo Finance

### Issue: Reputation Not Updating

**Diagnosis:**
```sql
SELECT * FROM reputation ORDER BY updated_at DESC LIMIT 10;
```

**Solutions:**
1. Manually trigger: `SELECT recompute_reputation();`
2. Check cron job logs
3. Verify market_alignments table has data

---

## Monitoring Queries

### System Health Dashboard

```sql
-- Platform overview
SELECT * FROM platform_stats;

-- Recent posts processing rate
SELECT 
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) as total,
  SUM(CASE WHEN llm_status = 'processed' THEN 1 ELSE 0 END) as processed,
  SUM(CASE WHEN llm_status = 'pending' THEN 1 ELSE 0 END) as pending,
  SUM(CASE WHEN llm_status = 'failed' THEN 1 ELSE 0 END) as failed
FROM posts
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Top users by reputation
SELECT * FROM get_top_users_by_reputation(20);

-- Recent trends
SELECT * FROM get_active_trends('market', NULL, 10);

-- Market alignment accuracy
SELECT 
  AVG(alignment_score) as avg_accuracy,
  COUNT(*) as total_predictions,
  SUM(CASE WHEN timing_accuracy = 'on_time' THEN 1 ELSE 0 END) as on_time_count
FROM market_alignments
WHERE created_at > NOW() - INTERVAL '7 days';
```

---

## Success Criteria

✅ **The platform is working correctly if:**

1. Posts are created successfully
2. Worker processes posts within 30 seconds
3. Insights table populated with semantic tags
4. Feed returns ranked posts with scores
5. Market data endpoints return real-time data
6. Transparency endpoints provide full breakdowns
7. Reputation scores update after processing
8. Trends are detected from post clusters
9. No posts stuck in pending > 10 minutes
10. LLM audit logs show successful processing

---

## Load Testing (Optional)

### Create Multiple Posts

```python
import requests
import time

BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "YOUR_SUPABASE_JWT"

posts = [
    {"content": "AAPL showing strong support at $180. Good entry point.", "tickers": ["AAPL"]},
    {"content": "TSLA deliveries beat estimates. Bullish on Q4.", "tickers": ["TSLA"]},
    {"content": "AMD gaining market share from INTC. Long AMD.", "tickers": ["AMD", "INTC"]},
    # Add more posts...
]

for post in posts:
    response = requests.post(
        f"{BASE_URL}/posts/create",
        json=post,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
    )
    print(f"Created post: {response.json()['id']}")
    time.sleep(1)  # Rate limit
```

Monitor worker processing time and success rate.

---

## Conclusion

This testing guide covers all major features of the platform. For production deployment, add:
- Automated test suite (pytest for backend, Jest for frontend)
- Load testing with realistic traffic patterns
- Security penetration testing
- Disaster recovery testing
- Performance profiling under load

The platform is now ready for comprehensive testing and refinement! 🚀




