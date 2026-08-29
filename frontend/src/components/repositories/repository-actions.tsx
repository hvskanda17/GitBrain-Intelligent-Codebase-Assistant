"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";

import { deleteRepositoryAction, reindexRepositoryAction } from "@/actions/repositories";
import { Button } from "@/components/ui/button";
import type { UserRole } from "@/types/api";

const CAN_INGEST: UserRole[] = ["admin", "developer"];

export function RepositoryActions({
  projectId,
  repositoryId,
  viewerRole,
}: {
  projectId: string;
  repositoryId: string;
  viewerRole: UserRole;
}) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  if (!CAN_INGEST.includes(viewerRole)) return null;

  return (
    <div className="flex shrink-0 gap-2">
      <Button
        variant="outline"
        size="sm"
        disabled={isPending}
        onClick={() => startTransition(async () => reindexRepositoryAction(projectId, repositoryId))}
      >
        Reindex
      </Button>
      <Button
        variant="destructive"
        size="sm"
        disabled={isPending}
        onClick={() =>
          startTransition(async () => {
            await deleteRepositoryAction(projectId, repositoryId);
            router.push(`/projects/${projectId}`);
          })
        }
      >
        Delete
      </Button>
    </div>
  );
}
