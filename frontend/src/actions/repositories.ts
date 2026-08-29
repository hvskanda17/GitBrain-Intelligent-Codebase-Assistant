"use server";

import { revalidatePath } from "next/cache";

import { apiFetch } from "@/lib/api";
import type { RepositoryCreateResponse, RepositoryStatusResponse } from "@/types/api";

export interface RepositoryFormState {
  error?: string;
}

export async function createRepositoryAction(
  projectId: string,
  formData: FormData,
): Promise<RepositoryFormState> {
  const remoteUrl = formData.get("remoteUrl");
  const branch = formData.get("branch");

  if (!remoteUrl || typeof remoteUrl !== "string" || remoteUrl.trim().length === 0) {
    return { error: "Give it a repository URL." };
  }

  try {
    await apiFetch<RepositoryCreateResponse>("/api/v1/repositories", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        remote_url: remoteUrl.trim(),
        branch: branch && typeof branch === "string" && branch.trim() ? branch.trim() : null,
      }),
    });
  } catch (err) {
    return { error: err instanceof Error ? err.message : "Couldn't start ingestion." };
  }

  revalidatePath(`/projects/${projectId}`);
  return {};
}

export async function reindexRepositoryAction(projectId: string, repositoryId: string): Promise<void> {
  await apiFetch(`/api/v1/repositories/${repositoryId}/reindex`, { method: "POST" });
  revalidatePath(`/projects/${projectId}/repositories/${repositoryId}`);
}

export async function deleteRepositoryAction(projectId: string, repositoryId: string): Promise<void> {
  await apiFetch(`/api/v1/repositories/${repositoryId}`, { method: "DELETE" });
  revalidatePath(`/projects/${projectId}`);
}

export async function getRepositoryStatusAction(repositoryId: string): Promise<RepositoryStatusResponse> {
  return apiFetch<RepositoryStatusResponse>(`/api/v1/repositories/${repositoryId}/status`);
}
