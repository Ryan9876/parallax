import React from 'react';
import { Platform, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { ConversationDto, EngineeringRunDto, WorkSpecificationDto } from '../../lib/api';
import {
  getEngineeringRunFailure,
  requestEngineeringRunRetry,
  subscribeEngineeringRunFailures,
} from '../../lib/engineeringRunEvents';
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
  return 'Project selected';
}

function useEngineeringRunFailure(conversationId: string | null | undefined) {
  const subscribe = React.useCallback((listener: () => void) => subscribeEngineeringRunFailures(listener), []);
  const getSnapshot = React.useCallback(() => getEngineeringRunFailure(conversationId ?? null), [conversationId]);
  return React.useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

function plainError(error: string | null): string | null {
  if (!error) return null;
  const normalized = error.toLowerCase();
  if (normalized.includes("couldn't prepare this project") || normalized.includes('couldn’t prepare this project')) {
    return 'Parallax couldn’t prepare this project for the next step yet. Your saved work is still here. Try again.';
  }
  return 'Parallax couldn’t continue that step. Your saved work is still here. Try again.';
}

function friendlyRunState(run: EngineeringRunDto | null): string {
  if (!run) return 'Not started';
  const stage = (run.state === 'FAILED' || run.state === 'PAUSED' || run.state === 'CANCELLED') && run.resume_stage
    ? run.resume_stage
    : run.state;
  const labels: Record<string, string> = {
    SPECIFY: 'Preparing your plan',
    PLAN: 'Planning the work',
    IMPLEMENT: 'Making the changes',
    BUILD: 'Preparing the result',
    TEST: 'Checking the result',
    VERIFY: 'Running final checks',
    REVIEW: 'Ready for your review',
    COMPLETE: 'Work complete',
    FAILED: 'Something needs attention',
    PAUSED: 'Work paused',
    CANCELLED: 'Work stopped',
  };
  const base = labels[stage] ?? 'Working on your request';
  if (run.state === 'FAILED') return `${base} · needs attention`;
  if (run.state === 'PAUSED') return `${base} · paused`;
  if (run.state === 'CANCELLED') return `${base} · stopped`;
  return base;
}

function TechnicalDetails({ children, label = 'Technical details' }: { children: React.ReactNode; label?: string }) {
  const [open, setOpen] = React.useState(false);
  return (
    <View style={styles.technicalDisclosure}>
      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel={open ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
        accessibilityState={{ expanded: open }}
        onPress={() => setOpen((current) => !current)}
        style={styles.technicalToggle}
      >
        <Text style={styles.technicalToggleText}>{open ? `Hide ${label}` : label}</Text>
        <Text aria-hidden style={styles.technicalChevron}>{open ? '⌃' : '⌄'}</Text>
      </TouchableOpacity>
      {open ? <View style={styles.technicalBody}>{children}</View> : null}
    </View>
  );
}

export function MobileHeader({ mode, projectId, conversationTitle, onModeChange, onNewConversation }: MobileHeaderProps) {
  const projectCompatibility = useProjectCompatibility();
  const projectName = projectId && projectCompatibility.project?.id === projectId
    ? projectCompatibility.project.name
    : shortProject(projectId);

  return (
    <View style={[styles.header, Platform.OS === 'web' && styles.headerWebAccountSpace]} testID="mobile-workspace-header">
      <View style={styles.headerIdentity}>
        <ParallaxLogo size={34} />
        <View style={styles.headerCopy}>
          <Text style={styles.brand}>Parallax</Text>
          <Text numberOfLines={1} style={styles.projectLabel}>{projectName}</Text>
          {conversationTitle ? <Text numberOfLines={1} style={styles.conversationLabel}>{conversationTitle}</Text> : null}
        </View>
      </View>
      <View style={styles.headerActions}>
        <View accessibilityLabel="Choose what you want to do" style={styles.modeSwitch}>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityState={{ selected: mode === 'reason' }}
            accessibilityLabel="Ask"
            onPress={() => onModeChange('reason')}
            style={[styles.modeButton, mode === 'reason' && styles.modeButtonActive]}
          >
            <Text style={[styles.modeText, mode === 'reason' && styles.modeTextActive]}>Ask</Text>
          </TouchableOpacity>
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityState={{ selected: mode === 'code' }}
            accessibilityLabel="Build"
            onPress={() => onModeChange('code')}
            style={[styles.modeButton, mode === 'code' && styles.modeButtonActive]}
          >
            <Text style={[styles.modeText, mode === 'code' && styles.modeTextActive]}>Build</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Start a new conversation" onPress={onNewConversation} style={styles.newButton}>
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
    { id: 'build', label: 'Progress' },
    { id: 'project', label: 'Project' },
  ];
  return (
    <View accessibilityRole="tablist" accessibilityLabel="Main navigation" style={styles.bottomNav} testID="mobile-bottom-navigation">
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
              {item.id === 'build' && buildActive ? <View accessibilityLabel="Work in progress" style={styles.liveDot} /> : null}
              <Text style={[styles.bottomNavText, selected && styles.bottomNavTextActive]}>{item.label}</Text>
            </View>
          </TouchableOpacity>
        );
      })}
    </View>
  );
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
  const runFailure = useEngineeringRunFailure(run?.conversation_id);
  const effectiveError = runFailure?.message ?? error;
  if (!specification && !run && !canDraft && !effectiveError) return null;

  let eyebrow = 'NEXT STEP';
  let title = 'Ready when you are';
  let copy = 'Describe what you want to accomplish.';
  let primaryLabel: string | null = null;
  let primaryAction: (() => void) | null = null;

  if (!specification && canDraft) {
    title = 'Turn your request into a build plan';
    copy = 'Parallax can summarize what you want and what success looks like before making changes.';
    primaryLabel = busy ? 'Creating plan…' : 'Create build plan';
    primaryAction = onCapture;
  } else if (specification?.status === 'DRAFT') {
    eyebrow = 'READY FOR YOU';
    title = 'Your build plan is ready to review';
    copy = `${specification.acceptance_criteria.length} success check${specification.acceptance_criteria.length === 1 ? '' : 's'} are included.`;
    primaryLabel = 'Review build plan';
    primaryAction = onReviewSpecification;
  } else if (run) {
    eyebrow = runFailure ? 'NEEDS ATTENTION' : run.state === 'REVIEW' || run.state === 'COMPLETE' ? 'READY FOR YOU' : 'IN PROGRESS';
    title = runFailure ? 'Parallax couldn’t continue this step' : friendlyRunState(run);
    copy = runFailure
      ? 'Your saved work is still here. Open Progress to see where it stopped and try again.'
      : run.last_failure_code
        ? 'Something needs attention. Open Progress to see what happened and what comes next.'
        : 'See where the work is now, what is finished, and what comes next.';
    primaryLabel = 'View progress';
    primaryAction = onOpenBuild;
  } else if (specification?.status === 'APPROVED') {
    eyebrow = 'PLAN APPROVED';
    title = 'Your plan is approved';
    copy = 'Parallax will keep the work aligned with what you approved.';
    primaryLabel = 'View progress';
    primaryAction = onOpenBuild;
  }

  return (
    <View style={styles.contextCard} testID="mobile-context-card">
      <Text style={styles.contextEyebrow}>{eyebrow}</Text>
      <Text style={styles.contextTitle}>{title}</Text>
      <Text style={styles.contextCopy}>{copy}</Text>
      {plainError(effectiveError) ? <Text accessibilityLiveRegion="polite" style={styles.error}>{plainError(effectiveError)}</Text> : null}
      {primaryLabel && primaryAction ? (
        <TouchableOpacity accessibilityRole="button" accessibilityLabel={primaryLabel} disabled={busy} onPress={primaryAction} style={styles.primaryButton}>
          <Text style={styles.primaryButtonText}>{primaryLabel}</Text>
        </TouchableOpacity>
      ) : null}
      {specification && specification.status !== 'DRAFT' ? (
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Review build plan" onPress={onReviewSpecification} style={styles.textButton}>
          <Text style={styles.textButtonText}>Review build plan</Text>
        </TouchableOpacity>
      ) : null}
      {effectiveError || run?.last_failure_code ? (
        <TechnicalDetails>
          {effectiveError ? <Text selectable style={styles.technicalLine}>System message: {effectiveError}</Text> : null}
          {run?.last_failure_code ? <Text selectable style={styles.technicalLine}>Issue code: {run.last_failure_code}</Text> : null}
        </TechnicalDetails>
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
      <Text style={styles.contextEyebrow}>YOUR REQUEST CHANGED</Text>
      <Text style={styles.contextTitle}>This is different from the plan you approved</Text>
      <Text style={styles.contextCopy}>Parallax stopped before changing the approved work. Start this as a new goal, or continue with the work you already approved.</Text>
      <TouchableOpacity accessibilityRole="button" accessibilityLabel="Start as a new goal" disabled={busy} onPress={onStartNewObjective} style={styles.primaryButton}>
        <Text style={styles.primaryButtonText}>Start as a new goal</Text>
      </TouchableOpacity>
      {canResumeApprovedScope ? (
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Continue approved work" disabled={busy} onPress={onResumeApprovedScope} style={styles.secondaryButton}>
          <Text style={styles.secondaryButtonText}>{busy ? 'Continuing…' : 'Continue approved work'}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

function PlanSection({ label, items }: { label: string; items: string[] }) {
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
          <Text style={styles.contextEyebrow}>BUILD PLAN · VERSION {specification.revision}</Text>
          <Text numberOfLines={1} style={styles.detailHeaderTitle}>{approved ? 'Approved plan' : 'Review your build plan'}</Text>
        </View>
      </View>
      <ScrollView style={styles.detailScroll} contentContainerStyle={styles.detailContent} keyboardShouldPersistTaps="handled">
        {amendment ? (
          <View style={styles.inlineNotice}>
            <Text style={styles.inlineNoticeTitle}>A newer request changes this plan.</Text>
            <Text style={styles.inlineNoticeCopy}>You can return to the approved work without changing it.</Text>
          </View>
        ) : null}
        <View style={styles.detailSection}>
          <Text style={styles.detailLabel}>WHAT YOU WANT</Text>
          <Text selectable style={styles.detailObjective}>{specification.objective}</Text>
        </View>
        <PlanSection label="WHAT SUCCESS LOOKS LIKE" items={specification.acceptance_criteria} />
        <PlanSection label="IMPORTANT LIMITS" items={specification.constraints} />
        <PlanSection label="QUESTIONS TO RESOLVE" items={specification.open_questions} />
        <PlanSection label="THINGS TO WATCH" items={specification.risks} />
        <View style={styles.planStateCard}>
          <Text style={styles.planStateTitle}>{approved ? 'Approved' : 'Waiting for your approval'}</Text>
          <Text style={styles.planStateCopy}>{approved ? 'Parallax will keep the work aligned to this plan.' : 'Approve only when this matches what you want Parallax to build.'}</Text>
        </View>
        {plainError(error) ? <Text style={styles.error}>{plainError(error)}</Text> : null}
        {specification.status === 'DRAFT' ? (
          <>
            <TouchableOpacity accessibilityRole="button" accessibilityLabel="Approve plan and continue" disabled={busy} onPress={onApprove} style={styles.primaryButtonLarge}>
              <Text style={styles.primaryButtonText}>{busy ? 'Approving…' : 'Approve plan and continue'}</Text>
            </TouchableOpacity>
            <TouchableOpacity accessibilityRole="button" accessibilityLabel="Update build plan" disabled={busy} onPress={onRefresh} style={styles.secondaryButtonLarge}>
              <Text style={styles.secondaryButtonText}>Update build plan</Text>
            </TouchableOpacity>
          </>
        ) : amendment ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Continue approved work" disabled={busy} onPress={onResumeApprovedScope} style={styles.primaryButtonLarge}>
            <Text style={styles.primaryButtonText}>{busy ? 'Continuing…' : 'Continue approved work'}</Text>
          </TouchableOpacity>
        ) : null}
        <TechnicalDetails>
          <Text selectable style={styles.technicalLine}>System object: Work Specification</Text>
          <Text selectable style={styles.technicalLine}>Revision: {specification.revision}</Text>
          <Text selectable style={styles.technicalLine}>Status: {specification.status}</Text>
          <Text selectable style={styles.technicalLine}>Confidence: {Math.round(specification.confidence * 100)}%</Text>
          {error ? <Text selectable style={styles.technicalLine}>System message: {error}</Text> : null}
        </TechnicalDetails>
      </ScrollView>
    </View>
  );
}

type StageStatus = 'complete' | 'current' | 'next' | 'pending' | 'failed' | 'paused' | 'cancelled';

type JourneyStep = {
  key: 'define' | 'plan' | 'create' | 'check' | 'review';
  label: string;
  description: string;
};

const JOURNEY_STEPS: readonly JourneyStep[] = [
  { key: 'define', label: 'Define', description: 'Agree on what you want and what success looks like.' },
  { key: 'plan', label: 'Plan', description: 'Work out how to approach the request.' },
  { key: 'create', label: 'Create', description: 'Make and prepare the changes.' },
  { key: 'check', label: 'Check', description: 'Test the result and run final checks.' },
  { key: 'review', label: 'Review', description: 'Review the finished result before anything moves further.' },
] as const;

function runStageKey(run: EngineeringRunDto | null): string | null {
  if (!run) return null;
  if (['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'].includes(run.state)) return run.state;
  if (run.resume_stage && ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'].includes(run.resume_stage)) return run.resume_stage;
  return null;
}

function journeyIndexForStage(stage: string | null): number {
  if (stage === 'SPECIFY') return 0;
  if (stage === 'PLAN') return 1;
  if (stage === 'IMPLEMENT' || stage === 'BUILD') return 2;
  if (stage === 'TEST' || stage === 'VERIFY') return 3;
  if (stage === 'REVIEW') return 4;
  return 1;
}

function currentJourneyIndex(specification: WorkSpecificationDto | null, run: EngineeringRunDto | null): number {
  if (!specification || specification.status !== 'APPROVED') return 0;
  if (!run) return 1;
  if (run.state === 'COMPLETE') return JOURNEY_STEPS.length - 1;
  return journeyIndexForStage(runStageKey(run));
}

function journeyStatus(index: number, specification: WorkSpecificationDto | null, run: EngineeringRunDto | null): StageStatus {
  if (index === 0) {
    if (specification?.status === 'APPROVED') return 'complete';
    return 'current';
  }
  if (!specification || specification.status !== 'APPROVED') return 'pending';
  if (!run) return index === 1 ? 'next' : 'pending';
  if (run.state === 'COMPLETE') return 'complete';

  const currentIndex = currentJourneyIndex(specification, run);
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
  if (status === 'next') return '→';
  return '○';
}

function stageStatusText(status: StageStatus): string {
  if (status === 'complete') return 'Done';
  if (status === 'failed') return 'Needs attention';
  if (status === 'paused') return 'Paused';
  if (status === 'cancelled') return 'Stopped';
  if (status === 'current') return 'In progress';
  if (status === 'next') return 'Up next';
  return 'Later';
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
  const runFailure = useEngineeringRunFailure(run?.conversation_id);
  const effectiveError = runFailure?.message ?? error;
  const currentIndex = currentJourneyIndex(specification, run);
  const currentStep = JOURNEY_STEPS[currentIndex] ?? JOURNEY_STEPS[0]!;
  const retryableFailure = Boolean(runFailure || run?.state === 'FAILED');
  const currentActivity = retryableFailure
    ? 'Something needs attention'
    : specification?.status === 'DRAFT'
      ? 'Your build plan needs your review'
      : run
        ? friendlyRunState(run)
        : specification?.status === 'APPROVED'
          ? 'Your plan is approved and ready'
          : 'Start by defining what you want';
  const complete = run?.state === 'COMPLETE';

  return (
    <ScrollView style={styles.screenScroll} contentContainerStyle={styles.screenContent} testID="mobile-build-workspace">
      <Text style={styles.screenKicker}>YOUR PROGRESS</Text>
      <Text style={styles.screenTitle}>Where things stand</Text>
      <Text style={styles.screenCopy}>Stay on one screen while Parallax moves through the work. You can see what is finished, what is happening now, and what comes next.</Text>

      <View style={styles.orientationCard} accessibilityLabel={`Current progress: ${complete ? 'complete' : `step ${currentIndex + 1} of ${JOURNEY_STEPS.length}`}`}>
        <View style={styles.orientationTopRow}>
          <Text style={styles.detailLabel}>{complete ? 'COMPLETE' : `STEP ${currentIndex + 1} OF ${JOURNEY_STEPS.length}`}</Text>
          <Text style={styles.orientationStepName}>{complete ? 'Finished' : currentStep.label}</Text>
        </View>
        <View style={styles.progressTrack} accessibilityElementsHidden>
          {JOURNEY_STEPS.map((step, index) => {
            const status = journeyStatus(index, specification, run);
            const active = status === 'current' || status === 'next' || status === 'failed' || status === 'paused' || status === 'cancelled';
            return <View key={step.key} style={[styles.progressSegment, status === 'complete' && styles.progressSegmentComplete, active && styles.progressSegmentActive]} />;
          })}
        </View>
        <Text style={styles.orientationDescription}>{complete ? 'Parallax finished the work and the result is ready.' : currentStep.description}</Text>
      </View>

      <View style={styles.activityCard}>
        <Text style={styles.detailLabel}>RIGHT NOW</Text>
        <Text style={styles.activityTitle}>{currentActivity}</Text>
        {retryableFailure ? <Text style={styles.activityCopy}>Parallax stopped safely. Your saved work is still here, and you can retry this step.</Text> : run?.last_failure_code ? <Text style={styles.activityCopy}>Something needs attention before Parallax can continue.</Text> : null}
        {plainError(effectiveError) ? <Text accessibilityLiveRegion="polite" style={styles.error}>{plainError(effectiveError)}</Text> : null}
        {retryableFailure && run ? (
          <TouchableOpacity
            accessibilityRole="button"
            accessibilityLabel="Try again"
            accessibilityState={{ disabled: busy }}
            disabled={busy}
            onPress={() => requestEngineeringRunRetry(run.conversation_id)}
            style={styles.primaryButton}
          >
            <Text style={styles.primaryButtonText}>{busy ? 'Trying again…' : 'Try again'}</Text>
          </TouchableOpacity>
        ) : !specification && canDraft ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Create build plan" disabled={busy} onPress={onCaptureSpecification} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>{busy ? 'Creating plan…' : 'Create build plan'}</Text>
          </TouchableOpacity>
        ) : specification?.status === 'DRAFT' ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Review build plan" onPress={onReviewSpecification} style={styles.primaryButton}>
            <Text style={styles.primaryButtonText}>Review build plan</Text>
          </TouchableOpacity>
        ) : run ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Open technical build details" onPress={onOpenDetails} style={styles.secondaryButton}>
            <Text style={styles.secondaryButtonText}>Open detailed view</Text>
          </TouchableOpacity>
        ) : null}
      </View>

      <View style={styles.lifecycleCard}>
        <Text style={styles.detailLabel}>THE JOURNEY</Text>
        {JOURNEY_STEPS.map((step, index) => {
          const status = journeyStatus(index, specification, run);
          return (
            <View key={step.key} style={[styles.stageRow, index === JOURNEY_STEPS.length - 1 && styles.stageRowLast]}>
              <View style={[styles.stageMarker, status === 'complete' && styles.stageMarkerComplete, (status === 'current' || status === 'next') && styles.stageMarkerCurrent, status === 'failed' && styles.stageMarkerFailed]}>
                <Text style={styles.stageMarkerText}>{stageMarker(status)}</Text>
              </View>
              <View style={styles.stageCopy}>
                <Text style={styles.stageTitle}>{step.label}</Text>
                <Text style={styles.stageMeta}>{stageStatusText(status)} · {step.description}</Text>
              </View>
            </View>
          );
        })}
      </View>

      <TechnicalDetails label="Technical details and evidence">
        <Text selectable style={styles.technicalLine}>System stage: {run?.state ?? 'Not started'}</Text>
        {run?.resume_stage ? <Text selectable style={styles.technicalLine}>Resume stage: {run.resume_stage}</Text> : null}
        {run?.last_failure_code ? <Text selectable style={styles.technicalLine}>Issue code: {run.last_failure_code}</Text> : null}
        {effectiveError ? <Text selectable style={styles.technicalLine}>System message: {effectiveError}</Text> : null}
        {run?.attempts?.length ? (
          <View style={styles.attemptList}>
            <Text style={styles.technicalHeading}>Recent attempts</Text>
            {run.attempts.slice(-3).reverse().map((attempt) => (
              <View key={attempt.id} style={styles.attemptRow}>
                <Text selectable style={styles.attemptStage}>{attempt.stage}</Text>
                <Text selectable style={styles.attemptMeta}>{attempt.status}{attempt.failure_code ? ` · ${attempt.failure_code}` : ''}</Text>
              </View>
            ))}
          </View>
        ) : <Text style={styles.technicalMuted}>No detailed attempt records yet.</Text>}
        {run ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Open full technical build details" onPress={onOpenDetails} style={styles.textButton}>
            <Text style={styles.textButtonText}>Open full technical details</Text>
          </TouchableOpacity>
        ) : null}
      </TechnicalDetails>
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
    ? 'This is an older conversation that is not linked to a current project.'
    : activeProjectId
      ? 'This conversation belongs to this project.'
      : displayProject
        ? 'This project is selected for your next build.'
        : 'Choose a project before starting a build.';

  return (
    <ScrollView style={styles.screenScroll} contentContainerStyle={styles.screenContent} testID="mobile-project-workspace">
      <Text style={styles.screenKicker}>CURRENT PROJECT</Text>
      <Text style={styles.screenTitle}>Your workspace</Text>
      <Text style={styles.screenCopy}>See what project you are in, return to a recent conversation, or start something new.</Text>

      <View style={styles.projectCard}>
        <Text style={styles.detailLabel}>{activeProjectId ? 'YOU ARE WORKING IN' : 'SELECTED PROJECT'}</Text>
        <Text style={styles.projectTitle}>{projectTitle}</Text>
        <Text style={styles.projectMeta}>{projectCaption}</Text>
        <Text numberOfLines={2} style={styles.projectConversation}>{activeConversation?.title ?? 'No conversation selected'}</Text>
        <Text style={styles.projectConversationMeta}>{activeConversation?.mode === 'code' ? 'Build conversation' : 'Ask conversation'}</Text>
        {!projectCompatibility.historical ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel={displayProject ? 'Change project' : 'Choose project'} onPress={projectCompatibility.openProjectSelector} style={styles.changeProjectButton}>
            <Text style={styles.changeProjectButtonText}>{displayProject ? 'Change project' : 'Choose project'}</Text>
          </TouchableOpacity>
        ) : null}
        <TechnicalDetails>
          <Text selectable style={styles.technicalLine}>Project ID: {activeProjectId ?? displayProject?.id ?? 'None'}</Text>
          <Text selectable style={styles.technicalLine}>Binding status: {activeConversation?.project_binding_status ?? 'None'}</Text>
        </TechnicalDetails>
      </View>

      <View style={styles.newActionRow}>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Ask something" onPress={onStartAsk} style={styles.secondaryActionTile}>
          <Text style={styles.secondaryActionTitle}>Ask something</Text>
          <Text style={styles.secondaryActionCopy}>Explore, plan, or talk through an idea.</Text>
        </TouchableOpacity>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Build something" onPress={onStartBuild} style={styles.primaryActionTile}>
          <Text style={styles.primaryActionTitle}>Build something</Text>
          <Text style={styles.primaryActionCopy}>Create or change an application.</Text>
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
const mono = Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' : undefined;

const styles = StyleSheet.create({
  header: { minHeight: 78, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, paddingHorizontal: 12, paddingVertical: 10, backgroundColor: 'rgba(251,247,238,0.98)', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  headerWebAccountSpace: { paddingRight: 68 },
  headerIdentity: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center', gap: 10 },
  headerCopy: { flex: 1, minWidth: 0 },
  brand: { color: palette.charcoal950, fontSize: 20, lineHeight: 23, fontWeight: '700', fontFamily: serif },
  projectLabel: { color: palette.olive700, fontSize: 14, lineHeight: 18, fontWeight: '700', marginTop: 1 },
  conversationLabel: { color: palette.charcoal600, fontSize: 13, lineHeight: 17, marginTop: 1 },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  modeSwitch: { minHeight: 48, padding: 3, flexDirection: 'row', alignItems: 'center', borderRadius: 15, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  modeButton: { minWidth: 48, minHeight: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 },
  modeButtonActive: { backgroundColor: palette.rust600 },
  modeText: { color: palette.charcoal600, fontSize: 14, lineHeight: 18, fontWeight: '800' },
  modeTextActive: { color: palette.ivory50 },
  newButton: { width: 46, height: 46, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.cream200 },
  newButtonText: { color: palette.rust700, fontSize: 22, lineHeight: 24 },
  bottomNav: { minHeight: 70, flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 10, paddingTop: 8, paddingBottom: 10, backgroundColor: 'rgba(245,238,223,0.99)', borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  bottomNavItem: { flex: 1, minHeight: 52, alignItems: 'center', justifyContent: 'center', borderRadius: 16 },
  bottomNavItemActive: { backgroundColor: palette.rust100 },
  bottomNavLabelRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  bottomNavText: { color: palette.charcoal600, fontSize: 14, lineHeight: 18, fontWeight: '800' },
  bottomNavTextActive: { color: palette.rust700 },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: palette.teal600 },
  contextCard: { marginBottom: 24, padding: 19, borderRadius: 21, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  amendmentCard: { marginBottom: 24, padding: 19, borderRadius: 21, backgroundColor: palette.rust100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(168,59,23,0.18)' },
  contextEyebrow: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.7, marginBottom: 7 },
  contextTitle: { color: palette.charcoal950, fontSize: 21, lineHeight: 27, fontWeight: '700', letterSpacing: -0.3 },
  contextCopy: { color: palette.charcoal600, fontSize: 16, lineHeight: 24, marginTop: 7 },
  primaryButton: { minHeight: 50, marginTop: 16, borderRadius: 15, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, backgroundColor: palette.rust600 },
  primaryButtonLarge: { minHeight: 54, marginTop: 26, borderRadius: 16, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18, backgroundColor: palette.rust600 },
  primaryButtonText: { color: palette.ivory50, fontSize: 15, lineHeight: 20, fontWeight: '800' },
  secondaryButton: { minHeight: 50, marginTop: 10, borderRadius: 15, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 16, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  secondaryButtonLarge: { minHeight: 52, marginTop: 10, borderRadius: 16, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  secondaryButtonText: { color: palette.charcoal800, fontSize: 15, lineHeight: 20, fontWeight: '800' },
  textButton: { minHeight: 46, marginTop: 8, alignItems: 'center', justifyContent: 'center' },
  textButtonText: { color: palette.teal700, fontSize: 14, lineHeight: 18, fontWeight: '800' },
  error: { color: palette.danger, fontSize: 14, lineHeight: 20, marginTop: 11 },
  detailRoot: { flex: 1, minHeight: 0, backgroundColor: palette.ivory50 },
  detailHeader: { minHeight: 80, flexDirection: 'row', alignItems: 'center', gap: 11, paddingHorizontal: 13, paddingVertical: 10, backgroundColor: palette.cream100, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  backButton: { minWidth: 72, minHeight: 48, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  backButtonText: { color: palette.teal700, fontSize: 14, lineHeight: 18, fontWeight: '800' },
  detailHeaderCopy: { flex: 1, minWidth: 0 },
  detailHeaderTitle: { color: palette.charcoal950, fontSize: 19, lineHeight: 24, fontWeight: '700' },
  detailScroll: { flex: 1, minHeight: 0 },
  detailContent: { paddingHorizontal: 19, paddingTop: 24, paddingBottom: 40 },
  detailSection: { marginBottom: 25 },
  detailLabel: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.75, marginBottom: 9 },
  detailObjective: { color: palette.charcoal950, fontSize: 18, lineHeight: 28 },
  detailItem: { color: palette.charcoal600, fontSize: 16, lineHeight: 25, marginBottom: 8 },
  inlineNotice: { marginBottom: 22, padding: 16, borderRadius: 17, backgroundColor: palette.rust100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(168,59,23,0.16)' },
  inlineNoticeTitle: { color: palette.charcoal950, fontSize: 16, lineHeight: 21, fontWeight: '800' },
  inlineNoticeCopy: { color: palette.charcoal600, fontSize: 15, lineHeight: 22, marginTop: 5 },
  planStateCard: { marginTop: 2, padding: 16, borderRadius: 17, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  planStateTitle: { color: palette.charcoal950, fontSize: 17, lineHeight: 22, fontWeight: '800' },
  planStateCopy: { color: palette.charcoal600, fontSize: 15, lineHeight: 22, marginTop: 5 },
  screenScroll: { flex: 1, minHeight: 0 },
  screenContent: { paddingHorizontal: 18, paddingTop: 24, paddingBottom: 42 },
  screenKicker: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.85 },
  screenTitle: { color: palette.charcoal950, fontSize: 31, lineHeight: 37, fontWeight: '600', letterSpacing: -0.85, fontFamily: serif, marginTop: 5 },
  screenCopy: { color: palette.charcoal600, fontSize: 16, lineHeight: 24, marginTop: 9, marginBottom: 20 },
  orientationCard: { padding: 18, borderRadius: 21, backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(0,132,135,0.18)', marginBottom: 14 },
  orientationTopRow: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', gap: 12 },
  orientationStepName: { color: palette.teal700, fontSize: 17, lineHeight: 22, fontWeight: '800' },
  progressTrack: { height: 8, flexDirection: 'row', gap: 5, marginTop: 12, marginBottom: 12 },
  progressSegment: { flex: 1, borderRadius: 999, backgroundColor: 'rgba(98,102,100,0.18)' },
  progressSegmentComplete: { backgroundColor: palette.olive600 },
  progressSegmentActive: { backgroundColor: palette.teal600 },
  orientationDescription: { color: palette.charcoal800, fontSize: 15, lineHeight: 22 },
  activityCard: { padding: 18, borderRadius: 21, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, marginBottom: 14 },
  activityTitle: { color: palette.charcoal950, fontSize: 21, lineHeight: 27, fontWeight: '700' },
  activityCopy: { color: palette.charcoal600, fontSize: 15, lineHeight: 22, marginTop: 6 },
  lifecycleCard: { paddingHorizontal: 17, paddingTop: 17, paddingBottom: 5, borderRadius: 21, backgroundColor: '#FFFDF8', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, marginBottom: 14 },
  stageRow: { minHeight: 70, flexDirection: 'row', alignItems: 'center', gap: 13, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border, paddingVertical: 8 },
  stageRowLast: { borderBottomWidth: 0 },
  stageMarker: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.cream200 },
  stageMarkerComplete: { backgroundColor: palette.olive200 },
  stageMarkerCurrent: { backgroundColor: palette.teal100 },
  stageMarkerFailed: { backgroundColor: palette.rust100 },
  stageMarkerText: { color: palette.charcoal800, fontSize: 15, lineHeight: 18, fontWeight: '800' },
  stageCopy: { flex: 1, minWidth: 0 },
  stageTitle: { color: palette.charcoal950, fontSize: 17, lineHeight: 22, fontWeight: '800' },
  stageMeta: { color: palette.charcoal600, fontSize: 14, lineHeight: 20, marginTop: 2 },
  technicalDisclosure: { marginTop: 12, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border, paddingTop: 6 },
  technicalToggle: { minHeight: 48, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  technicalToggleText: { color: palette.teal700, fontSize: 14, lineHeight: 18, fontWeight: '800' },
  technicalChevron: { color: palette.teal700, fontSize: 18, lineHeight: 20, fontWeight: '800' },
  technicalBody: { padding: 14, borderRadius: 15, backgroundColor: palette.cream150, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  technicalHeading: { color: palette.charcoal950, fontSize: 14, lineHeight: 18, fontWeight: '800', marginTop: 8, marginBottom: 6 },
  technicalLine: { color: palette.charcoal800, fontSize: 12, lineHeight: 18, fontFamily: mono, marginBottom: 4 },
  technicalMuted: { color: palette.charcoal600, fontSize: 13, lineHeight: 19 },
  attemptList: { marginTop: 6 },
  attemptRow: { minHeight: 48, paddingVertical: 8, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  attemptStage: { color: palette.charcoal950, fontSize: 13, lineHeight: 18, fontWeight: '800', fontFamily: mono },
  attemptMeta: { color: palette.charcoal600, fontSize: 12, lineHeight: 18, marginTop: 2, fontFamily: mono },
  projectCard: { padding: 18, borderRadius: 21, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, marginBottom: 14 },
  projectTitle: { color: palette.charcoal950, fontSize: 22, lineHeight: 28, fontWeight: '700' },
  projectMeta: { color: palette.olive700, fontSize: 15, lineHeight: 22, fontWeight: '700', marginTop: 7 },
  projectConversation: { color: palette.charcoal800, fontSize: 16, lineHeight: 23, marginTop: 14 },
  projectConversationMeta: { color: palette.charcoal600, fontSize: 14, lineHeight: 19, marginTop: 5 },
  changeProjectButton: { minHeight: 50, marginTop: 16, alignItems: 'center', justifyContent: 'center', borderRadius: 15, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  changeProjectButtonText: { color: palette.teal700, fontSize: 15, lineHeight: 20, fontWeight: '800' },
  newActionRow: { flexDirection: 'row', gap: 11, marginBottom: 24 },
  secondaryActionTile: { flex: 1, minHeight: 116, padding: 16, borderRadius: 18, justifyContent: 'center', backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  primaryActionTile: { flex: 1, minHeight: 116, padding: 16, borderRadius: 18, justifyContent: 'center', backgroundColor: palette.rust600 },
  secondaryActionTitle: { color: palette.charcoal950, fontSize: 16, lineHeight: 21, fontWeight: '800' },
  secondaryActionCopy: { color: palette.charcoal600, fontSize: 14, lineHeight: 20, marginTop: 5 },
  primaryActionTitle: { color: palette.ivory50, fontSize: 16, lineHeight: 21, fontWeight: '800' },
  primaryActionCopy: { color: 'rgba(251,247,238,0.86)', fontSize: 14, lineHeight: 20, marginTop: 5 },
  conversationList: { marginBottom: 12 },
  conversationRow: { minHeight: 68, flexDirection: 'row', alignItems: 'center', gap: 11, paddingHorizontal: 15, paddingVertical: 11, borderRadius: 16, marginBottom: 8, backgroundColor: '#FFFDF8', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  conversationRowSelected: { backgroundColor: palette.teal100, borderColor: 'rgba(0,132,135,0.24)' },
  conversationRowCopy: { flex: 1, minWidth: 0 },
  conversationTitle: { color: palette.charcoal950, fontSize: 16, lineHeight: 21, fontWeight: '700' },
  conversationMeta: { color: palette.charcoal600, fontSize: 13, lineHeight: 18, marginTop: 3 },
  chevron: { color: palette.charcoal450, fontSize: 24, lineHeight: 26 },
});