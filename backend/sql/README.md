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

## Migrations Applied

### 1. `001_get_personalized_feed.sql`
**Function:** `get_personalized_feed(p_user_id uuid, p_limit int, p_offset int)`

Returns personalized feed with ranking based on:
- LLM quality scores
- User reputation
- Engagement (likes/dislikes)

### 2. `002_get_trending_tickers.sql`
**Function:** `get_trending_tickers(p_hours int, p_limit int)`

Returns trending tickers based on mention count in the specified time window.

### 3. `003_semantic_search_posts.sql`
**Function:** `semantic_search_posts(query_embedding vector(1024), search_limit int)`

Performs semantic search over posts using pgvector similarity.
Requires Cohere embed-english-v3.0 embeddings (1024 dimensions).

### 4. `004_recompute_reputation.sql`
**Function:** `recompute_reputation()`

Updates user reputation scores based on post quality and engagement metrics.
Called by the ARQ worker cron job.

### 5. `005_auto_create_profiles.sql` ⭐ **IMPORTANT**
**Function:** `handle_new_user()`  
**Trigger:** `on_auth_user_created`

Automatically creates a profile entry in `public.profiles` when a new user signs up via Supabase Auth.

**What it does:**
- Trigger fires on every new user registration in `auth.users`
- Creates corresponding entry in `public.profiles` table
- Extracts username from email or generates one
- Backfills profiles for any existing auth users

**Why it's important:**
This ensures data consistency between `auth.users` and `public.profiles` tables, eliminating the need for manual profile creation or sync endpoints.

## Notes
- These functions use `SECURITY DEFINER` to bypass RLS policies when needed
- Proper permissions are granted to authenticated users and service roles
- The functions are optimized with proper indexes on relevant columns

## Troubleshooting

### Profile Not Found Error
**Symptom:** Users get "Profile not found" or foreign key constraint errors when creating posts.

**Solution:**
1. Verify the trigger is installed:
   ```sql
   SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';
   ```

2. Check if profile exists for the user:
   ```sql
   SELECT id, username, email FROM public.profiles WHERE id = 'USER_UUID';
   ```

3. Manually create profile if missing:
   ```sql
   INSERT INTO public.profiles (id, username, email)
   VALUES ('USER_UUID', 'username', 'email@example.com');
   ```

4. Re-run the backfill from `005_auto_create_profiles.sql` if multiple users are affected.

### Trigger Not Firing
**Symptom:** New users sign up but profiles aren't created automatically.

**Solution:**
1. Check trigger status:
   ```sql
   SELECT * FROM pg_trigger WHERE tgname = 'on_auth_user_created';
   ```

2. Verify function exists:
   ```sql
   SELECT routine_name FROM information_schema.routines 
   WHERE routine_name = 'handle_new_user';
   ```

3. Re-apply the migration `005_auto_create_profiles.sql` if needed.

