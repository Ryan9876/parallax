import { authenticatedRequest } from './api';

async function deletionError(response: Response, fallback: string): Promise<Error> {
  try {
    const payload = await response.json() as { detail?: string };
    if (typeof payload.detail === 'string' && payload.detail.trim()) return new Error(payload.detail);
  } catch {
    // Preserve the safe fallback when the API did not return JSON.
  }
  return new Error(fallback);
}

async function deleteResource(path: string, fallback: string): Promise<void> {
  const response = await authenticatedRequest(path, { method: 'DELETE' });
  if (!response.ok) throw await deletionError(response, fallback);
}

export function deleteConversation(conversationId: string): Promise<void> {
  return deleteResource(
    `/v1/conversations/${conversationId}`,
    'Conversation could not be deleted.',
  );
}

export function deleteProject(projectId: string): Promise<void> {
  return deleteResource(
    `/v1/projects/${projectId}`,
    'Project could not be deleted.',
  );
}
