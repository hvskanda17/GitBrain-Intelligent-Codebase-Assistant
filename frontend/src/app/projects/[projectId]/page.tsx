import type { Metadata } from "next";

import { CreateRepositoryDialog } from "@/components/repositories/create-repository-dialog";
import { RepositoryList } from "@/components/repositories/repository-list";
import { apiFetch, requireSession } from "@/lib/api";
import type { Repository } from "@/types/api";

export const metadata: Metadata = { title: "Repositories · GitBrain" };

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const [repositories, user] = await Promise.all([
    apiFetch<Repository[]>(`/api/v1/repositories?project_id=${projectId}`),
    requireSession(),
  ]);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold tracking-tight">Repositories</h1>
          <p className="text-sm text-ink-soft">Everything GitBrain is indexing for this project.</p>
        </div>
        {["admin", "developer"].includes(user.role) && <CreateRepositoryDialog projectId={projectId} />}
      </div>
      <RepositoryList projectId={projectId} repositories={repositories} />
    </div>
  );
}
