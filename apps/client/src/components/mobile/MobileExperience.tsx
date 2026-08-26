import React from 'react';
import { Platform, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { ConversationDto, EngineeringRunDto, WorkSpecificationDto } from '../../lib/api';
import { palette } from '../../theme';
import { ParallaxLogo } from '../ParallaxLogo';
import { useProjectCompatibility } from '../ProjectCompatibilityGate';

export type MobileDestination = 'chat' | 'build' | 'project';

type MobileHeaderProps = {
  mode: 'reason' | 'code';
  projectId: string | null;
  conversationTitle?: string | null;
  onModeChange(next: 'reason' | 'code'): void;
  onNewConversation(): void;
};

function shortProject(projectId: string | null): string {
  if (!projectId) return 'No project selected';
  return `Project ${projectId.slice(0, 8)}`;
}

export function MobileHeader({ mode, projectId, conversationTitle, onModeChange, onNewConversation }: MobileHeaderProps) {
  const projectCompatibility = useProjectCompatibility();
  const projectName = projectId && projectCompatibility.project?.id === projectId
    ? projectCompatibility.project.name
    : shortProject(projectId);

  return (
    <View style={styles.header} testID="mobile-workspace-header">
      <View style={styles.headerIdentity}>
        <ParallaxLogo size={34} />
        <View style={styles.headerCopy}>
          <Text style={styles.brand}>Parallax</Text>
          <Text numberOfLines={1} style={styles.projectLabel}>{projectName}</Text>
          {conversationTitle ? <Text numberOfLines={1} style={styles.conversationLabel}>{conversationTitle}</Text> : null}
        </View>
      </View>
      <View style={styles.headerActions}>
        <View accessibilityLabel="Parallax mode" style={styles.modeSwitch}>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityState={{ selected: mode === 'reason' }}
            accessibilityLabel="Ask mode"
            onPress={() => onModeChange('reason')}
            style={[styles.modeButton, mode === 'reason' && styles.modeButtonActive]}
          >
            <Text style={[styles.modeText, mode === 'reason' && styles.modeTextActive]}>Ask</Text>
          </TouchableOpacity>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityState={{ selected: mode === 'code' }}
            accessibilityLabel="Build mode"
            onPress={() => onModeChange('code')}
            style={[styles.modeButton, mode === 'code' && styles.modeButtonActive]}
          >
            <Text style={[styles.modeText, mode === 'code' && styles.modeTextActive]}>Build</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="New conversation" onPress={onNewConversation} style={styles.newButton}>
          <Text style={styles.newButtonText}>＋</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

type BottomNavigationProps = {
  active: MobileDestination;
  onSelect(destination: MobileDestination): void;
  buildActive?: boolean;
};

export function MobileBottomNavigation({ active, onSelect, buildActive = false }: BottomNavigationProps) {
  const items: Array<{ id: MobileDestination; label: string }> = [
    { id: 'chat', label: 'Chat' },
    { id: 'build', label: 'Build' },
    { id: 'project', label: 'Project' },
  ];
  return (
    <View accessibilityRole="tablist" accessibilityLabel="Primary mobile navigation" style={styles.bottomNav} testID="mobile-bottom-navigation">
      {items.map((item) => {
        const selected = active === item.id;
        return (
          <TouchableOpacity
            key={item.id}
            accessibilityRole="tab"
            accessibilityLabel={item.label}
            accessibilityState={{ selected }}
            onPress={() => onSelect(item.id)}
            style={[styles.bottomNavItem, selected && styles.bottomNavItemActive]}
          >
            <View style={styles.bottomNavLabelRow}>
              {item.id === 'build' && buildActive ? <View accessibilityLabel="Build active" style={styles.liveDot} /> : null}
              <Text style={[styles.bottomNavText, selected && styles.bottomNavTextActive]}>{item.label}</Text>
            </View>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function friendlyRunState(run: EngineeringRunDto | null): string {
  if (!run) return 'Not started';
  const stage = (run.state === 'FAILED' || run.state === 'PAUSED' || run.state === 'CANCELLED') && run.resume_stage
    ? run.resume_stage
    : run.state;
  const labels: Record<string, string> = {
    SPECIFY: 'Preparing specification',
    PLAN: 'Planning the build',
    IMPLEMENT: 'Implementing changes',
    BUILD: 'Building the application',
    TEST: 'Running tests',
    VERIFY: 'Verifying the result',
    REVIEW: 'Ready for review',
    COMPLETE: 'Build complete',
    FAILED: 'Build needs attention',
    PAUSED: 'Build paused',
    CANCELLED: 'Build cancelled',
  };
  const base = labels[stage] ?? stage.replaceAll('_', ' ').toLowerCase();
  if (run.state === 'FAILED') return `${base} · needs attention`;
  if (run.state === 'PAUSED') return `${base} · paused`;
  if (run.state === 'CANCELLED') return `${base} · cancelled`;
  return base;
}

type MobileContextCardProps = {
  specification: WorkSpecificationDto | null;
  run: EngineeringRunDto | null;
  canDraft: boolean;
  busy: boolean;
  error: string | null;
  onCapture(): void;
  onReviewSpecification(): void;
  onOpenBuild(): void;
};

export function MobileContextCard({ specification, run, canDraft, busy, error, onCapture, onReviewSpecification, onOpenBuild }: MobileContextCardProps) {
  if (!specification && !run && !canDraft && !error) return null;

  let eyebrow = 'BUILD';
  let title = 'Ready when you are';
  let copy = 'Describe the outcome you want to create.';
  let primaryLabel: string | null = null;
  let primaryAction: (() => void) | null = null;

  if (!specification && canDraft) {
    eyebrow = 'NEXT STEP';
    title = 'Define what Parallax should build';
    copy = 'Capture the objective and success criteria before implementation begins.';
    primaryLabel = busy ? 'Capturing…' : 'Capture specification';
    primaryAction = onCapture;
  } else if (specification?.status === 'DRAFT') {
    eyebrow = 'ACTION REQUIRED';
    title = 'Specification ready';
    copy = `${specification.acceptance_criteria.length} acceptance criteria are ready for your review.`;
    primaryLabel = 'Review specification';
    primaryAction = onReviewSpecification;
  } else if (run) {
    eyebrow = run.state === 'REVIEW' || run.state === 'COMPLETE' ? 'BUILD READY' : 'BUILD STATUS';
    title = friendlyRunState(run);
    copy = run.last_failure_code ? `Latest issue: ${run.last_failure_code}` : 'Open Build for the guided lifecycle and engineering evidence.';
    primaryLabel = 'Open Build';
    primaryAction = onOpenBuild;
  } else if (specification?.status === 'APPROVED') {
    eyebrow = 'SPECIFICATION APPROVED';
    title = 'The build contract is approved';
    copy = 'Parallax will keep implementation aligned to this approved scope.';
    primaryLabel = 'Open Build';
    primaryAction = onOpenBuild;
  }

  return (
    <View style={styles.contextCard} testID="mobile-context-card">
      <Text style={styles.contextEyebrow}>{eyebrow}</Text>
      <Text style={styles.contextTitle}>{title}</Text>
      <Text style={styles.contextCopy}>{copy}</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {primaryLabel && primaryAction ? (
        <TouchableOpacity accessibilityRole="button" accessibilityLabel={primaryLabel} disabled={busy} onPress={primaryAction} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>{primaryLabel}</Text>
        </TouchableOpacity>
      ) : null}
      {specification ? (
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Review current specification" onPress={onReviewSpecification} style={styles.textButton}>
          <Text style={styles.textButtonText}>Review current specification</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

type AmendmentNoticeProps = {
  busy?: boolean;
  canResumeApprovedScope: boolean;
  onStartNewObjective(): void;
  onResumeApprovedScope(): void;
};

export function MobileAmendmentNotice({ busy = false, canResumeApprovedScope, onStartNewObjective, onResumeApprovedScope }: AmendmentNoticeProps) {
  return (
    <View accessibilityLiveRegion="polite" style={styles.amendmentCard} testID="mobile-spec-amendment">
      <Text style={styles.contextEyebrow}>SCOPE CHANGE</Text>
      <Text style={styles.contextTitle}>This request changes the approved build</Text>
      <Text style={styles.contextCopy}>Parallax stopped before changing the approved scope. Start a new objective for this request, or return to the build you already approved.</Text>
      <TouchableOpacity accessibilityRole="button" accessibilityLabel="Start new objective" disabled={busy} onPress={onStartNewObjective} style={styles.primaryButton}>
        <Text style={styles.primaryButtonText}>Start new objective</Text>
      </TouchableOpacity>
      {canResumeApprovedScope ? (
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Continue current approved build" disabled={busy} onPress={onResumeApprovedScope} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>{busy ? 'Continuing…' : 'Continue current build'}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

function SpecSection({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <View style={styles.detailSection}>
      <Text style={styles.detailLabel}>{label}</Text>
      {items.map((item, index) => <Text selectable key={`${label}-${index}`} style={styles.detailItem}>• {item}</Text>)}
    </View>
  );
}

type SpecificationDetailProps = {
  specification: WorkSpecificationDto;
  busy: boolean;
  error: string | null;
  amendment: boolean;
  onBack(): void;
  onApprove(): void;
  onRefresh(): void;
  onResumeApprovedScope(): void;
};

export function MobileSpecificationDetail({ specification, busy, error, amendment, onBack, onApprove, onRefresh, onResumeApprovedScope }: SpecificationDetailProps) {
  const approved = specification.status === 'APPROVED';
  return (
    <View style={styles.detailRoot} testID="mobile-specification-detail">
      <View style={styles.detailHeader}>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Back to Chat" onPress={onBack} style={styles.backButton}>
          <Text style={styles.backButtonText}>‹ Back</Text>
        </TouchableOpacity>
        <View style={styles.detailHeaderCopy}>
          <Text style={styles.contextEyebrow}>SPECIFICATION · REV {specification.revision}</Text>
          <Text numberOfLines={1} style={styles.detailHeaderTitle}>{approved ? 'Approved build' : 'Review before building'}</Text>
        </View>
      </View>
      <ScrollView style={styles.detailScroll} contentContainerStyle={styles.detailContent} keyboardShouldPersistTaps="handled">
        {amendment ? (
          <View style={styles.inlineNotice}>
            <Text style={styles.inlineNoticeTitle}>A newer request changes this approved scope.</Text>
            <Text style={styles.inlineNoticeCopy}>You can return to this approved build without changing it.</Text>
          </View>
        ) : null}
        <View style={styles.detailSection}>
          <Text style={styles.detailLabel}>OBJECTIVE</Text>
          <Text selectable style={styles.detailObjective}>{specification.objective}</Text>
        </View>
        <SpecSection label="ACCEPTANCE CRITERIA" items={specification.acceptance_criteria} />
        <SpecSection label="CONSTRAINTS" items={specification.constraints} />
        <SpecSection label="OPEN QUESTIONS" items={specification.open_questions} />
        <SpecSection label="RISKS" items={specification.risks} />
        <Text style={styles.detailMeta}>Status {specification.status} · Confidence {Math.round(specification.confidence * 100)}%</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {specification.status === 'DRAFT' ? (
          <>
            <TouchableOpacity accessibilityRole="button" accessibilityLabel="Approve and continue" disabled={busy} onPress={onApprove} style={styles.primaryButtonLarge}>
              <Text style={styles.primaryButtonText}>{busy ? 'Approving…' : 'Approve and continue'}</Text>
            </TouchableOpacity>
            <TouchableOpacity accessibilityRole="button" accessibilityLabel="Refresh specification draft" disabled={busy} onPress={onRefresh} style={styles.secondaryButtonLarge}>
              <Text style={styles.secondaryButtonText}>Refresh draft</Text>
            </TouchableOpacity>
          </>
        ) : amendment ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Continue current approved build" disabled={busy} onPress={onResumeApprovedScope} style={styles.primaryButtonLarge}>
            <Text style={styles.primaryButtonText}>{busy ? 'Continuing…' : 'Continue current build'}</Text>
          </TouchableOpacity>
        ) : null}
      </ScrollView>
    </View>
  );
}

const BUILD_STAGES = [
  { key: 'SPEC', label: 'Specification' },
  { key: 'PLAN', label: 'Plan' },
  { key: 'IMPLEMENT', label: 'Implementation' },
  { key: 'BUILD', label: 'Build' },
  { key: 'TEST', label: 'Test' },
  { key: 'VERIFY', label: 'Verify' },
  { key: 'REVIEW', label: 'Review' },
] as const;

type StageStatus = 'complete' | 'current' | 'pending' | 'failed' | 'paused' | 'cancelled';

function runStageKey(run: EngineeringRunDto | null): string | null {
  if (!run) return null;
  if (['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'].includes(run.state)) return run.state;
  if (run.resume_stage && ['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'].includes(run.resume_stage)) return run.resume_stage;
  return null;
}

function stageStatus(key: string, specification: WorkSpecificationDto | null, run: EngineeringRunDto | null): StageStatus {
  if (key === 'SPEC') {
    if (specification?.status === 'APPROVED') return 'complete';
    if (specification?.status === 'DRAFT' || !specification) return 'current';
    return 'pending';
  }
  if (!specification || specification.status !== 'APPROVED') return 'pending';
  if (!run) return 'pending';
  if (run.state === 'COMPLETE') return 'complete';

  const current = runStageKey(run);
  if (!current) return 'pending';
  const keys = BUILD_STAGES.map((item) => item.key);
  const currentIndex = keys.indexOf(current as typeof keys[number]);
  const index = keys.indexOf(key as typeof keys[number]);
  if (index < currentIndex) return 'complete';
  if (index > currentIndex) return 'pending';
  if (run.state === 'FAILED') return 'failed';
  if (run.state === 'PAUSED') return 'paused';
  if (run.state === 'CANCELLED') return 'cancelled';
  return 'current';
}

function stageMarker(status: StageStatus): string {
  if (status === 'complete') return '✓';
  if (status === 'failed') return '!';
  if (status === 'paused') return 'Ⅱ';
  if (status === 'cancelled') return '×';
  if (status === 'current') return '•';
  return '○';
}

function stageStatusText(status: StageStatus): string {
  if (status === 'complete') return 'Complete';
  if (status === 'failed') return 'Needs attention';
  if (status === 'paused') return 'Paused';
  if (status === 'cancelled') return 'Cancelled';
  if (status === 'current') return 'Current';
  return 'Pending';
}

type BuildWorkspaceProps = {
  specification: WorkSpecificationDto | null;
  run: EngineeringRunDto | null;
  canDraft: boolean;
  busy: boolean;
  error: string | null;
  onCaptureSpecification(): void;
  onReviewSpecification(): void;
  onOpenDetails(): void;
};

export function MobileBuildWorkspace({ specification, run, canDraft, busy, error, onCaptureSpecification, onReviewSpecification, onOpenDetails }: BuildWorkspaceProps) {
  const currentActivity = specification?.status === 'DRAFT'
    ? 'Specification needs your review'
    : run
      ? friendlyRunState(run)
      : specification?.status === 'APPROVED'
        ? 'Specification approved'
        : 'No build started';

  return (
    <ScrollView style={styles.screenScroll} contentContainerStyle={styles.screenContent} testID="mobile-build-workspace">
      <Text style={styles.screenKicker}>GUIDED BUILD</Text>
      <Text style={styles.screenTitle}>Build</Text>
      <Text style={styles.screenCopy}>Follow the current build without needing to interpret Parallax’s internal engineering state.</Text>

      <View style={styles.activityCard}>
        <Text style={styles.detailLabel}>CURRENT ACTIVITY</Text>
        <Text style={styles.activityTitle}>{currentActivity}</Text>
        {run?.last_failure_code ? <Text style={styles.activityCopy}>Latest issue: {run.last_failure_code}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {!specification && canDraft ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Capture specification" disabled={busy} onPress={onCaptureSpecification} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>{busy ? 'Capturing…' : 'Capture specification'}</Text>
          </TouchableOpacity>
        ) : specification?.status === 'DRAFT' ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Review specification" onPress={onReviewSpecification} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Review specification</Text>
          </TouchableOpacity>
        ) : run ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Open build details" onPress={onOpenDetails} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Open build details</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      <View style={styles.lifecycleCard}>
        <Text style={styles.detailLabel}>BUILD LIFECYCLE</Text>
        {BUILD_STAGES.map((stage, index) => {
          const status = stageStatus(stage.key, specification, run);
          return (
            <View key={stage.key} style={[styles.stageRow, index === BUILD_STAGES.length - 1 && styles.stageRowLast]}>
              <View style={[styles.stageMarker, status === 'complete' && styles.stageMarkerComplete, status === 'current' && styles.stageMarkerCurrent, status === 'failed' && styles.stageMarkerFailed]}>
                <Text style={styles.stageMarkerText}>{stageMarker(status)}</Text>
              </View>
              <View style={styles.stageCopy}>
                <Text style={styles.stageTitle}>{stage.label}</Text>
                <Text style={styles.stageMeta}>{stageStatusText(status)}</Text>
              </View>
            </View>
          );
        })}
      </View>

      {run?.attempts?.length ? (
        <View style={styles.evidenceCard}>
          <Text style={styles.detailLabel}>RECENT EVIDENCE</Text>
          {run.attempts.slice(-3).reverse().map((attempt) => (
            <View key={attempt.id} style={styles.attemptRow}>
              <Text style={styles.attemptStage}>{attempt.stage}</Text>
              <Text style={styles.attemptMeta}>{attempt.status}{attempt.failure_code ? ` · ${attempt.failure_code}` : ''}</Text>
            </View>
          ))}
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Open build details and evidence" onPress={onOpenDetails} style={styles.textButton}>
            <Text style={styles.textButtonText}>View full engineering evidence</Text>
          </TouchableOpacity>
        </View>
      ) : null}
    </ScrollView>
  );
}

type ProjectWorkspaceProps = {
  activeConversation: ConversationDto | undefined;
  conversations: ConversationDto[];
  onOpenConversation(conversation: ConversationDto): void;
  onStartAsk(): void;
  onStartBuild(): void;
};

export function MobileProjectWorkspace({ activeConversation, conversations, onOpenConversation, onStartAsk, onStartBuild }: ProjectWorkspaceProps) {
  const projectCompatibility = useProjectCompatibility();
  const activeProjectId = activeConversation?.project_id ?? null;
  const boundProject = activeProjectId && projectCompatibility.project?.id === activeProjectId
    ? projectCompatibility.project
    : null;
  const displayProject = boundProject ?? (!activeProjectId ? projectCompatibility.project : null);
  const projectTitle = displayProject?.name ?? shortProject(activeProjectId);
  const projectCaption = projectCompatibility.historical
    ? 'Historical Build conversation · no canonical Project binding'
    : activeProjectId
      ? `Bound Project · ${activeProjectId.slice(0, 8)}`
      : displayProject
        ? 'Selected for future Build work'
        : 'Choose a Project before starting Build work';

  return (
    <ScrollView style={styles.screenScroll} contentContainerStyle={styles.screenContent} testID="mobile-project-workspace">
      <Text style={styles.screenKicker}>CURRENT CONTEXT</Text>
      <Text style={styles.screenTitle}>Project</Text>
      <Text style={styles.screenCopy}>See where Build work belongs, switch conversations, or choose the Project for your next Build.</Text>

      <View style={styles.projectCard}>
        <Text style={styles.detailLabel}>{activeProjectId ? 'CURRENT PROJECT' : 'BUILD PROJECT'}</Text>
        <Text style={styles.projectTitle}>{projectTitle}</Text>
        <Text style={styles.projectMeta}>{projectCaption}</Text>
        <Text numberOfLines={2} style={styles.projectConversation}>{activeConversation?.title ?? 'No conversation selected'}</Text>
        <Text style={styles.projectConversationMeta}>{activeConversation?.mode === 'code' ? 'Build' : 'Ask'} · {activeConversation?.project_binding_status ?? 'No binding'}</Text>
        {!projectCompatibility.historical ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel={displayProject ? 'Change project' : 'Choose project'} onPress={projectCompatibility.openProjectSelector} style={styles.changeProjectButton}>
            <Text style={styles.changeProjectButtonText}>{displayProject ? 'Change project' : 'Choose project'}</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      <View style={styles.newActionRow}>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Start new Ask conversation" onPress={onStartAsk} style={styles.secondaryActionTile}>
          <Text style={styles.secondaryActionTitle}>New Ask</Text>
          <Text style={styles.secondaryActionCopy}>Analyze, plan or discuss.</Text>
        </TouchableOpacity>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Start new Build conversation" onPress={onStartBuild} style={styles.primaryActionTile}>
          <Text style={styles.primaryActionTitle}>New Build</Text>
          <Text style={styles.primaryActionCopy}>Create or change software.</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.conversationList}>
        <Text style={styles.detailLabel}>RECENT CONVERSATIONS</Text>
        {conversations.slice(0, 12).map((conversation) => {
          const selected = conversation.id === activeConversation?.id;
          return (
            <TouchableOpacity
              key={conversation.id}
              accessibilityRole="button"
              accessibilityLabel={`Open ${conversation.title}`}
              accessibilityState={{ selected }}
              onPress={() => onOpenConversation(conversation)}
              style={[styles.conversationRow, selected && styles.conversationRowSelected]}
            >
              <View style={styles.conversationRowCopy}>
                <Text numberOfLines={1} style={styles.conversationTitle}>{conversation.title}</Text>
                <Text numberOfLines={1} style={styles.conversationMeta}>{conversation.mode === 'code' ? 'Build' : 'Ask'} · {shortProject(conversation.project_id)}</Text>
              </View>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </ScrollView>
  );
}

const serif = Platform.OS === 'web' ? 'Georgia, ui-serif, Charter, serif' : undefined;

const styles = StyleSheet.create({
  header: { minHeight: 68, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, paddingLeft: 14, paddingRight: 58, paddingVertical: 9, backgroundColor: 'rgba(251,247,238,0.97)', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  headerIdentity: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center', gap: 9 },
  headerCopy: { flex: 1, minWidth: 0 },
  brand: { color: palette.charcoal950, fontSize: 17, lineHeight: 20, fontWeight: '700', fontFamily: serif },
  projectLabel: { color: palette.olive700, fontSize: 9, lineHeight: 13, fontWeight: '800', marginTop: 1 },
  conversationLabel: { color: palette.charcoal450, fontSize: 8, lineHeight: 11, marginTop: 1 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  modeSwitch: { minHeight: 40, padding: 3, flexDirection: 'row', alignItems: 'center', borderRadius: 14, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  modeButton: { minWidth: 46, minHeight: 34, borderRadius: 11, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 },
  modeButtonActive: { backgroundColor: palette.rust600 },
  modeText: { color: palette.charcoal600, fontSize: 9, fontWeight: '800' },
  modeTextActive: { color: palette.ivory50 },
  newButton: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.cream200 },
  newButtonText: { color: palette.rust700, fontSize: 18 },
  bottomNav: { minHeight: 64, flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 10, paddingTop: 7, paddingBottom: 8, backgroundColor: 'rgba(245,238,223,0.98)', borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  bottomNavItem: { flex: 1, minHeight: 48, alignItems: 'center', justifyContent: 'center', borderRadius: 15 },
  bottomNavItemActive: { backgroundColor: palette.rust100 },
  bottomNavLabelRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  bottomNavText: { color: palette.charcoal600, fontSize: 10, fontWeight: '800' },
  bottomNavTextActive: { color: palette.rust700 },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: palette.teal600 },
  contextCard: { marginBottom: 22, padding: 16, borderRadius: 19, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  amendmentCard: { marginBottom: 22, padding: 16, borderRadius: 19, backgroundColor: palette.rust100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(168,59,23,0.18)' },
  contextEyebrow: { color: palette.olive700, fontSize: 8, lineHeight: 11, fontWeight: '800', letterSpacing: 0.9, marginBottom: 5 },
  contextTitle: { color: palette.charcoal950, fontSize: 17, lineHeight: 22, fontWeight: '700', letterSpacing: -0.25 },
  contextCopy: { color: palette.charcoal600, fontSize: 11, lineHeight: 17, marginTop: 5 },
  primaryButton: { minHeight: 44, marginTop: 13, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 14, backgroundColor: palette.rust600 },
  primaryButtonLarge: { minHeight: 50, marginTop: 24, borderRadius: 15, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, backgroundColor: palette.rust600 },
  primaryButtonText: { color: palette.ivory50, fontSize: 10, lineHeight: 14, fontWeight: '800' },
  secondaryButton: { minHeight: 44, marginTop: 8, borderRadius: 14, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 14, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  secondaryButtonLarge: { minHeight: 48, marginTop: 9, borderRadius: 15, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  secondaryButtonText: { color: palette.charcoal800, fontSize: 10, lineHeight: 14, fontWeight: '800' },
  textButton: { minHeight: 44, marginTop: 6, alignItems: 'center', justifyContent: 'center' },
  textButtonText: { color: palette.teal700, fontSize: 9, fontWeight: '800' },
  error: { color: palette.danger, fontSize: 10, lineHeight: 15, marginTop: 9 },
  detailRoot: { flex: 1, minHeight: 0, backgroundColor: palette.ivory50 },
  detailHeader: { minHeight: 70, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 12, paddingVertical: 9, backgroundColor: palette.cream100, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  backButton: { minWidth: 66, minHeight: 44, borderRadius: 13, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  backButtonText: { color: palette.teal700, fontSize: 10, fontWeight: '800' },
  detailHeaderCopy: { flex: 1, minWidth: 0 },
  detailHeaderTitle: { color: palette.charcoal950, fontSize: 16, lineHeight: 20, fontWeight: '700' },
  detailScroll: { flex: 1, minHeight: 0 },
  detailContent: { paddingHorizontal: 18, paddingTop: 22, paddingBottom: 34 },
  detailSection: { marginBottom: 22 },
  detailLabel: { color: palette.olive700, fontSize: 8, lineHeight: 11, fontWeight: '800', letterSpacing: 0.9, marginBottom: 7 },
  detailObjective: { color: palette.charcoal950, fontSize: 16, lineHeight: 25 },
  detailItem: { color: palette.charcoal600, fontSize: 13, lineHeight: 21, marginBottom: 6 },
  detailMeta: { color: palette.charcoal450, fontSize: 9, lineHeight: 14, marginTop: 2 },
  inlineNotice: { marginBottom: 20, padding: 14, borderRadius: 16, backgroundColor: palette.rust100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(168,59,23,0.16)' },
  inlineNoticeTitle: { color: palette.charcoal950, fontSize: 12, lineHeight: 17, fontWeight: '800' },
  inlineNoticeCopy: { color: palette.charcoal600, fontSize: 10, lineHeight: 16, marginTop: 4 },
  screenScroll: { flex: 1, minHeight: 0 },
  screenContent: { paddingHorizontal: 16, paddingTop: 22, paddingBottom: 34 },
  screenKicker: { color: palette.olive700, fontSize: 8, lineHeight: 11, fontWeight: '800', letterSpacing: 1.0 },
  screenTitle: { color: palette.charcoal950, fontSize: 29, lineHeight: 34, fontWeight: '600', letterSpacing: -0.8, fontFamily: serif, marginTop: 4 },
  screenCopy: { color: palette.charcoal600, fontSize: 11, lineHeight: 18, marginTop: 7, marginBottom: 18 },
  activityCard: { padding: 16, borderRadius: 19, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, marginBottom: 14 },
  activityTitle: { color: palette.charcoal950, fontSize: 17, lineHeight: 22, fontWeight: '700' },
  activityCopy: { color: palette.charcoal600, fontSize: 10, lineHeight: 16, marginTop: 5 },
  lifecycleCard: { paddingHorizontal: 16, paddingTop: 16, paddingBottom: 4, borderRadius: 19, backgroundColor: '#FFFDF8', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, marginBottom: 14 },
  stageRow: { minHeight: 54, flexDirection: 'row', alignItems: 'center', gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  stageRowLast: { borderBottomWidth: 0 },
  stageMarker: { width: 30, height: 30, borderRadius: 15, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.cream200 },
  stageMarkerComplete: { backgroundColor: palette.olive200 },
  stageMarkerCurrent: { backgroundColor: palette.teal100 },
  stageMarkerFailed: { backgroundColor: palette.rust100 },
  stageMarkerText: { color: palette.charcoal800, fontSize: 12, fontWeight: '800' },
  stageCopy: { flex: 1, minWidth: 0 },
  stageTitle: { color: palette.charcoal950, fontSize: 12, lineHeight: 16, fontWeight: '700' },
  stageMeta: { color: palette.charcoal450, fontSize: 9, lineHeight: 13, marginTop: 1 },
  evidenceCard: { padding: 16, borderRadius: 19, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  attemptRow: { minHeight: 43, paddingVertical: 8, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  attemptStage: { color: palette.charcoal950, fontSize: 10, lineHeight: 14, fontWeight: '800' },
  attemptMeta: { color: palette.charcoal600, fontSize: 9, lineHeight: 14, marginTop: 2 },
  projectCard: { padding: 16, borderRadius: 19, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, marginBottom: 14 },
  projectTitle: { color: palette.charcoal950, fontSize: 19, lineHeight: 24, fontWeight: '700' },
  projectMeta: { color: palette.olive700, fontSize: 9, lineHeight: 13, fontWeight: '700', marginTop: 6 },
  projectConversation: { color: palette.charcoal600, fontSize: 11, lineHeight: 17, marginTop: 12 },
  projectConversationMeta: { color: palette.charcoal450, fontSize: 9, lineHeight: 13, marginTop: 4 },
  changeProjectButton: { minHeight: 44, marginTop: 14, alignItems: 'center', justifyContent: 'center', borderRadius: 14, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  changeProjectButtonText: { color: palette.teal700, fontSize: 10, fontWeight: '800' },
  newActionRow: { flexDirection: 'row', gap: 10, marginBottom: 22 },
  secondaryActionTile: { flex: 1, minHeight: 86, padding: 14, borderRadius: 17, justifyContent: 'center', backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  primaryActionTile: { flex: 1, minHeight: 86, padding: 14, borderRadius: 17, justifyContent: 'center', backgroundColor: palette.rust600 },
  secondaryActionTitle: { color: palette.charcoal950, fontSize: 12, fontWeight: '800' },
  secondaryActionCopy: { color: palette.charcoal600, fontSize: 9, lineHeight: 14, marginTop: 4 },
  primaryActionTitle: { color: palette.ivory50, fontSize: 12, fontWeight: '800' },
  primaryActionCopy: { color: 'rgba(251,247,238,0.82)', fontSize: 9, lineHeight: 14, marginTop: 4 },
  conversationList: { marginBottom: 12 },
  conversationRow: { minHeight: 58, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 13, paddingVertical: 9, borderRadius: 15, marginBottom: 7, backgroundColor: '#FFFDF8', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  conversationRowSelected: { backgroundColor: palette.teal100, borderColor: 'rgba(0,132,135,0.22)' },
  conversationRowCopy: { flex: 1, minWidth: 0 },
  conversationTitle: { color: palette.charcoal950, fontSize: 11, lineHeight: 15, fontWeight: '700' },
  conversationMeta: { color: palette.charcoal450, fontSize: 8, lineHeight: 12, marginTop: 3 },
  chevron: { color: palette.teal700, fontSize: 22, lineHeight: 24 },
});