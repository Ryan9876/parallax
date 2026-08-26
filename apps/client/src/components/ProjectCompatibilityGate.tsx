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

export function ProjectCompatibilityGate({ children }: { children: React.ReactNode }) {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const [projects, setProjects] = React.useState<ProjectDto[]>([]);
  const [selectedProjectId, setSelectedProjectId] = React.useState<string | null>(null);
  const [loaded, setLoaded] = React.useState(false);
  const [open, setOpen] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');
  const [projectName, setProjectName] = React.useState('');
  const [repositoryRef, setRepositoryRef] = React.useState('');
  const [activeBinding, setActiveBinding] = React.useState<ActiveBinding>({
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
    setError(detail || 'That Project is no longer available.');
    setOpen(true);
    setCreating(false);
  }, []);

  const observeConversation = React.useCallback((conversation: ConversationDto) => {
    const nextBinding: ActiveBinding = {
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
    if (loadedRef.current) return;
    try {
      const preferred = activeBindingRef.current.status === 'PROJECT_BOUND'
        ? activeBindingRef.current.projectId
        : null;
      await loadProjects(preferred, activeBindingRef.current.status !== 'HISTORICAL_UNBOUND');
    } catch {
      // Error state is rendered in the selector. Manual refresh remains available.
    }
  }, [loadProjects]);

  const createProject = React.useCallback(async () => {
    const name = projectName.trim();
    const repository = normalizeRepositoryInput(repositoryRef);
    if (!name) {
      setError('Enter a Project name.');
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
            accessibilityLabel={historical ? 'Historical Code conversation without Project binding' : 'Choose Project for future Code work'}
            disabled={historical}
            onPress={() => void openSelector()}
            style={[styles.bindingPill, styles.bindingPillDesktop]}
          >
            <View style={[styles.bindingDot, historical ? styles.bindingDotHistorical : styles.bindingDotBound]} />
            <Text numberOfLines={1} style={historical ? styles.bindingHistoricalText : styles.bindingText}>
              {historical
                ? 'HISTORICAL CODE · UNBOUND'
                : `PROJECT · ${activeProject?.name ?? selectedProject?.name ?? 'BOUND'}`}
            </Text>
          </TouchableOpacity>
        ) : null}

        {open ? (
          <View accessibilityViewIsModal style={[styles.selectorLayer, compact && styles.selectorLayerCompact]}>
            <View style={[styles.selectorPanel, compact && styles.selectorPanelCompact]}>
              <View style={styles.selectorHeader}>
                <View style={styles.selectorHeaderCopy}>
                  <Text style={[styles.kicker, compact && styles.kickerCompact]}>{compact ? 'PROJECT' : 'CODE · PROJECT'}</Text>
                  <Text style={[styles.selectorTitle, compact && styles.selectorTitleCompact]}>{pendingRef.current ? (compact ? 'Choose a project for Build' : 'Choose a Project for Code') : compact ? 'Choose project' : 'Project for future Code work'}</Text>
                  <Text style={[styles.selectorCopy, compact && styles.selectorCopyCompact]}>{compact ? 'Choose where future Build work belongs. Parallax keeps the canonical Project binding protected.' : 'Only the canonical Project ID is used. Workspace and repository metadata do not grant execution authority.'}</Text>
                </View>
                {!pendingRef.current ? (
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel="Close Project selector" onPress={() => setOpen(false)} style={styles.closeButton}>
                    <Text style={[styles.closeText, compact && styles.closeTextCompact]}>×</Text>
                  </TouchableOpacity>
                ) : null}
              </View>

              {error ? <Text accessibilityLiveRegion="polite" style={styles.errorText}>{error}</Text> : null}

              {busy && !loaded ? <ActivityIndicator color={compact ? palette.teal600 : palette.cyan} size="small" style={styles.spinner} /> : null}

              {!creating && projects.length > 0 ? (
                <ScrollView style={styles.projectList} contentContainerStyle={styles.projectListContent} keyboardShouldPersistTaps="handled">
                  {projects.map((project) => {
                    const selected = project.id === selectedProjectId;
                    return (
                      <TouchableOpacity
                        key={project.id}
                        accessibilityRole="button"
                        accessibilityLabel={`Select Project ${project.name}`}
                        accessibilityState={{ selected, disabled: busy }}
                        disabled={busy}
                        onPress={() => settleSelection(project.id)}
                        style={[styles.projectRow, compact && styles.projectRowCompact, selected && styles.projectRowSelected, compact && selected && styles.projectRowSelectedCompact]}
                      >
                        <View style={styles.projectCopy}>
                          <Text numberOfLines={1} style={[styles.projectName, compact && styles.projectNameCompact]}>{project.name}</Text>
                          <Text numberOfLines={1} style={[styles.projectMeta, compact && styles.projectMetaCompact]}>{project.repository_ref ?? project.slug}</Text>
                        </View>
                        <Text style={selected ? [styles.selectedLabel, compact && styles.selectedLabelCompact] : [styles.selectLabel, compact && styles.selectLabelCompact]}>{selected ? 'SELECTED' : 'USE'}</Text>
                      </TouchableOpacity>
                    );
                  })}
                </ScrollView>
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
                    accessibilityLabel="Repository identity"
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
                      <TouchableOpacity accessibilityRole="button" accessibilityLabel="Cancel Project creation" disabled={busy} onPress={() => setCreating(false)} style={[styles.secondaryButton, compact && styles.secondaryButtonCompact]}>
                        <Text style={[styles.secondaryButtonText, compact && styles.secondaryButtonTextCompact]}>BACK</Text>
                      </TouchableOpacity>
                    ) : null}
                    <TouchableOpacity accessibilityRole="button" accessibilityLabel="Create Project" disabled={busy} onPress={() => void createProject()} style={[styles.primaryButton, compact && styles.primaryButtonCompact]}>
                      <Text style={[styles.primaryButtonText, compact && styles.primaryButtonTextCompact]}>{busy ? 'CREATING…' : 'CREATE PROJECT'}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ) : (
                <View style={[styles.selectorActions, compact && styles.selectorActionsCompact]}>
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel="Refresh Projects" disabled={busy} onPress={() => void loadProjects(selectedRef.current, true).catch(() => undefined)} style={[styles.secondaryButton, compact && styles.secondaryButtonCompact]}>
                    <Text style={[styles.secondaryButtonText, compact && styles.secondaryButtonTextCompact]}>{busy ? 'REFRESHING…' : 'REFRESH'}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity accessibilityRole="button" accessibilityLabel="New Project" disabled={busy} onPress={() => { setError(''); setCreating(true); }} style={[styles.primaryButton, compact && styles.primaryButtonCompact]}>
                    <Text style={[styles.primaryButtonText, compact && styles.primaryButtonTextCompact]}>NEW PROJECT</Text>
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
    minHeight: 30,
    maxWidth: 250,
    paddingHorizontal: 10,
    borderRadius: 15,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(11,16,25,0.92)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: 'rgba(167,151,255,0.18)',
  },
  bindingPillDesktop: { top: 16, right: 150 },
  bindingDot: { width: 6, height: 6, borderRadius: 3 },
  bindingDotBound: { backgroundColor: palette.sage },
  bindingDotHistorical: { backgroundColor: palette.warning },
  bindingText: { flexShrink: 1, color: palette.textSecondary, fontSize: 8, fontWeight: '800', letterSpacing: 0.65 },
  bindingHistoricalText: { flexShrink: 1, color: palette.warning, fontSize: 8, fontWeight: '800', letterSpacing: 0.55 },
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
    maxWidth: 520,
    maxHeight: '86%',
    padding: 22,
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
  kicker: { color: palette.violet, fontSize: 8, fontWeight: '800', letterSpacing: 1.15 },
  kickerCompact: { color: palette.olive700 },
  selectorTitle: { color: palette.text, fontSize: 20, fontWeight: '600', letterSpacing: -0.35, marginTop: 5 },
  selectorTitleCompact: { color: palette.charcoal950, fontSize: 22, lineHeight: 27 },
  selectorCopy: { color: palette.textSecondary, fontSize: 11, lineHeight: 17, marginTop: 7 },
  selectorCopyCompact: { color: palette.charcoal600, fontSize: 11, lineHeight: 17 },
  closeButton: { width: 44, height: 44, marginTop: -8, marginRight: -8, alignItems: 'center', justifyContent: 'center', borderRadius: 22 },
  closeText: { color: palette.textSecondary, fontSize: 24, lineHeight: 26 },
  closeTextCompact: { color: palette.charcoal600 },
  errorText: { color: palette.danger, fontSize: 10, lineHeight: 15, marginTop: 13 },
  spinner: { marginTop: 20 },
  projectList: { maxHeight: 250, marginTop: 16 },
  projectListContent: { gap: 7 },
  projectRow: {
    minHeight: 54,
    paddingHorizontal: 13,
    paddingVertical: 10,
    borderRadius: 15,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: palette.glassSoft,
  },
  projectRowCompact: { minHeight: 58, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  projectRowSelected: { backgroundColor: palette.indigoWash },
  projectRowSelectedCompact: { backgroundColor: palette.teal100, borderColor: 'rgba(0,132,135,0.22)' },
  projectCopy: { flex: 1, minWidth: 0 },
  projectName: { color: palette.text, fontSize: 13, fontWeight: '600' },
  projectNameCompact: { color: palette.charcoal950 },
  projectMeta: { color: palette.muted, fontSize: 9, marginTop: 4 },
  projectMetaCompact: { color: palette.charcoal450 },
  selectLabel: { color: palette.violet, fontSize: 8, fontWeight: '800', letterSpacing: 0.65 },
  selectLabelCompact: { color: palette.teal700 },
  selectedLabel: { color: palette.sage, fontSize: 8, fontWeight: '800', letterSpacing: 0.65 },
  selectedLabelCompact: { color: palette.olive700 },
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
  secondaryButtonText: { color: palette.textSecondary, fontSize: 9, fontWeight: '800', letterSpacing: 0.7 },
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
  primaryButtonText: { color: palette.text, fontSize: 9, fontWeight: '800', letterSpacing: 0.7 },
  primaryButtonTextCompact: { color: palette.ivory50 },
});
