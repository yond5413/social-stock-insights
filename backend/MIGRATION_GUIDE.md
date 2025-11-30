# Supabase Migration Guide

This guide walks you through migrating the backend from raw PostgreSQL connections to Supabase Python SDK.

## What Changed

### 1. Dependencies
- **Added**: `supabase`, `cohere`
- **Removed**: `asyncpg`, `PyJWT` (no longer needed)

### 2. Configuration
- **Removed**: `DATABASE_URL` (deprecated)
- **Added**: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `COHERE_API_KEY`

### 3. Database Operations
- All database operations now use Supabase client
- Complex queries moved to PostgreSQL RPC functions
- Embeddings now use Cohere's `embed-english-v3.0` model (1024 dimensions)

### 4. Authentication
- Switched from manual JWT handling to Supabase Auth verification
- More secure and maintainable

## Setup Steps

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create `backend/.env` or `backend/.env.local`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Cohere
COHERE_API_KEY=your-cohere-api-key

# OpenRouter
OPENROUTER_API_KEY=your-openrouter-api-key
```

### Step 3: Apply SQL Migrations

You need to create the RPC functions in your Supabase database:

#### Option A: Supabase Dashboard
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Run each file in `backend/sql/` in order:
   - `001_get_personalized_feed.sql`
   - `002_get_trending_tickers.sql`
   - `003_semantic_search_posts.sql`
   - `004_recompute_reputation.sql`

#### Option B: psql Command Line
```bash
psql <your-database-connection-string> -f backend/sql/001_get_personalized_feed.sql
psql <your-database-connection-string> -f backend/sql/002_get_trending_tickers.sql
psql <your-database-connection-string> -f backend/sql/003_semantic_search_posts.sql
psql <your-database-connection-string> -f backend/sql/004_recompute_reputation.sql
```

### Step 4: Verify Database Schema

Ensure your Supabase database has these tables:
- `profiles` (or `users`)
- `posts`
- `post_embeddings` (with `vector(1024)` column for Cohere embeddings)
- `insights`
- `reputation`
- `post_engagement`
- `llm_audit_logs`

### Step 5: Update Embedding Dimensions

If you were using OpenAI embeddings before (1536 dimensions), you need to update your `post_embeddings` table to use 1024 dimensions for Cohere:

```sql
-- If the table exists with wrong dimensions, you may need to recreate it
ALTER TABLE post_embeddings ALTER COLUMN embedding TYPE vector(1024);
```

### Step 6: Start the Backend

```bash
uvicorn app.main:app --reload --port 8000
```

### Step 7: Start the Worker (Optional)

```bash
arq app.worker.WorkerSettings
```

## Testing

### Test Health Endpoint
```bash
curl http://localhost:8000/health
```

### Test Creating a Post
```bash
curl -X POST http://localhost:8000/posts/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT_TOKEN" \
  -d '{"content": "AAPL looking strong", "tickers": ["AAPL"]}'
```

### Test Feed Endpoint
```bash
curl http://localhost:8000/feed/ \
  -H "Authorization: Bearer YOUR_SUPABASE_JWT_TOKEN"
```

### Test Trending Endpoint
```bash
curl http://localhost:8000/market/trending
```

## Benefits of This Migration

1. **Cleaner Code**: Supabase SDK is more intuitive than raw SQL
2. **Better Performance**: RPC functions are optimized and cached
3. **Easier Auth**: Supabase handles JWT verification automatically
4. **Better Embeddings**: Cohere's models are more powerful and cost-effective
5. **Scalability**: Built-in connection pooling and optimization
6. **Security**: Easy to add Row Level Security (RLS) policies

## Troubleshooting

### Issue: "relation 'posts' does not exist"
**Solution**: Make sure your database schema is created in Supabase. Check the schema in Supabase Dashboard > Table Editor.

### Issue: "Function 'get_personalized_feed' does not exist"
**Solution**: Run the SQL migrations from `backend/sql/` directory.

### Issue: "Invalid or expired token"
**Solution**: Make sure you're passing a valid Supabase JWT token in the Authorization header.

### Issue: "Embedding dimension mismatch"
**Solution**: Cohere uses 1024-dimensional embeddings. Update your `post_embeddings` table schema.

## Rollback (if needed)

If you need to rollback to the old asyncpg version:

1. Restore `backend/requirements.txt` to include `asyncpg` and remove `supabase`, `cohere`
2. Restore the old `backend/app/db.py` file
3. Restore the old router files
4. Run `pip install -r requirements.txt`

However, the new version is recommended for production use.




