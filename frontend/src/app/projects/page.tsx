import type { Metadata } from "next";

import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import { ProjectList } from "@/components/projects/project-list";
import { apiFetch } from "@/lib/api";
import type { Project } from "@/types/api";

export const metadata: Metadata = { title: "Projects · GitBrain" };

export default async function ProjectsPage() {
  const projects = await apiFetch<Project[]>("/api/v1/projects");

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-ink-soft">Group the repositories you want GitBrain to understand.</p>
        </div>
        <CreateProjectDialog />
      </div>
      <ProjectList projects={projects} />
    </div>
  );
}
