import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { apiFetch, requireSession } from "@/lib/api";
import { ACCESS_COOKIE } from "@/lib/session";
import type { Repository } from "@/types/api";
import type { ChatSession } from "@/types/chat";
import { ChatInterface } from "@/components/chat/chat-interface";
import { RepositoryActions } from "@/components/repositories/repository-actions";

export const metadata: Metadata = { title: "Chat · GitBrain" };

export default async function RepositoryChatPage({
  params,
}: {
  params: Promise<{ projectId: string; repositoryId: string }>;
}) {
  const { projectId, repositoryId } = await params;
  
  // Verify session & repository
  const [user, repository] = await Promise.all([
    requireSession(),
    apiFetch<Repository>(`/api/v1/repositories/${repositoryId}`).catch(() => null),
  ]);

  if (!repository) {
    redirect(`/projects/${projectId}`);
  }

  // Need access token for client-side API requests since we're not running through a proxy for SSE easily
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_COOKIE)?.value;

  // Fetch initial sessions
  const sessions = await apiFetch<ChatSession[]>(`/api/v1/chat/sessions?repository_id=${repositoryId}`).catch(() => []);

  // Ensure pinned sessions appear first, then newest
  const sortedSessions = [...sessions].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate font-mono text-lg font-medium">{repository.remote_url} / Chat</h1>
          <p className="text-sm text-ink-soft">Ask questions about your codebase.</p>
        </div>
        <RepositoryActions projectId={projectId} repositoryId={repositoryId} viewerRole={user.role} />
      </div>

      <ChatInterface 
        repositoryId={repositoryId} 
        initialSessions={sortedSessions} 
        accessToken={accessToken} 
      />
    </div>
  );
}
