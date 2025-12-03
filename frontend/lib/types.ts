export interface FeedItem {
  id: string;
  user_id: string;
  username?: string | null;
  content: string;
  tickers: string[];
  llm_status: string | null;
  created_at: string;
  summary?: string | null;
  sentiment?: string | null;
  quality_score?: number | null;
  final_score: number;
  view_count?: number;
  like_count?: number;
  comment_count?: number;
  engagement_score?: number;
  user_has_liked?: boolean;
  is_bookmarked?: boolean;
  insight_type?: string | null;
  is_processing?: boolean;
}
