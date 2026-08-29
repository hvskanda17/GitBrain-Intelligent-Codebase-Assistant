export type UserRole = "admin" | "developer" | "viewer";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
}

export interface Project {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export type IndexingStatus =
  | "pending"
  | "cloning"
  | "parsing"
  | "analyzing"
  | "embedding"
  | "ready"
  | "failed";

export interface Repository {
  id: string;
  project_id: string;
  remote_url: string;
  default_branch: string;
  primary_language: string | null;
  status: IndexingStatus;
  last_indexed_at: string | null;
  stats: Record<string, unknown>;
  created_at: string;
}

export interface RepositoryStatusResponse {
  status: IndexingStatus;
  progress_pct: number | null;
  current_stage: string | null;
}

export interface RepositoryCreateResponse {
  repository_id: string;
  status: IndexingStatus;
}
