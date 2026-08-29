import type { Metadata } from "next";

import { RepositoryActions } from "@/components/repositories/repository-actions";
import { RepositoryStatusPoller } from "@/components/repositories/repository-status-poller";
import { apiFetch, requireSession } from "@/lib/api";
import type { Repository } from "@/types/api";

import Link from "next/link";
import { MessageSquare } from "lucide-react";

export const metadata: Metadata = { title: "Repository · GitBrain" };

export default async function RepositoryDetailPage({
  params,
}: {
  params: Promise<{ projectId: string; repositoryId: string }>;
}) {
  const { projectId, repositoryId } = await params;
  const [repository, user] = await Promise.all([
    apiFetch<Repository>(`/api/v1/repositories/${repositoryId}`),
    requireSession(),
  ]);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="truncate font-mono text-lg font-medium">{repository.remote_url}</h1>
          <p className="text-sm text-ink-soft">{repository.default_branch}</p>
        </div>
        <RepositoryActions projectId={projectId} repositoryId={repositoryId} viewerRole={user.role} />
      </div>

      <div className="rounded-lg border border-line p-5">
        <p className="mb-3 text-xs uppercase tracking-wide text-ink-soft">Indexing status</p>
        <RepositoryStatusPoller repositoryId={repositoryId} initialStatus={repository.status} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Link 
          href={`/projects/${projectId}/repositories/${repositoryId}/chat`}
          className="group flex flex-col gap-2 rounded-lg border border-line p-5 text-left transition-colors hover:border-primary hover:bg-surface"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
            <MessageSquare className="h-5 w-5" />
          </div>
          <h3 className="font-medium text-ink">Chat</h3>
          <p className="text-sm text-ink-soft">Ask questions about your codebase, search for symbols, and trace dependencies.</p>
        </Link>
        
        <div className="flex flex-col gap-2 rounded-lg border border-dashed border-line p-5 text-left opacity-50">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted text-ink-soft">
            <span className="font-mono text-xs">...</span>
          </div>
          <h3 className="font-medium text-ink">File Explorer & Graphs</h3>
          <p className="text-sm text-ink-soft">Coming soon in Phase 9.</p>
        </div>
      </div>
    </div>
  );
}
