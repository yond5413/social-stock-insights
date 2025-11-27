export interface FeedItem {
  id: string;
  user_id: string;
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
  sentiment?: string | null;
  is_processing?: boolean;
}



