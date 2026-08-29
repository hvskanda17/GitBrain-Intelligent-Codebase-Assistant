import Link from "next/link";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Project } from "@/types/api";

export function ProjectList({ projects }: { projects: Project[] }) {
  if (projects.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-line p-10 text-center">
        <p className="text-sm text-ink-soft">No projects yet. Create one to start ingesting a repository.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {projects.map((project) => (
        <Link key={project.id} href={`/projects/${project.id}`}>
          <Card className="transition-colors hover:border-accent">
            <CardHeader>
              <CardTitle>{project.name}</CardTitle>
              <CardDescription className="font-mono text-xs">
                created {new Date(project.created_at).toLocaleDateString()}
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      ))}
    </div>
  );
}
