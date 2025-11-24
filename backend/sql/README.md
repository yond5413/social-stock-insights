# SQL Migrations for Supabase

This directory contains PostgreSQL functions (RPC) that need to be created in your Supabase database.

## How to Apply

### Option 1: Supabase Dashboard SQL Editor
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of each `.sql` file
4. Run each migration in order (001, 002, etc.)

### Option 2: Supabase CLI
```bash
supabase db push
```

### Option 3: psql
```bash
psql <your-database-url> -f 001_get_personalized_feed.sql
psql <your-database-url> -f 002_get_trending_tickers.sql
```

## Functions Created

### 1. `get_personalized_feed(p_user_id uuid, p_limit int, p_offset int)`
Returns personalized feed with ranking based on:
- LLM quality scores
- User reputation
- Engagement (likes/dislikes)

### 2. `get_trending_tickers(p_hours int, p_limit int)`
Returns trending tickers based on mention count in the specified time window.

### 3. `semantic_search_posts(query_embedding vector(1024), search_limit int)`
Performs semantic search over posts using pgvector similarity.
Requires Cohere embed-english-v3.0 embeddings (1024 dimensions).

### 4. `recompute_reputation()`
Updates user reputation scores based on post quality and engagement metrics.
Called by the ARQ worker cron job.

## Notes
- These functions use `SECURITY DEFINER` to bypass RLS policies when needed
- Proper permissions are granted to authenticated users and service roles
- The functions are optimized with proper indexes on relevant columns

