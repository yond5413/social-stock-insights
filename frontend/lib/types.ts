export interface FeedItem {
  id: string;
  user_id: string;
  username?: string | null;
  content: string;
  tickers: string[];
  llm_status: string | null;
  created_at: string;
  summary?: string | null;
  quality_score?: number | null;
  final_score: number;
  view_count?: number;
  like_count?: number;
  comment_count?: number;
  engagement_score?: number;
  user_has_liked?: boolean;
  sentiment?: string | null;
  is_processing?: boolean;
}



