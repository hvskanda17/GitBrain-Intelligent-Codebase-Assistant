import Link from "next/link";

import { StatusTrail } from "@/components/repositories/status-trail";
import { Card, CardContent } from "@/components/ui/card";
import type { Repository } from "@/types/api";

export function RepositoryList({
  projectId,
  repositories,
}: {
  projectId: string;
  repositories: Repository[];
}) {
  if (repositories.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-line p-10 text-center">
        <p className="text-sm text-ink-soft">No repositories yet. Add one to start indexing.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {repositories.map((repo) => (
        <Link key={repo.id} href={`/projects/${projectId}/repositories/${repo.id}`}>
          <Card className="transition-colors hover:border-accent">
            <CardContent className="flex items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <p className="truncate font-mono text-sm">{repo.remote_url}</p>
                <p className="text-xs text-ink-soft">{repo.default_branch}</p>
              </div>
              <StatusTrail status={repo.status} className="shrink-0" />
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
