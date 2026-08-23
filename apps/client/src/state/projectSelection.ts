export type ProjectIdentity = {
  id: string;
};

export function hasProject(projects: ProjectIdentity[], projectId: string | null | undefined): boolean {
  return Boolean(projectId && projects.some((project) => project.id === projectId));
}

export function reconcileProjectSelection(
  projects: ProjectIdentity[],
  selectedProjectId: string | null,
  preferredProjectId: string | null = null,
  allowSingleProjectDefault = true,
): string | null {
  if (hasProject(projects, preferredProjectId)) return preferredProjectId;
  if (hasProject(projects, selectedProjectId)) return selectedProjectId;
  if (allowSingleProjectDefault && projects.length === 1) return projects[0]?.id ?? null;
  return null;
}

export function requireCanonicalCodeProject(
  projects: ProjectIdentity[],
  selectedProjectId: string | null,
): string | null {
  return hasProject(projects, selectedProjectId) ? selectedProjectId : null;
}

export function upsertProject<T extends ProjectIdentity>(projects: T[], project: T): T[] {
  return [project, ...projects.filter((candidate) => candidate.id !== project.id)];
}
