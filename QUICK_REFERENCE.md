# Quick Reference - Environment Variables

## 🔑 Where to Get API Keys

| Service | URL | What to Get |
|---------|-----|-------------|
| **Supabase** | [app.supabase.com](https://app.supabase.com) | Settings → API → Copy URL, anon key, service_role key |
| **Cohere** | [dashboard.cohere.com/api-keys](https://dashboard.cohere.com/api-keys) | Create new API key |
| **OpenRouter** | [openrouter.ai/keys](https://openrouter.ai/keys) | Create new API key |

## 📁 File Locations

```
frontend/.env.local          ← Frontend environment variables
backend/.env                 ← Backend environment variables
```

## 📋 Required Variables

### Frontend (`frontend/.env.local`)
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Backend (`backend/.env`)
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
COHERE_API_KEY=your-cohere-api-key
OPENROUTER_API_KEY=sk-or-v1-...
```

## ✅ Verification Checklist

- [ ] Created `frontend/.env.local` file
- [ ] Created `backend/.env` file
- [ ] Added Supabase URL (both files)
- [ ] Added Supabase anon key (both files)
- [ ] Added Supabase service key (backend only)
- [ ] Added Cohere API key (backend only)
- [ ] Added OpenRouter API key (backend only)
- [ ] Restarted backend server
- [ ] Restarted frontend server
- [ ] Backend starts without validation errors
- [ ] Frontend starts without "supabaseUrl is required" error

## 🚀 Start Commands

```bash
# Backend (from backend/ directory)
uvicorn app.main:app --reload --port 8000

# Frontend (from frontend/ directory)
npm run dev
```

## 🔍 Common Errors

| Error | Solution |
|-------|----------|
| "supabaseUrl is required" | Missing `NEXT_PUBLIC_SUPABASE_URL` in `frontend/.env.local` |
| "5 validation errors for Settings" | Missing environment variables in `backend/.env` |
| Variables not loading | Restart the server after creating/editing .env files |

## 💡 Tips

- Never commit `.env` or `.env.local` files (already in `.gitignore`)
- Both Cohere and OpenRouter have free tiers
- Use the same Supabase URL and anon key for both frontend and backend
- The service key is different from the anon key (and more powerful - keep it secret!)





