import React from 'react';
import { Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { api, type ConversationDto, type ProjectDto } from '../lib/api';
import { deleteProject } from '../lib/deletionApi';
import { palette } from '../theme';

type Props = {
  conversation: ConversationDto | undefined;
  onStartCodeWork(): void;
};

function TechnicalDetails({ conversation }: { conversation: ConversationDto | undefined }) {
  const [open, setOpen] = React.useState(false);
  return (
    <View style={styles.technicalWrap}>
      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide technical details' : 'Show technical details'}
        accessibilityState={{ expanded: open }}
        onPress={() => setOpen((value) => !value)}
        style={styles.technicalToggle}
      >
        <Text style={styles.technicalToggleText}>{open ? 'Hide technical details' : 'Technical details'}</Text>
        <Text style={styles.technicalChevron}>{open ? '⌃' : '⌄'}</Text>
      </TouchableOpacity>
      {open ? (
        <View style={styles.technicalBody}>
          <Text selectable style={styles.technicalLine}>Mode: {conversation?.mode ?? 'Unavailable'}</Text>
          <Text selectable style={styles.technicalLine}>Project binding: {conversation?.project_binding_status ?? 'Unavailable'}</Text>
          <Text selectable style={styles.technicalLine}>Project ID: {conversation?.project_id ?? 'Unavailable'}</Text>
          <Text selectable style={styles.technicalLine}>Specification ID: {conversation?.spec_id ?? 'Unavailable'}</Text>
        </View>
      ) : null}
    </View>
  );
}

function messageFor(cause: unknown): string {
  return cause instanceof Error && cause.message.trim() ? cause.message : 'Project could not be deleted.';
}

export function EditorialProjectWorkspace({ conversation, onStartCodeWork }: Props) {
  const binding = conversation?.project_binding_status ?? null;
  const projectId = conversation?.project_id ?? null;
  const bound = binding === 'PROJECT_BOUND' && Boolean(projectId);
  const historical = binding === 'HISTORICAL_UNBOUND' && conversation?.mode === 'code';
  const [projects, setProjects] = React.useState<ProjectDto[]>([]);
  const [projectsLoading, setProjectsLoading] = React.useState(true);
  const [projectError, setProjectError] = React.useState('');
  const [confirmDeleteId, setConfirmDeleteId] = React.useState<string | null>(null);
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  const loadProjects = React.useCallback(async () => {
    setProjectsLoading(true);
    try {
      setProjects(await api.listProjects());
      setProjectError('');
    } catch (cause) {
      setProjectError(cause instanceof Error ? cause.message : 'Projects are unavailable.');
    } finally {
      setProjectsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const confirmDelete = React.useCallback(async (project: ProjectDto) => {
    if (project.id === projectId || deletingId) return;
    setDeletingId(project.id);
    setProjectError('');
    try {
      await deleteProject(project.id);
      setProjects((current) => current.filter((item) => item.id !== project.id));
      setConfirmDeleteId(null);
    } catch (cause) {
      setProjectError(messageFor(cause));
    } finally {
      setDeletingId(null);
    }
  }, [deletingId, projectId]);

  const stateLabel = bound ? 'Current project' : historical ? 'Older conversation' : 'No project needed';

  return (
    <View style={styles.wrap} testID="editorial-project-workspace">
      <View style={styles.intro}>
        <Text style={styles.kicker}>Project workspace</Text>
        <Text style={styles.title}>Know where your work belongs.</Text>
        <Text style={styles.copy}>Projects keep related conversations and builds together so it is easier to return to work later.</Text>
      </View>

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={styles.cardHeaderCopy}>
            <Text style={styles.cardKicker}>Current conversation</Text>
            <Text numberOfLines={2} style={styles.cardTitle}>{conversation?.title ?? 'No conversation selected'}</Text>
          </View>
          <View style={[styles.statePill, bound ? styles.stateBound : historical ? styles.stateHistorical : styles.stateNeutral]}>
            <Text style={styles.stateText}>{stateLabel}</Text>
          </View>
        </View>

        <View style={styles.summaryGrid}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Activity</Text>
            <Text style={styles.summaryValue}>{conversation?.mode === 'code' ? 'Build' : 'Ask'}</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Project</Text>
            <Text style={styles.summaryValue}>{bound ? 'Connected to this conversation' : historical ? 'Not connected to a current project' : 'Not required for this conversation'}</Text>
          </View>
        </View>

        <View style={styles.boundary}>
          <Text style={styles.boundaryTitle}>What happens if you delete a project?</Text>
          <Text style={styles.boundaryCopy}>The project and its conversations disappear from your active Parallax workspace. Technical history is kept, and linked GitHub repositories or Vercel deployments are not deleted.</Text>
        </View>
        <TechnicalDetails conversation={conversation} />
      </View>

      <View style={styles.actionRow}>
        <View style={styles.actionCopy}>
          <Text style={styles.actionTitle}>Start a new build</Text>
          <Text style={styles.actionText}>Parallax will help you choose or create the project needed for the work.</Text>
        </View>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Start a build" onPress={onStartCodeWork} style={styles.actionButton}>
          <Text style={styles.actionButtonText}>Start a build</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.projectListCard}>
        <View style={styles.projectListHeader}>
          <View>
            <Text style={styles.cardKicker}>Your projects</Text>
            <Text style={styles.projectListTitle}>Manage projects</Text>
          </View>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Refresh projects" disabled={projectsLoading} onPress={() => void loadProjects()} style={styles.refreshButton}>
            <Text style={styles.refreshButtonText}>{projectsLoading ? 'Refreshing…' : 'Refresh'}</Text>
          </TouchableOpacity>
        </View>
        {projectError ? <Text accessibilityLiveRegion="polite" style={styles.errorText}>Parallax couldn’t update the project list. Your existing projects have not changed.</Text> : null}
        {!projectsLoading && projects.length === 0 ? <Text style={styles.emptyText}>No active projects.</Text> : null}
        {projects.map((project) => {
          const current = project.id === projectId;
          const confirming = confirmDeleteId === project.id;
          const deleting = deletingId === project.id;
          return (
            <View key={project.id} style={styles.projectRow}>
              <View style={styles.projectRowMain}>
                <View style={styles.projectRowCopy}>
                  <Text numberOfLines={1} style={styles.projectName}>{project.name}</Text>
                  <Text numberOfLines={1} style={styles.projectMeta}>{project.repository_ref ?? project.slug}</Text>
                </View>
                {current ? (
                  <View style={styles.currentPill}><Text style={styles.currentPillText}>Current</Text></View>
                ) : (
                  <TouchableOpacity
                    accessibilityRole="button"
                    accessibilityLabel={`Delete project ${project.name}`}
                    accessibilityHint="Requires confirmation. Technical history is kept."
                    disabled={Boolean(deletingId)}
                    onPress={() => { setProjectError(''); setConfirmDeleteId(project.id); }}
                    style={styles.deleteButton}
                  >
                    <Text style={styles.deleteButtonText}>Delete</Text>
                  </TouchableOpacity>
                )}
              </View>
              {confirming ? (
                <View style={styles.confirmPanel} accessibilityLiveRegion="polite">
                  <Text style={styles.confirmCopy}>Delete “{project.name}” from Parallax? Its conversations will disappear from active history. GitHub and Vercel resources, along with technical history, will remain intact.</Text>
                  <View style={styles.confirmActions}>
                    <TouchableOpacity accessibilityRole="button" accessibilityLabel="Cancel project deletion" disabled={deleting} onPress={() => setConfirmDeleteId(null)} style={styles.confirmCancel}>
                      <Text style={styles.confirmCancelText}>Cancel</Text>
                    </TouchableOpacity>
                    <TouchableOpacity accessibilityRole="button" accessibilityLabel={`Confirm delete project ${project.name}`} disabled={deleting} onPress={() => void confirmDelete(project)} style={styles.confirmDelete}>
                      <Text style={styles.confirmDeleteText}>{deleting ? 'Deleting…' : 'Delete project'}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              ) : null}
            </View>
          );
        })}
      </View>
    </View>
  );
}

const serif = Platform.OS === 'web' ? 'Georgia, ui-serif, Charter, serif' : undefined;
const mono = Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : undefined;

const styles = StyleSheet.create({
  wrap: { flex: 1, minHeight: 0, width: '100%', maxWidth: 980, alignSelf: 'center', paddingHorizontal: 30, paddingTop: 34, paddingBottom: 30 },
  intro: { maxWidth: 700, marginBottom: 24 },
  kicker: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 7 },
  title: { color: palette.charcoal950, fontSize: 31, lineHeight: 37, fontWeight: '500', letterSpacing: -0.9, fontFamily: serif },
  copy: { color: palette.charcoal600, fontSize: 15, lineHeight: 23, marginTop: 8, maxWidth: 660 },
  card: { borderRadius: 22, padding: 22, backgroundColor: 'rgba(245,238,223,0.88)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#5B4C36', shadowOpacity: 0.065, shadowRadius: 18, shadowOffset: { width: 0, height: 8 } },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 18, marginBottom: 22 },
  cardHeaderCopy: { flex: 1, minWidth: 0 },
  cardKicker: { color: palette.charcoal450, fontSize: 11, lineHeight: 15, fontWeight: '800', letterSpacing: 0.65, textTransform: 'uppercase', marginBottom: 4 },
  cardTitle: { color: palette.charcoal950, fontSize: 19, lineHeight: 25, fontWeight: '700', maxWidth: 620 },
  statePill: { minHeight: 34, maxWidth: 190, paddingHorizontal: 12, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
  stateBound: { backgroundColor: palette.olive200 },
  stateHistorical: { backgroundColor: palette.rust100 },
  stateNeutral: { backgroundColor: palette.cream200 },
  stateText: { color: palette.charcoal800, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  summaryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  summaryItem: { minWidth: 220, flexGrow: 1, flexBasis: 260, padding: 15, borderRadius: 15, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  summaryLabel: { color: palette.charcoal450, fontSize: 11, lineHeight: 15, textTransform: 'uppercase', letterSpacing: 0.55, marginBottom: 5 },
  summaryValue: { color: palette.charcoal800, fontSize: 14, lineHeight: 21, fontWeight: '600' },
  boundary: { marginTop: 18, paddingTop: 17, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  boundaryTitle: { color: palette.charcoal950, fontSize: 14, lineHeight: 19, fontWeight: '800', marginBottom: 5 },
  boundaryCopy: { color: palette.charcoal600, fontSize: 13, lineHeight: 20, maxWidth: 720 },
  technicalWrap: { marginTop: 10, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border, paddingTop: 6 },
  technicalToggle: { minHeight: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  technicalToggleText: { color: palette.teal700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  technicalChevron: { color: palette.teal700, fontSize: 18, lineHeight: 20, fontWeight: '800' },
  technicalBody: { padding: 12, borderRadius: 13, backgroundColor: palette.cream150 },
  technicalLine: { color: palette.charcoal800, fontSize: 12, lineHeight: 18, fontFamily: mono, marginBottom: 3 },
  actionRow: { marginTop: 16, minHeight: 92, borderRadius: 18, paddingHorizontal: 18, paddingVertical: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 18, backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(0,132,135,0.18)' },
  actionCopy: { flex: 1, minWidth: 0 },
  actionTitle: { color: palette.teal700, fontSize: 15, lineHeight: 20, fontWeight: '800', marginBottom: 4 },
  actionText: { color: palette.charcoal600, fontSize: 13, lineHeight: 19 },
  actionButton: { minHeight: 46, paddingHorizontal: 17, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust600 },
  actionButtonText: { color: palette.ivory50, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  projectListCard: { marginTop: 16, borderRadius: 22, padding: 20, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  projectListHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 12 },
  projectListTitle: { color: palette.charcoal950, fontSize: 18, lineHeight: 23, fontWeight: '700' },
  refreshButton: { minHeight: 44, paddingHorizontal: 13, borderRadius: 12, alignItems: 'center', justifyContent: 'center', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  refreshButtonText: { color: palette.teal700, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  errorText: { color: palette.danger, fontSize: 13, lineHeight: 19, marginBottom: 9 },
  emptyText: { color: palette.charcoal450, fontSize: 13, lineHeight: 19 },
  projectRow: { paddingVertical: 12, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  projectRowMain: { minHeight: 52, flexDirection: 'row', alignItems: 'center', gap: 14 },
  projectRowCopy: { flex: 1, minWidth: 0 },
  projectName: { color: palette.charcoal950, fontSize: 14, lineHeight: 19, fontWeight: '700' },
  projectMeta: { color: palette.charcoal450, fontSize: 12, lineHeight: 17, marginTop: 2 },
  currentPill: { minHeight: 34, paddingHorizontal: 11, borderRadius: 999, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.olive200 },
  currentPillText: { color: palette.charcoal800, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  deleteButton: { minHeight: 44, paddingHorizontal: 13, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust100 },
  deleteButtonText: { color: palette.rust700, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  confirmPanel: { marginTop: 8, padding: 14, borderRadius: 14, backgroundColor: palette.rust100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(168,59,23,0.18)' },
  confirmCopy: { color: palette.charcoal600, fontSize: 13, lineHeight: 20 },
  confirmActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 11 },
  confirmCancel: { minHeight: 44, paddingHorizontal: 13, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  confirmCancelText: { color: palette.charcoal600, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  confirmDelete: { minHeight: 44, paddingHorizontal: 13, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust600 },
  confirmDeleteText: { color: palette.ivory50, fontSize: 12, lineHeight: 16, fontWeight: '800' },
});
