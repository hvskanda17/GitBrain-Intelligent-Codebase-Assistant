"use server";

import { revalidatePath } from "next/cache";

import { apiFetch } from "@/lib/api";
import type { Project } from "@/types/api";

export interface ProjectFormState {
  error?: string;
}

export async function createProjectAction(formData: FormData): Promise<ProjectFormState> {
  const name = formData.get("name");
  if (!name || typeof name !== "string" || name.trim().length === 0) {
    return { error: "Give the project a name." };
  }

  try {
    await apiFetch<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name: name.trim() }),
    });
  } catch (err) {
    return { error: err instanceof Error ? err.message : "Couldn't create the project." };
  }

  revalidatePath("/projects");
  return {};
}
