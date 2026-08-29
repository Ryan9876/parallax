import React from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  api,
  installProjectCompatibilityResolver,
  type ConversationDto,
  type ProjectCompatibilityResolver,
  type ProjectDto,
} from '../lib/api';
import { deleteConversation, deleteProject } from '../lib/deletionApi';
import {
  reconcileProjectSelection,
  requireCanonicalCodeProject,
  upsertProject,
} from '../state/projectSelection';
import { palette } from '../theme';

type PendingSelection = {
  promise: Promise<string>;
  resolve(projectId: string): void;
};

type ActiveBinding = {
  conversationId: string | null;
  mode: ConversationDto['mode'];
  projectId: string | null;
  status: ConversationDto['project_binding_status'];
};

type ProjectCompatibilityContextValue = {
  project: ProjectDto | null;
  historical: boolean;
  openProjectSelector(): void;
};

const ProjectCompatibilityContext = React.createContext<ProjectCompatibilityContextValue>({
  project: null,
  historical: false,
  openProjectSelector: () => undefined,
});

export function useProjectCompatibility(): ProjectCompatibilityContextValue {
  return React.useContext(ProjectCompatibilityContext);
}

const REPOSITORY_SHORTHAND_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?\/[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?$/;

function messageFor(cause: unknown, fallback: string): string {
  return cause instanceof Error && cause.message.trim() ? cause.message : fallback;
}

function normalizeRepositoryInput(value: string): string {
  const candidate = value.trim();
  if (!candidate) return '';
  return REPOSITORY_SHORTHAND_PATTERN.test(candidate) ? `github:${candidate}` : candidate;
}

function projectReference(project: ProjectDto): string {
  const reference = project.repository_ref?.trim();
  if (!reference) return 'No repository linked';
  if (reference.startsWith('github:')) return `GitHub · ${reference.slice('github:'.length)}`;
  return `Repository · ${reference}`;
}

export function ProjectCompatibilityGate({ children }: { children: React.ReactNode }) {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const [projects, setProjects] = React.useState<ProjectDto[]>([]);
  const [conversations, setConversations] = React.useState<ConversationDto[]>([]);
  const [selectedProjectId, setSelectedProjectId] = React.useState<string | null>(null);
  const [loaded, setLoaded] = React.useState(false);
  const [open, setOpen] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [historyBusy, setHistoryBusy] = React.useState(false);
  const [error, setError] = React.useState('');
  const [projectName, setProjectName] = React.useState('');
  const [repositoryRef, setRepositoryRef] = React.useState('');
  const [confirmProjectId, setConfirmProjectId] = React.useState<string | null>(null);
  const [confirmConversationId, setConfirmConversationId] = React.useState<string | null>(null);
  const [deletingKey, setDeletingKey] = React.useState<string | null>(null);
  const [activeBinding, setActiveBinding] = React.useState<ActiveBinding>({
    conversationId: null,
    mode: 'reason',
    projectId: null,
    status: 'HISTORICAL_UNBOUND',
  });

  const projectsRef = React.useRef<ProjectDto[]>([]);
  const selectedRef = React.useRef<string | null>(null);
  const loadedRef = React.useRef(false);
  const activeBindingRef = React.useRef(activeBinding);
  const pendingRef = React.useRef<PendingSelection | null>(null);

  const commitProjects = React.useCallback((nextProjects: ProjectDto[], preferredProjectId: string | null = null, allowSingleProjectDefault = true) => {
    projectsRef.current = nextProjects;
    setProjects(nextProjects);
    loadedRef.current = true;
    setLoaded(true);
    const nextSelection = reconcileProjectSelection(
      nextProjects,
      selectedRef.current,
      preferredProjectId,
      allowSingleProjectDefault,
    );
    selectedRef.current = nextSelection;
    setSelectedProjectId(nextSelection);
    return nextSelection;
  }, []);

  const loadProjects = React.useCallback(async (preferredProjectId: string | null = null, allowSingleProjectDefault = true) => {
    setBusy(true);
    try {
      const nextProjects = await api.listProjects();
      const nextSelection = commitProjects(nextProjects, preferredProjectId, allowSingleProjectDefault);
      setError('');
      return { projects: nextProjects, selectedProjectId: nextSelection };
    } catch (cause) {
      loadedRef.current = false;
      setLoaded(false);
      setError(messageFor(cause, 'Projects are unavailable.'));
      throw cause;
    } finally {
      setBusy(false);
    }
  }, [commitProjects]);

  const loadConversationHistory = React.useCallback(async () => {
    setHistoryBusy(true);
    try {
      setConversations(await api.listConversations());
    } catch (cause) {
      setError(messageFor(cause, 'Conversation history is unavailable.'));
    } finally {
      setHistoryBusy(false);
    }
  }, []);

  const settleSelection = React.useCallback((projectId: string) => {
    if (!projectsRef.current.some((project) => project.id === projectId)) return;
    selectedRef.current = projectId;
    setSelectedProjectId(projectId);
    setError('');
    setOpen(false);
    setCreating(false);
    const pending = pendingRef.current;
    pendingRef.current = null;
    pending?.resolve(projectId);
  }, []);

  const requestSelection = React.useCallback(async (): Promise<string> => {
    let availableProjects = projectsRef.current;
    let candidate = requireCanonicalCodeProject(availableProjects, selectedRef.current);

    if (!loadedRef.current || !candidate) {
      const refreshed = await loadProjects(selectedRef.current, true);
      availableProjects = refreshed.projects;
      candidate = requireCanonicalCodeProject(availableProjects, refreshed.selectedProjectId);
    }

    if (candidate) return candidate;
    if (pendingRef.current) return pendingRef.current.promise;

    setCreating(availableProjects.length === 0);
    setOpen(true);
    const pending: Partial<PendingSelection> = {};
    pending.promise = new Promise<string>((resolve) => {
      pending.resolve = resolve;
    });
    pendingRef.current = pending as PendingSelection;
    return pending.promise;
  }, [loadProjects]);

  const invalidateProject = React.useCallback((projectId: string, detail: string) => {
    if (selectedRef.current === projectId) {
      selectedRef.current = null;
      setSelectedProjectId(null);
    }
    loadedRef.current = false;
    setLoaded(false);
    setError(detail || 'That project is no longer available.');
    setOpen(true);
    setCreating(false);
  }, []);

  const observeConversation = React.useCallback((conversation: ConversationDto) => {
    const nextBinding: ActiveBinding = {
      conversationId: conversation.id,
      mode: conversation.mode,
      projectId: conversation.project_id,
      status: conversation.project_binding_status,
    };
    activeBindingRef.current = nextBinding;
    setActiveBinding(nextBinding);

    if (conversation.mode === 'code' && conversation.project_binding_status === 'HISTORICAL_UNBOUND') {
      selectedRef.current = null;
      setSelectedProjectId(null);
      return;
    }

    if (
      conversation.mode === 'code'
      && conversation.project_binding_status === 'PROJECT_BOUND'
      && conversation.project_id
      && projectsRef.current.some((project) => project.id === conversation.project_id)
    ) {
      selectedRef.current = conversation.project_id;
      setSelectedProjectId(conversation.project_id);
    }
  }, []);

  React.useEffect(() => {
    const resolver: ProjectCompatibilityResolver = {
      resolveCodeProject: requestSelection,
      invalidateProject,
      observeConversation,
    };
    return installProjectCompatibilityResolver(resolver);
  }, [invalidateProject, observeConversation, requestSelection]);

  React.useEffect(() => {
    if (!compact || loadedRef.current) return;
    if (activeBinding.mode !== 'code' || activeBinding.status !== 'PROJECT_BOUND' || !activeBinding.projectId) return;
    void loadProjects(activeBinding.projectId, true).catch(() => undefined);
  }, [activeBinding.mode, activeBinding.projectId, activeBinding.status, compact, loadProjects]);

  const openSelector = React.useCallback(async () => {
    setOpen(true);
    setCreating(false);
    setConfirmProjectId(null);
    setConfirmConversationId(null);
    const preferred = activeBindingRef.current.status === 'PROJECT_BOUND'
      ? activeBindingRef.current.projectId
      : null;
    const tasks: Promise<unknown>[] = [loadConversationHistory()];
    if (!loadedRef.current) {
      tasks.push(loadProjects(preferred, activeBindingRef.current.status !== 'HISTORICAL_UNBOUND'));
    }
    await Promise.allSettled(tasks);
  }, [loadConversationHistory, loadProjects]);

  const createProject = React.useCallback(async () => {
    const name = projectName.trim();
    const repository = normalizeRepositoryInput(repositoryRef);
    if (!name) {
      setError('Enter a project name.');
      return;
    }

    setBusy(true);
    try {
      const created = await api.createProject({
        name,
        ...(repository ? { repository_ref: repository } : {}),
      });
      const nextProjects = upsertProject(projectsRef.current, created);
      projectsRef.current = nextProjects;
      setProjects(nextProjects);
      loadedRef.current = true;
      setLoaded(true);
      setProjectName('');
      setRepositoryRef('');
      settleSelection(created.id);
    } catch (cause) {
      setError(messageFor(cause, 'Project could not be created.'));
    } finally {
      setBusy(false);
    }
  }, [projectName, repositoryRef, settleSelection]);

  const removeProject = React.useCallback(async (project: ProjectDto) => {
    if (deletingKey || activeBindingRef.current.projectId === project.id) return;
    setDeletingKey(`project:${project.id}`);
    setError('');
    try {
      await deleteProject(project.id);
      const nextProjects = projectsRef.current.filter((item) => item.id !== project.id);
      commitProjects(nextProjects, null, true);
      setConversations((current) => current.filter((conversation) => conversation.project_id !== project.id));
      setConfirmProjectId(null);
    } catch (cause) {
      setError(messageFor(cause, 'Project could not be deleted.'));
    } finally {
      setDeletingKey(null);
    }
  }, [commitProjects, deletingKey]);

  const removeConversation = React.useCallback(async (conversation: ConversationDto) => {
    if (deletingKey || activeBindingRef.current.conversationId === conversation.id) return;
    setDeletingKey(`conversation:${conversation.id}`);
    setError('');
    try {
      await deleteConversation(conversation.id);
      setConversations((current) => current.filter((item) => item.id !== conversation.id));
      setConfirmConversationId(null);
    } catch (cause) {
      setError(messageFor(cause, 'Conversation could not be deleted.'));
    } finally {
      setDeletingKey(null);
    }
  }, [deletingKey]);

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;
  const activeProject = projects.find((project) => project.id === activeBinding.projectId) ?? null;
  const historical = activeBinding.mode === 'code' && activeBinding.status === 'HISTORICAL_UNBOUND';
  const boundCode = activeBinding.mode === 'code' && activeBinding.status === 'PROJECT_BOUND';
  const showBindingPill = historical || boundCode;
  const contextProject = activeProject ?? selectedProject;
  const contextValue = React.useMemo<ProjectCompatibilityContextValue>(() => ({
    project: contextProject,
    historical,
    openProjectSelector: () => { void openSelector(); },
  }), [contextProject, historical, openSelector]);

  return (
    <ProjectCompatibilityContext.Provider value={contextValue}>
      <View style={styles.root}>
        {children}

        {showBindingPill && !compact ? (
          <TouchableOpacity
            accessibilityRole={historical ? undefined : 'button'}
            accessibilityLabel={historical ? 'Older Build conversation without a project' : 'Change project for future builds'}
            disabled={historical}
            onPress={() => void openSelector()}
            style={[styles.bindingPill, styles.bindingPillDesktop]}
          >
            <View style={[styles.bindingDot, historical ? styles.bindingDotHistorical : styles.bindingDotBound]} />
            <Text numberOfLines={1} style={historical ? styles.bindingHistoricalText : styles.bindingText}>
              {historical
                ? 'OLDER BUILD · NO PROJECT'
                : `PROJECT · ${activeProject?.name ?? selectedProject?.name ?? 'SELECTED'}`}
            </Text>
          </TouchableOpacity>
        ) : null}

        {open ? (
          <View accessibilityViewIsModal style={[styles.selectorLayer, compact && styles.selectorLayerCompact]}>
            <View style={[styles.selectorPanel, compact && styles.selectorPanelCompact]}>
              <View style={styles.selectorHeader}>
                <View style={styles.selectorHeaderCopy}>
                  <Text style={[styles.kicker, compact && styles.kickerCompact]}>{compact ? 'PROJECT' : 'BUILD · PROJECT'}</Text>
                  <Text style={[styles.selectorTitle, compact && styles.selectorTitleCompact]}>{pendingRef.current ? 'Choose a project for Build' : compact ? 'Projects & history' : 'Projects & conversation history'}</Text>
                  <Text style={[styles.selectorCopy, compact && styles.selectorCopyCompact]}>Choose the project for this build, or remove old Parallax history. Deleting here does not delete anything in GitHub or Vercel, and technical records are kept.</Text>
                </View>
                {!pendingRef.current ? (
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel="Close project selector" onPress={() => setOpen(false)} style={styles.closeButton}>
                    <Text style={[styles.closeText, compact && styles.closeTextCompact]}>×</Text>
                  </TouchableOpacity>
                ) : null}
              </View>

              {error ? <Text accessibilityLiveRegion="polite" style={styles.errorText}>{error}</Text> : null}

              {busy && !loaded ? <ActivityIndicator color={compact ? palette.teal600 : palette.cyan} size="small" style={styles.spinner} /> : null}

              {!creating && projects.length > 0 ? (
                <View style={styles.managementSection}>
                  <Text style={[styles.managementLabel, compact && styles.managementLabelCompact]}>PROJECTS</Text>
                  <ScrollView style={styles.projectList} contentContainerStyle={styles.projectListContent} keyboardShouldPersistTaps="handled">
                    {projects.map((project) => {
                      const selected = project.id === selectedProjectId;
                      const current = activeBinding.projectId === project.id;
                      const confirming = confirmProjectId === project.id;
                      const deleting = deletingKey === `project:${project.id}`;
                      return (
                        <View key={project.id} style={[styles.projectRow, compact && styles.projectRowCompact, selected && styles.projectRowSelected, compact && selected && styles.projectRowSelectedCompact]}>
                          <View style={styles.managementMainRow}>
                            <TouchableOpacity
                              accessibilityRole="button"
                              accessibilityLabel={`Select project ${project.name}`}
                              accessibilityState={{ selected, disabled: busy }}
                              disabled={busy}
                              onPress={() => settleSelection(project.id)}
                              style={styles.projectSelectButton}
                            >
                              <View style={styles.projectCopy}>
                                <Text numberOfLines={1} style={[styles.projectName, compact && styles.projectNameCompact]}>{project.name}</Text>
                                <Text numberOfLines={1} style={[styles.projectMeta, compact && styles.projectMetaCompact]}>{projectReference(project)}</Text>
                              </View>
                              <Text style={selected ? [styles.selectedLabel, compact && styles.selectedLabelCompact] : [styles.selectLabel, compact && styles.selectLabelCompact]}>{selected ? 'Selected' : 'Use'}</Text>
                            </TouchableOpacity>
                            {!current && !pendingRef.current ? (
                              <TouchableOpacity
                                accessibilityRole="button"
                                accessibilityLabel={`Delete project ${project.name}`}
                                disabled={Boolean(deletingKey)}
                                onPress={() => { setError(''); setConfirmProjectId(project.id); setConfirmConversationId(null); }}
                                style={[styles.smallDeleteButton, compact && styles.smallDeleteButtonCompact]}
                              >
                                <Text style={[styles.smallDeleteText, compact && styles.smallDeleteTextCompact]}>Delete</Text>
                              </TouchableOpacity>
                            ) : null}
                          </View>
                          {confirming ? (
                            <View style={[styles.confirmPanel, compact && styles.confirmPanelCompact]} accessibilityLiveRegion="polite">
                              <Text style={[styles.confirmCopy, compact && styles.confirmCopyCompact]}>Delete this project from Parallax? Its conversations will be removed from active history. This will not delete anything in GitHub or Vercel, and technical records are kept.</Text>
                              <View style={styles.confirmActions}>
                                <TouchableOpacity accessibilityRole="button" accessibilityLabel="Cancel project deletion" disabled={deleting} onPress={() => setConfirmProjectId(null)} style={[styles.confirmCancel, compact && styles.confirmCancelCompact]}>
                                  <Text style={[styles.confirmCancelText, compact && styles.confirmCancelTextCompact]}>Cancel</Text>
                                </TouchableOpacity>
                                <TouchableOpacity accessibilityRole="button" accessibilityLabel={`Confirm delete project ${project.name}`} disabled={deleting} onPress={() => void removeProject(project)} style={[styles.confirmDelete, compact && styles.confirmDeleteCompact]}>
                                  <Text style={styles.confirmDeleteText}>{deleting ? 'Deleting…' : 'Delete project'}</Text>
                                </TouchableOpacity>
                              </View>
                            </View>
                          ) : null}
                        </View>
                      );
                    })}
                  </ScrollView>
                </View>
              ) : null}

              {!creating && (historyBusy || conversations.length > 0) ? (
                <View style={styles.managementSection}>
                  <View style={styles.managementHeadingRow}>
                    <Text style={[styles.managementLabel, compact && styles.managementLabelCompact]}>RECENT CONVERSATIONS</Text>
                    {historyBusy ? <ActivityIndicator size="small" color={compact ? palette.teal600 : palette.violet} /> : null}
                  </View>
                  <ScrollView style={styles.historyList} contentContainerStyle={styles.historyListContent} keyboardShouldPersistTaps="handled">
                    {conversations.slice(0, 12).map((conversation) => {
                      const current = activeBinding.conversationId === conversation.id;
                      const confirming = confirmConversationId === conversation.id;
                      const deleting = deletingKey === `conversation:${conversation.id}`;
                      return (
                        <View key={conversation.id} style={[styles.historyRow, compact && styles.historyRowCompact]}>
                          <View style={styles.managementMainRow}>
                            <View style={styles.historyCopy}>
                              <Text numberOfLines={1} style={[styles.historyTitle, compact && styles.historyTitleCompact]}>{conversation.title}</Text>
                              <Text numberOfLines={1} style={[styles.historyMeta, compact && styles.historyMetaCompact]}>{conversation.mode === 'code' ? 'Build' : 'Ask'}{conversation.project_id ? ' · Project' : ''}</Text>
                            </View>
                            {current ? (
                              <Text style={[styles.currentLabel, compact && styles.currentLabelCompact]}>Current</Text>
                            ) : (
                              <TouchableOpacity
                                accessibilityRole="button"
                                accessibilityLabel={`Delete conversation ${conversation.title}`}
                                disabled={Boolean(deletingKey)}
                                onPress={() => { setError(''); setConfirmConversationId(conversation.id); setConfirmProjectId(null); }}
                                style={[styles.smallDeleteButton, compact && styles.smallDeleteButtonCompact]}
                              >
                                <Text style={[styles.smallDeleteText, compact && styles.smallDeleteTextCompact]}>Delete</Text>
                              </TouchableOpacity>
                            )}
                          </View>
                          {confirming ? (
                            <View style={[styles.confirmPanel, compact && styles.confirmPanelCompact]} accessibilityLiveRegion="polite">
                              <Text style={[styles.confirmCopy, compact && styles.confirmCopyCompact]}>Delete this conversation from active history? Technical records are kept.</Text>
                              <View style={styles.confirmActions}>
                                <TouchableOpacity accessibilityRole="button" accessibilityLabel="Cancel conversation deletion" disabled={deleting} onPress={() => setConfirmConversationId(null)} style={[styles.confirmCancel, compact && styles.confirmCancelCompact]}>
                                  <Text style={[styles.confirmCancelText, compact && styles.confirmCancelTextCompact]}>Cancel</Text>
                                </TouchableOpacity>
                                <TouchableOpacity accessibilityRole="button" accessibilityLabel={`Confirm delete conversation ${conversation.title}`} disabled={deleting} onPress={() => void removeConversation(conversation)} style={[styles.confirmDelete, compact && styles.confirmDeleteCompact]}>
                                  <Text style={styles.confirmDeleteText}>{deleting ? 'Deleting…' : 'Delete'}</Text>
                                </TouchableOpacity>
                              </View>
                            </View>
                          ) : null}
                        </View>
                      );
                    })}
                  </ScrollView>
                </View>
              ) : null}

              {creating ? (
                <View style={styles.createForm}>
                  <TextInput
                    accessibilityLabel="Project name"
                    value={projectName}
                    onChangeText={setProjectName}
                    placeholder="Project name"
                    placeholderTextColor={palette.muted}
                    style={[styles.input, compact && styles.inputCompact]}
                    maxLength={120}
                  />
                  <TextInput
                    accessibilityLabel="Repository (optional)"
                    autoCapitalize="none"
                    autoCorrect={false}
                    value={repositoryRef}
                    onChangeText={setRepositoryRef}
                    placeholder="Optional · owner/repository"
                    placeholderTextColor={palette.muted}
                    style={[styles.input, compact && styles.inputCompact]}
                    maxLength={240}
                  />
                  <View style={[styles.formActions, compact && styles.formActionsCompact]}>
                    {projects.length > 0 ? (
                      <TouchableOpacity accessibilityRole="button" accessibilityLabel="Cancel project creation" disabled={busy} onPress={() => setCreating(false)} style={[styles.secondaryButton, compact && styles.secondaryButtonCompact]}>
                        <Text style={[styles.secondaryButtonText, compact && styles.secondaryButtonTextCompact]}>Back</Text>
                      </TouchableOpacity>
                    ) : null}
                    <TouchableOpacity accessibilityRole="button" accessibilityLabel="Create project" disabled={busy} onPress={() => void createProject()} style={[styles.primaryButton, compact && styles.primaryButtonCompact]}>
                      <Text style={[styles.primaryButtonText, compact && styles.primaryButtonTextCompact]}>{busy ? 'Creating…' : 'Create project'}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ) : (
                <View style={[styles.selectorActions, compact && styles.selectorActionsCompact]}>
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel="Refresh projects and conversation history" disabled={busy || historyBusy} onPress={() => { void loadProjects(selectedRef.current, true).catch(() => undefined); void loadConversationHistory(); }} style={[styles.secondaryButton, compact && styles.secondaryButtonCompact]}>
                    <Text style={[styles.secondaryButtonText, compact && styles.secondaryButtonTextCompact]}>{busy || historyBusy ? 'Refreshing…' : 'Refresh'}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel="New project" disabled={busy} onPress={() => { setError(''); setCreating(true); }} style={[styles.primaryButton, compact && styles.primaryButtonCompact]}>
                    <Text style={[styles.primaryButtonText, compact && styles.primaryButtonTextCompact]}>New project</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          </View>
        ) : null}
      </View>
    </ProjectCompatibilityContext.Provider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, minWidth: 0, minHeight: 0 },
  bindingPill: {
    position: 'absolute',
    zIndex: 42,
    minHeight: 44,
    maxWidth: 280,
    paddingHorizontal: 12,
    borderRadius: 22,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    backgroundColor: 'rgba(11,16,25,0.92)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(167,151,255,0.18)',
  },
  bindingPillDesktop: { top: 16, right: 150 },
  bindingDot: { width: 7, height: 7, borderRadius: 4 },
  bindingDotBound: { backgroundColor: palette.sage },
  bindingDotHistorical: { backgroundColor: palette.warning },
  bindingText: { flexShrink: 1, color: palette.textSecondary, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.4 },
  bindingHistoricalText: { flexShrink: 1, color: palette.warning, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.35 },
  selectorLayer: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    zIndex: 80,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    backgroundColor: 'rgba(5,7,13,0.64)',
  },
  selectorLayerCompact: { backgroundColor: 'rgba(23,32,36,0.42)', padding: 10 },
  selectorPanel: {
    width: '100%',
    maxWidth: 560,
    maxHeight: '90%',
    padding: 24,
    borderRadius: 24,
    backgroundColor: 'rgba(17,21,37,0.97)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(167,151,255,0.24)',
    shadowColor: '#8F63D8',
    shadowOpacity: 0.18,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 14 },
  },
  selectorPanelCompact: { padding: 18, borderRadius: 22, backgroundColor: palette.cream100, borderColor: palette.border, shadowColor: '#564B38', shadowOpacity: 0.12, shadowRadius: 22 },
  selectorHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  selectorHeaderCopy: { flex: 1, minWidth: 0 },
  kicker: { color: palette.violet, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.8 },
  kickerCompact: { color: palette.olive700 },
  selectorTitle: { color: palette.text, fontSize: 22, lineHeight: 28, fontWeight: '600', letterSpacing: -0.35, marginTop: 5 },
  selectorTitleCompact: { color: palette.charcoal950, fontSize: 22, lineHeight: 27 },
  selectorCopy: { color: palette.textSecondary, fontSize: 14, lineHeight: 21, marginTop: 7 },
  selectorCopyCompact: { color: palette.charcoal600, fontSize: 16, lineHeight: 24 },
  closeButton: { width: 44, height: 44, marginTop: -8, marginRight: -8, alignItems: 'center', justifyContent: 'center', borderRadius: 22 },
  closeText: { color: palette.textSecondary, fontSize: 24, lineHeight: 26 },
  closeTextCompact: { color: palette.charcoal600 },
  errorText: { color: palette.danger, fontSize: 14, lineHeight: 20, marginTop: 13 },
  spinner: { marginTop: 20 },
  managementSection: { marginTop: 16 },
  managementHeadingRow: { minHeight: 24, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  managementLabel: { color: palette.muted, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.6 },
  managementLabelCompact: { color: palette.olive700 },
  projectList: { maxHeight: 210, marginTop: 7 },
  projectListContent: { gap: 7 },
  projectRow: {
    minHeight: 60,
    paddingHorizontal: 9,
    paddingVertical: 8,
    borderRadius: 15,
    backgroundColor: palette.glassSoft,
  },
  projectRowCompact: { minHeight: 60, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  projectRowSelected: { backgroundColor: palette.indigoWash },
  projectRowSelectedCompact: { backgroundColor: palette.teal100, borderColor: 'rgba(0,132,135,0.22)' },
  managementMainRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  projectSelectButton: { flex: 1, minWidth: 0, minHeight: 44, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 4 },
  projectCopy: { flex: 1, minWidth: 0 },
  projectName: { color: palette.text, fontSize: 15, lineHeight: 20, fontWeight: '600' },
  projectNameCompact: { color: palette.charcoal950 },
  projectMeta: { color: palette.muted, fontSize: 12, lineHeight: 16, marginTop: 4 },
  projectMetaCompact: { color: palette.charcoal450 },
  selectLabel: { color: palette.violet, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  selectLabelCompact: { color: palette.teal700 },
  selectedLabel: { color: palette.sage, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  selectedLabelCompact: { color: palette.olive700 },
  smallDeleteButton: { minHeight: 44, paddingHorizontal: 10, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(196,74,27,0.14)' },
  smallDeleteButtonCompact: { backgroundColor: palette.rust100 },
  smallDeleteText: { color: '#E6A78E', fontSize: 13, lineHeight: 17, fontWeight: '800' },
  smallDeleteTextCompact: { color: palette.rust700 },
  historyList: { maxHeight: 190, marginTop: 7 },
  historyListContent: { gap: 6 },
  historyRow: { minHeight: 58, paddingHorizontal: 10, paddingVertical: 8, borderRadius: 13, backgroundColor: palette.glassSoft },
  historyRowCompact: { backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  historyCopy: { flex: 1, minWidth: 0 },
  historyTitle: { color: palette.text, fontSize: 14, lineHeight: 19, fontWeight: '600' },
  historyTitleCompact: { color: palette.charcoal950 },
  historyMeta: { color: palette.muted, fontSize: 12, lineHeight: 16, marginTop: 3 },
  historyMetaCompact: { color: palette.charcoal450 },
  currentLabel: { color: palette.sage, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  currentLabelCompact: { color: palette.olive700 },
  confirmPanel: { marginTop: 7, padding: 12, borderRadius: 12, backgroundColor: 'rgba(196,74,27,0.12)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(196,74,27,0.2)' },
  confirmPanelCompact: { backgroundColor: palette.rust100, borderColor: 'rgba(168,59,23,0.18)' },
  confirmCopy: { color: palette.textSecondary, fontSize: 14, lineHeight: 21 },
  confirmCopyCompact: { color: palette.charcoal600, fontSize: 15, lineHeight: 22 },
  confirmActions: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 7, marginTop: 10 },
  confirmCancel: { minHeight: 44, paddingHorizontal: 12, borderRadius: 10, alignItems: 'center', justifyContent: 'center', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong },
  confirmCancelCompact: { backgroundColor: palette.ivory50, borderColor: palette.border },
  confirmCancelText: { color: palette.textSecondary, fontSize: 13, lineHeight: 17, fontWeight: '800' },
  confirmCancelTextCompact: { color: palette.charcoal600 },
  confirmDelete: { minHeight: 44, paddingHorizontal: 12, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust600 },
  confirmDeleteCompact: { backgroundColor: palette.rust600 },
  confirmDeleteText: { color: palette.ivory50, fontSize: 13, lineHeight: 17, fontWeight: '800' },
  createForm: { gap: 9, marginTop: 17 },
  input: {
    minHeight: 48,
    paddingHorizontal: 13,
    paddingVertical: 10,
    borderRadius: 14,
    color: palette.text,
    fontSize: 16,
    backgroundColor: palette.surfaceRaised,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.border,
  },
  inputCompact: { color: palette.charcoal950, backgroundColor: palette.ivory50 },
  formActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 4 },
  formActionsCompact: { flexWrap: 'wrap' },
  selectorActions: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, marginTop: 16 },
  selectorActionsCompact: { flexWrap: 'wrap' },
  secondaryButton: {
    minHeight: 44,
    paddingHorizontal: 15,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 13,
    backgroundColor: palette.glassSoft,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.borderStrong,
  },
  secondaryButtonCompact: { backgroundColor: palette.ivory50, borderColor: palette.border },
  secondaryButtonText: { color: palette.textSecondary, fontSize: 14, lineHeight: 18, fontWeight: '800' },
  secondaryButtonTextCompact: { color: palette.charcoal600 },
  primaryButton: {
    minHeight: 44,
    paddingHorizontal: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 13,
    backgroundColor: palette.violetDeep,
  },
  primaryButtonCompact: { backgroundColor: palette.rust600 },
  primaryButtonText: { color: palette.text, fontSize: 14, lineHeight: 18, fontWeight: '800' },
  primaryButtonTextCompact: { color: palette.ivory50 },
});