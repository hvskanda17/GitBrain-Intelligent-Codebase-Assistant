"use client";

import { useEffect, useState } from "react";

import { getRepositoryStatusAction } from "@/actions/repositories";
import { StatusTrail } from "@/components/repositories/status-trail";
import type { IndexingStatus } from "@/types/api";

const TERMINAL_STATUSES: IndexingStatus[] = ["ready", "failed"];
const POLL_INTERVAL_MS = 4000;

export function RepositoryStatusPoller({
  repositoryId,
  initialStatus,
}: {
  repositoryId: string;
  initialStatus: IndexingStatus;
}) {
  const [status, setStatus] = useState<IndexingStatus>(initialStatus);

  useEffect(() => {
    if (TERMINAL_STATUSES.includes(status)) return;

    const interval = setInterval(async () => {
      try {
        const result = await getRepositoryStatusAction(repositoryId);
        setStatus(result.status);
      } catch {
        // transient hiccup -- the next tick tries again
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [repositoryId, status]);

  return <StatusTrail status={status} />;
}
