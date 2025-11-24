# Backend - Social Stocks Insights

FastAPI backend for the Social Stocks Insights platform, now powered by Supabase.

## Features

- **Supabase Integration**: Using Supabase Python SDK for database operations
- **Supabase Auth**: Built-in authentication with JWT verification
- **PostgreSQL RPC Functions**: Complex queries optimized as database functions
- **Cohere Embeddings**: Using `embed-english-v3.0` for semantic search
- **OpenRouter LLM**: For post analysis, tagging, and quality scoring
- **ARQ Workers**: Async background jobs for LLM processing
- **yfinance**: Real-time market data integration

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` or `.env.local` in the `backend/` directory:

```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Cohere
COHERE_API_KEY=your-cohere-api-key

# OpenRouter
OPENROUTER_API_KEY=your-openrouter-api-key
```

### 3. Apply Database Migrations

Run the SQL files in `sql/` directory in your Supabase SQL Editor:

1. `001_get_personalized_feed.sql`
2. `002_get_trending_tickers.sql`
3. `003_semantic_search_posts.sql`
4. `004_recompute_reputation.sql`

See `sql/README.md` for details.

### 4. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### 5. Run the Worker (Optional)

For background LLM processing:

```bash
arq app.worker.WorkerSettings
```

## API Endpoints

### Health Check
```
GET /health
```

### Posts
```
POST /posts/create - Create a new post
GET /posts/{post_id} - Get a specific post
```

### Feed
```
GET /feed/ - Get personalized ranked feed
```

### Market
```
GET /market/snapshot/{ticker} - Get real-time ticker data
GET /market/trending - Get trending tickers
```

### Insights
```
POST /insights/search - Semantic search over posts
```

### Development
```
POST /dev/seed - Seed database with test data
```

## Architecture

### Database Operations
- Simple CRUD: Supabase PostgREST (`.insert()`, `.select()`, `.update()`)
- Complex Queries: PostgreSQL RPC functions (`.rpc()`)
- Auth: Supabase Auth verification

### Embeddings
- Model: Cohere `embed-english-v3.0`
- Dimensions: 1024
- Storage: `post_embeddings` table with pgvector

### LLM Processing
- Tagging & Scoring: OpenRouter (configurable model)
- Async Processing: ARQ workers
- Audit Logging: `llm_audit_logs` table

## Project Structure

```
backend/
├── app/
│   ├── config.py           # Environment configuration
│   ├── supabase_client.py  # Supabase client & auth
│   ├── llm.py              # LLM & embedding functions
│   ├── main.py             # FastAPI application
│   ├── schemas.py          # Pydantic models
│   ├── worker.py           # ARQ background workers
│   └── routers/
│       ├── posts.py        # Post CRUD
│       ├── feed.py         # Ranked feed
│       ├── market.py       # Market data
│       ├── insights.py     # Semantic search
│       └── dev.py          # Development utilities
├── sql/
│   ├── 001_get_personalized_feed.sql
│   ├── 002_get_trending_tickers.sql
│   ├── 003_semantic_search_posts.sql
│   ├── 004_recompute_reputation.sql
│   └── README.md
├── requirements.txt
├── MIGRATION_GUIDE.md
└── README.md
```

## Development

### Testing Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get trending tickers
curl http://localhost:8000/market/trending

# Get feed (requires auth token)
curl http://localhost:8000/feed/ \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT_TOKEN"
```

### API Documentation

FastAPI automatically generates OpenAPI docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Migration from asyncpg

See `MIGRATION_GUIDE.md` for detailed migration instructions from the previous asyncpg implementation.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Supabase anon/public key | Yes |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | Yes |
| `COHERE_API_KEY` | Cohere API key for embeddings | Yes |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM | Yes |

## Troubleshooting

### "relation 'posts' does not exist"
Ensure your database schema is created in Supabase.

### "Function does not exist"
Run the SQL migrations from the `sql/` directory.

### "Invalid or expired token"
Make sure you're using a valid Supabase JWT token.

### Embedding dimension mismatch
Cohere uses 1024-dimensional embeddings. Update your schema if needed.

## License

See root LICENSE file.

