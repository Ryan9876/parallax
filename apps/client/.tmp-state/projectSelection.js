"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.hasProject = hasProject;
exports.reconcileProjectSelection = reconcileProjectSelection;
exports.requireCanonicalCodeProject = requireCanonicalCodeProject;
exports.upsertProject = upsertProject;
function hasProject(projects, projectId) {
    return Boolean(projectId && projects.some((project) => project.id === projectId));
}
function reconcileProjectSelection(projects, selectedProjectId, preferredProjectId = null, allowSingleProjectDefault = true) {
    if (hasProject(projects, preferredProjectId))
        return preferredProjectId;
    if (hasProject(projects, selectedProjectId))
        return selectedProjectId;
    if (allowSingleProjectDefault && projects.length === 1)
        return projects[0]?.id ?? null;
    return null;
}
function requireCanonicalCodeProject(projects, selectedProjectId) {
    return hasProject(projects, selectedProjectId) ? selectedProjectId : null;
}
function upsertProject(projects, project) {
    return [project, ...projects.filter((candidate) => candidate.id !== project.id)];
}
