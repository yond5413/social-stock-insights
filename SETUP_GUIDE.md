# Environment Setup Guide

## 🚨 Current Issue
Your application is failing because environment variables are missing. Both frontend and backend need API keys to function.

## ✅ Quick Fix (3 Steps)

### Step 1: Create Frontend Environment File

Create a file named `.env.local` in the `frontend` directory with this content:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url-here
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key-here
```

**File location:** `frontend/.env.local`

### Step 2: Create Backend Environment File

Create a file named `.env` in the `backend` directory with this content:

```env
# Supabase Configuration
SUPABASE_URL=your-supabase-url-here
SUPABASE_ANON_KEY=your-supabase-anon-key-here
SUPABASE_SERVICE_KEY=your-supabase-service-role-key-here

# Cohere API Key (for embeddings)
COHERE_API_KEY=your-cohere-api-key-here

# OpenRouter API Key (for LLM tagging and scoring)
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

**File location:** `backend/.env`

### Step 3: Get Your API Keys

Replace the placeholder values with real API keys:

#### 📦 Supabase Keys (Required for both frontend and backend)
1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project (or create a new one)
3. Go to **Settings** → **API**
4. Copy the following:
   - **Project URL** → Use for `SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public** key → Use for `SUPABASE_ANON_KEY` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role** key (⚠️ Secret!) → Use for `SUPABASE_SERVICE_KEY`

#### 🤖 Cohere API Key (Required for backend - embeddings)
1. Go to [Cohere Dashboard](https://dashboard.cohere.com/api-keys)
2. Sign up or log in
3. Create a new API key
4. Copy it to `COHERE_API_KEY`

#### 🧠 OpenRouter API Key (Required for backend - LLM operations)
1. Go to [OpenRouter](https://openrouter.ai/keys)
2. Sign up or log in
3. Create a new API key
4. Copy it to `OPENROUTER_API_KEY`

## 🔄 After Creating the Files

1. **Restart both servers:**
   - Stop the frontend server (Ctrl+C in terminal 1)
   - Stop the backend server (Ctrl+C in terminal 2)
   - Start backend: `cd backend && uvicorn app.main:app --reload --port 8000`
   - Start frontend: `cd frontend && npm run dev`

2. **Verify it works:**
   - Backend should start without validation errors
   - Frontend should start without "supabaseUrl is required" error

## 📝 Notes

- **Security:** Never commit `.env` files to Git (they're already in `.gitignore`)
- **API_BASE_URL:** The frontend already defaults to `http://localhost:8000`, so you don't need to set `NEXT_PUBLIC_API_BASE_URL` for local development
- **Free tiers available:** Both Cohere and OpenRouter offer free tiers for testing

## ❓ Troubleshooting

### Backend still shows validation errors?
- Make sure `.env` file is in the `backend` directory (not the root)
- Check that there are no typos in variable names
- Restart the backend server

### Frontend still shows "supabaseUrl is required"?
- Make sure `.env.local` file is in the `frontend` directory (not the root)
- Variable names must start with `NEXT_PUBLIC_` for Next.js
- Restart the frontend server







