## Social Stocks Insights

A social platform for sharing **stock market insights**, powered by an LLM-backed ranking engine.  
Think **StockTwits/Twitter, but optimized for deep stock analysis**: posts are tagged, summarized, scored for quality, and ranked using both **semantic signals and market data**.

---

## Core Features

- **Insight posts**
  - Users create free-form posts about tickers.
  - Tickers are stored and used for feeds, market data, and trending views.

- **LLM intelligence (via OpenRouter)**
  - Tagging: insight type, sector, catalyst, risk profile.
  - Summarization: short summary for each post.
  - Quality scoring: normalized 0–1 score.
  - Embeddings: semantic search over posts.

- **Ranking engine**
  - Combines:
    - LLM quality score
    - Author reputation
    - Engagement (likes/dislikes)
    - (Planned) market alignment from `yfinance`
  - Drives the **personalized / global feed**.

- **Semantic search**
  - Embedding-based search endpoint to find related insights by meaning, not keywords.

- **Supabase-native backend**
  - Postgres + `pgvector` for embeddings.
  - Supabase Auth for sessions.
  - RLS policies set for app tables.

- **Modern frontend**
  - Next.js app with:
    - Anonymous sign-in via Supabase Auth.
    - Create-post UI.
    - Ranked feed with summaries & scores.

---

## Tech Stack

- **Frontend**: Next.js (React), TypeScript
- **Backend**: FastAPI (Python)
- **Async workers**: ARQ + Redis
- **Database**: Supabase Postgres (`pgvector` enabled)
- **Auth**: Supabase Auth (JWT)
- **LLMs**: OpenRouter (free models like `openai/gpt-oss-20b:free`, etc.)
- **Market data**: `yfinance` (for live prices / OHLC)

---

## Getting Started

🚀 **Quick Start**: See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed setup instructions with API key links.

### Prerequisites

You'll need API keys from:
- **Supabase** (Project URL, Anon Key, Service Key)
- **Cohere** (for embeddings)
- **OpenRouter** (for LLM operations)

### Quick Setup

#### 1. Create Environment Files

**Option A - Use the helper script (Windows):**
```powershell
.\create-env-files.ps1
```

**Option B - Use the helper script (Mac/Linux):**
```bash
chmod +x create-env-files.sh
./create-env-files.sh
```

**Option C - Manual creation:**
- Copy `env.example` contents to `backend/.env`
- Copy `env.example` contents to `frontend/.env.local` (use only the `NEXT_PUBLIC_*` variables)

#### 2. Add Your API Keys

Edit the created files and replace placeholder values with your actual API keys.

See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed instructions on getting API keys.

#### 3. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

#### 4. Run the Application

**Backend API:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Health check: `GET http://localhost:8000/health`

**Frontend:**
```bash
cd frontend
npm run dev
```
App will be at: `http://localhost:3000`

**Worker (optional):**
```bash
cd backend
arq app.worker.WorkerSettings
```
The worker processes posts with LLM tagging, summarization, and scoring.

---

## How It Works (High Level)

1. **User signs in (anon)** via Supabase Auth; frontend gets a JWT.
2. **User creates a post** from the Next.js UI.
3. **FastAPI**:
   - Stores the post in `posts` (tying it to Supabase `auth.users` via `profiles`).
   - Marks `llm_status = 'pending'`.
   - (Expected) enqueues `process_post(post_id)` to Redis/ARQ.
4. **Worker**:
   - Calls OpenRouter to:
     - Tag + summarize + score.
     - Generate embeddings (content + summary).
   - Writes to `insights`, `post_embeddings`, `llm_audit_logs`, and updates `reputation`.
   - Marks `llm_status = 'processed'`.
5. **Feed endpoint** computes a `final_score` using:
   - `quality_score` (LLM)
   - `reputation.overall_score`
   - Engagement (likes/dislikes)
6. **Frontend feed**:
   - Calls `/feed` using the user’s token.
   - Renders posts with tickers, summary, quality score, and final ranking score.

---

## API Overview (MVP)

- **Health**
  - `GET /health` → `{ "status": "ok" }`

- **Posts**
  - `POST /posts/create` – create a new post (auth required).
  - `GET /posts/{id}` – fetch a post.

- **Feed & search**
  - `GET /feed` – ranked feed (global/personalized).
  - `POST /insights/search` – semantic search over posts.

- **(Planned) Market data**
  - `GET /market/{ticker}` – latest snapshot.
  - Background worker: `ingest_market_data` via `yfinance`.

---

## Testing

### Manual end-to-end

1. Start:
   - `uvicorn app.main:app --reload --port 8000`
   - `arq app.worker.WorkerSettings`
   - `npm run dev` (frontend).

2. In the browser:
   - Go to `http://localhost:3000`.
   - Click **“Sign in (anon)”**.
   - Create a post (with tickers like `AAPL, TSLA`).
   - Wait a short time for the worker to process.
   - Refresh feed:
     - You should see:
       - Your post.
       - LLM summary.
       - Quality score & final ranking score.

3. Inspect Supabase tables:
   - `posts`, `insights`, `post_embeddings`, `reputation`, `llm_audit_logs` should all have new rows.

### API sanity checks

Use curl/Postman:

- `GET /health`
- `POST /posts/create` (with `Authorization: Bearer <supabase-jwt>`)
- `GET /feed`
- `POST /insights/search` with `{ "query": "EV earnings", "limit": 10 }`

---

## Roadmap (Post-Hackathon)

- Full **ticker pages** with market data and per-ticker ranking.
- **Trending tickers** view.
- Rich **comments** and conversations.
- Advanced **reputation** metrics (sector expertise, historical accuracy).
- More robust **auth** (proper JWT verification, non-anonymous users).
- Production-grade **monitoring**, rate limiting, and prompt tuning.