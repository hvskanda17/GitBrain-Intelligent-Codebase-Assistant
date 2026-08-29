import { cn } from "@/lib/utils";
import type { IndexingStatus } from "@/types/api";

const STAGES: IndexingStatus[] = ["cloning", "parsing", "analyzing", "embedding", "ready"];

const STAGE_LABELS: Record<IndexingStatus, string> = {
  pending: "Queued",
  cloning: "Cloning",
  parsing: "Parsing",
  analyzing: "Analyzing",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

/**
 * Renders IndexingStatus as its actual position in the ingestion pipeline (see
 * docs/02_LOW_LEVEL_DESIGN.md from Phase 1) rather than an isolated colored badge --
 * the order is real information here, not decoration.
 */
export function StatusTrail({ status, className }: { status: IndexingStatus; className?: string }) {
  if (status === "failed") {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <span className="h-1.5 w-8 rounded-full bg-danger" />
        <span className="font-mono text-xs text-danger">failed</span>
      </div>
    );
  }

  const currentIndex = status === "pending" ? -1 : STAGES.indexOf(status);

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="flex items-center gap-1">
        {STAGES.map((stage, i) => (
          <span
            key={stage}
            title={STAGE_LABELS[stage]}
            className={cn(
              "h-1.5 w-5 rounded-full transition-colors",
              i < currentIndex && "bg-accent",
              i === currentIndex && stage !== "ready" && "animate-pulse bg-accent",
              stage === "ready" && currentIndex === STAGES.length - 1 && "bg-success",
              i > currentIndex && "bg-line",
            )}
          />
        ))}
      </div>
      <span className="font-mono text-xs text-ink-soft">{STAGE_LABELS[status]}</span>
    </div>
  );
}
