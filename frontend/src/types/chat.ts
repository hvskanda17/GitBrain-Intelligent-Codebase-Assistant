export interface ChatSession {
  id: string;
  repository_id: string;
  user_id: string;
  title: string | null;
  is_pinned: boolean;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  sources: Array<{
    source_type: string;
    source_id: string;
    label: string;
    file_path: string;
    score: number;
  }>;
  confidence_score: number | null;
  is_saved: boolean;
  created_at: string;
}
