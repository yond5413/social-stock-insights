# Frontend - Social Stocks Insights

Next.js frontend for the Social Stocks Insights platform.

## Features

- **Ranked Feed**: Personalized feed of stock insights with LLM-generated summaries and quality scores.
- **Post Creation**: Create new posts with ticker tagging (e.g., $AAPL).
- **Engagement**:
  - **Likes**: Like/unlike posts.
  - **Comments**: View and add comments to posts.
- **Search**: Fuzzy search for posts by content or ticker.
- **Usernames**: Displays actual usernames from user profiles.
- **Authentication**: Anonymous sign-in via Supabase Auth.

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI, Lucide React
- **Data Fetching**: SWR
- **State/Effects**: React Hooks

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Environment Variables

Create a `.env.local` file in the `frontend/` directory with the following variables:

```env
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Project Structure

- `app/`: Next.js App Router pages and layouts.
- `components/`: Reusable UI components (PostCard, CommentsDialog, etc.).
- `lib/`: Utility functions and Supabase client.
- `hooks/`: Custom React hooks.
