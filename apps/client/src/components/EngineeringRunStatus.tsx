import React from 'react';
import { Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { authenticatedRequest, type EngineeringRunDto } from '../lib/api';
import {
  getEngineeringRunFailure,
  subscribeEngineeringRunFailures,
} from '../lib/engineeringRunEvents';
import { palette } from '../theme';
import { ReviewReworkPanel } from './ReviewReworkPanel';

const RAW_STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'];
const AUTONOMOUS_STAGES = ['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY'];
const DELIVERY_MUTABLE_STAGES = ['SPECIFY', 'PLAN'];
type EngineeringRunView = EngineeringRunDto & { autonomy_stop_reason?: string | null };
type JourneyStatus = 'complete' | 'current' | 'pending' | 'failed' | 'paused' | 'cancelled';
type DeliveryMode = 'source-only' | 'vercel-preview';

const JOURNEY = [
  { key: 'define', label: 'Define', description: 'Agree on the goal and what success looks like.' },
  { key: 'plan', label: 'Plan', description: 'Work out the approach.' },
  { key: 'create', label: 'Create', description: 'Make and prepare the changes.' },
  { key: 'check', label: 'Check', description: 'Test the result and run final checks.' },
  { key: 'review', label: 'Review', description: 'Review the finished result before anything moves further.' },
] as const;

function useEngineeringRunFailure(conversationId: string) {
  const subscribe = React.useCallback((listener: () => void) => subscribeEngineeringRunFailures(listener), []);
  const getSnapshot = React.useCallback(() => getEngineeringRunFailure(conversationId), [conversationId]);
  return React.useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

function rawStage(run: EngineeringRunDto): string | null {
  if (RAW_STAGES.includes(run.state)) return run.state;
  if (run.resume_stage && RAW_STAGES.includes(run.resume_stage)) return run.resume_stage;
  return null;
}

function journeyIndex(stage: string | null): number {
  if (stage === 'SPECIFY') return 0;
  if (stage === 'PLAN') return 1;
  if (stage === 'IMPLEMENT' || stage === 'BUILD') return 2;
  if (stage === 'TEST' || stage === 'VERIFY') return 3;
  if (stage === 'REVIEW') return 4;
  return 1;
}

function currentJourneyIndex(run: EngineeringRunDto): number {
  if (run.state === 'COMPLETE') return JOURNEY.length - 1;
  return journeyIndex(rawStage(run));
}

function journeyStatus(index: number, run: EngineeringRunDto): JourneyStatus {
  if (run.state === 'COMPLETE') return 'complete';
  const current = currentJourneyIndex(run);
  if (index < current) return 'complete';
  if (index > current) return 'pending';
  if (run.state === 'FAILED') return 'failed';
  if (run.state === 'PAUSED') return 'paused';
  if (run.state === 'CANCELLED') return 'cancelled';
  return 'current';
}

function friendlyState(run: EngineeringRunDto): string {
  if (run.state === 'COMPLETE') return 'Work complete';
  if (run.state === 'REVIEW') return 'Ready for your review';
  if (run.state === 'FAILED') return 'Something needs attention';
  if (run.state === 'PAUSED') return 'Work paused';
  if (run.state === 'CANCELLED') return 'Work stopped';
  const labels: Record<string, string> = {
    SPECIFY: 'Defining the goal',
    PLAN: 'Planning the work',
    IMPLEMENT: 'Making the changes',
    BUILD: 'Preparing the result',
    TEST: 'Checking the result',
    VERIFY: 'Running final checks',
  };
  return labels[run.state] ?? 'Working on your request';
}

function plainRunError(error?: string | null): string | null {
  if (!error) return null;
  const normalized = error.toLowerCase();
  if (normalized.includes("couldn't prepare this project") || normalized.includes('couldn’t prepare this project')) {
    return 'Parallax couldn’t prepare this project for the next step yet. Your saved work is still here. Try again.';
  }
  return 'Parallax couldn’t continue this step. Your saved work is still here. Try again.';
}

function boundaryMessage(run: EngineeringRunDto, stopReason?: string | null): string | null {
  const reported: Record<string, string> = {
    EXECUTOR_UNAVAILABLE: 'Parallax can’t continue right now because the build environment is unavailable. Nothing was changed.',
    IMPLEMENTATION_REQUIRED: 'The plan is ready and the next step is to make the changes.',
    IMPLEMENTATION_FAILED: 'Parallax could not finish making the changes. Review what happened before continuing.',
    REVIEW_REQUIRED: 'The result is ready for your review.',
    EXECUTION_FAILED: 'Parallax could not complete this step. Review what happened before continuing.',
    PAUSED: 'The work is paused.',
    FAILED: 'Something needs attention before the work can continue.',
    COMPLETE: 'The work is complete.',
    CANCELLED: 'The work was stopped.',
    SPEC_AMENDMENT: 'Your request changed from the approved plan, so Parallax stopped before changing the approved work.',
    MAX_STEPS_REACHED: 'Parallax reached its safe automatic-work limit and needs a review before continuing.',
  };
  if (stopReason && reported[stopReason]) return reported[stopReason] ?? null;
  if (run.state === 'IMPLEMENT') return reported.IMPLEMENTATION_REQUIRED ?? null;
  if (run.state === 'REVIEW') return reported.REVIEW_REQUIRED ?? null;
  if (run.state === 'FAILED') return reported.FAILED ?? null;
  return null;
}

async function readDeliveryMode(projectId: string): Promise<DeliveryMode> {
  const response = await authenticatedRequest(`/v1/projects/${projectId}`);
  if (!response.ok) throw new Error(`Project delivery settings are unavailable (${response.status}).`);
  const payload = await response.json() as { delivery_mode?: unknown };
  if (payload.delivery_mode !== 'source-only' && payload.delivery_mode !== 'vercel-preview') {
    throw new Error('Project delivery settings are invalid.');
  }
  return payload.delivery_mode;
}

async function writeDeliveryMode(projectId: string, deliveryMode: DeliveryMode): Promise<DeliveryMode> {
  const response = await authenticatedRequest(`/v1/projects/${projectId}/delivery`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ delivery_mode: deliveryMode }),
  });
  if (!response.ok) {
    let message = `Delivery setting could not be changed (${response.status}).`;
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === 'string' && payload.detail.trim()) message = payload.detail;
    } catch {
      // Keep the bounded status fallback.
    }
    throw new Error(message);
  }
  const payload = await response.json() as { delivery_mode?: unknown };
  if (payload.delivery_mode !== 'source-only' && payload.delivery_mode !== 'vercel-preview') {
    throw new Error('Project delivery settings are invalid.');
  }
  return payload.delivery_mode;
}

async function downloadAcceptedSource(projectId: string, runId: string): Promise<void> {
  if (Platform.OS !== 'web') throw new Error('Source download is available from the web or desktop app.');
  const response = await authenticatedRequest(`/v1/projects/${projectId}/engineering-runs/${runId}/source-download`);
  if (!response.ok) {
    let message = `Source download is unavailable (${response.status}).`;
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === 'string' && payload.detail.trim()) message = payload.detail;
    } catch {
      // Binary or empty error responses keep the status fallback.
    }
    throw new Error(message);
  }
  const body = await response.blob();
  const disposition = response.headers.get('content-disposition') ?? '';
  const match = disposition.match(/filename="([^"]+)"/i);
  const filename = match?.[1] ?? `parallax-source-${runId.slice(0, 8)}.zip`;
  const objectUrl = URL.createObjectURL(body);
  try {
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function TechnicalDetails({ run, stopReason, error }: { run: EngineeringRunDto; stopReason?: string | null; error?: string | null }) {
  const [open, setOpen] = React.useState(false);
  const passed = run.attempts.filter((item) => item.status === 'PASSED').map((item) => item.stage);
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
          <Text selectable style={styles.technicalLine}>System object: Engineering Run</Text>
          <Text selectable style={styles.technicalLine}>Run state: {run.state}</Text>
          {run.resume_stage ? <Text selectable style={styles.technicalLine}>Resume stage: {run.resume_stage}</Text> : null}
          <Text selectable style={styles.technicalLine}>Spec ID: {run.spec_id}</Text>
          <Text selectable style={styles.technicalLine}>Binding: {run.binding_status}</Text>
          <Text selectable style={styles.technicalLine}>Work Specification revision: {run.work_specification_revision ?? 'None'}</Text>
          <Text selectable style={styles.technicalLine}>Acceptance criteria: {run.acceptance_criteria.length}</Text>
          <Text selectable style={styles.technicalLine}>Passed stages: {passed.length ? passed.join(' · ') : 'None yet'}</Text>
          {run.last_failure_code ? <Text selectable style={styles.technicalLine}>Issue code: {run.last_failure_code}</Text> : null}
          {stopReason ? <Text selectable style={styles.technicalLine}>Stop reason: {stopReason}</Text> : null}
          {error ? <Text selectable style={styles.technicalLine}>Last request error: {error}</Text> : null}
        </View>
      ) : null}
    </View>
  );
}

export function EngineeringRunStatus({ run, busy, error, onPause, onResume, onCancel, onRequestChanges }: {
  run: EngineeringRunDto;
  busy: boolean;
  error?: string | null;
  onPause(): void;
  onResume(): void;
  onCancel(): void;
  onRequestChanges(acceptanceIds: string[], finding: string): void;
  reducedGraphics?: boolean;
}) {
  const storedFailure = useEngineeringRunFailure(run.conversation_id);
  const effectiveError = error ?? storedFailure?.message ?? null;
  const bound = run.binding_status === 'APPROVED_SPEC_BOUND';
  const canPause = bound && RAW_STAGES.includes(run.state);
  const canResume = bound && (run.state === 'PAUSED' || run.state === 'FAILED');
  const canRunAutonomously = bound && AUTONOMOUS_STAGES.includes(run.state);
  const stopReason = (run as EngineeringRunView).autonomy_stop_reason;
  const boundary = boundaryMessage(run, stopReason);
  const requestError = storedFailure?.code === 'REPOSITORY_AUTHORIZATION_REQUIRED'
    ? 'This repository needs one-time provider permission before Parallax can continue. Grant access to this exact repository in your connected GitHub provider, then choose Try again. Your current run is preserved.'
    : plainRunError(effectiveError);
  const currentIndex = currentJourneyIndex(run);
  const currentStep = JOURNEY[currentIndex] ?? JOURNEY[0]!;
  const complete = run.state === 'COMPLETE';
  const [deliveryMode, setDeliveryMode] = React.useState<DeliveryMode | null>(null);
  const [deliveryBusy, setDeliveryBusy] = React.useState(false);
  const [deliveryError, setDeliveryError] = React.useState<string | null>(null);
  const projectId = run.project_id;
  const canChangeDelivery = Boolean(projectId) && bound && DELIVERY_MUTABLE_STAGES.includes(run.state);
  const canDownloadSource = Boolean(projectId) && run.state === 'REVIEW' && deliveryMode === 'source-only' && Platform.OS === 'web';

  React.useEffect(() => {
    let cancelled = false;
    if (!projectId) {
      setDeliveryMode(null);
      setDeliveryError(null);
      return () => { cancelled = true; };
    }
    void readDeliveryMode(projectId)
      .then((mode) => {
        if (!cancelled) {
          setDeliveryMode(mode);
          setDeliveryError(null);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled) setDeliveryError(cause instanceof Error ? cause.message : 'Delivery settings are unavailable.');
      });
    return () => { cancelled = true; };
  }, [projectId, run.state]);

  const chooseDelivery = React.useCallback(async (nextMode: DeliveryMode) => {
    if (!projectId || deliveryBusy || !canChangeDelivery || nextMode === deliveryMode) return;
    setDeliveryBusy(true);
    setDeliveryError(null);
    try {
      setDeliveryMode(await writeDeliveryMode(projectId, nextMode));
    } catch (cause) {
      setDeliveryError(cause instanceof Error ? cause.message : 'Delivery setting could not be changed.');
    } finally {
      setDeliveryBusy(false);
    }
  }, [canChangeDelivery, deliveryBusy, deliveryMode, projectId]);

  const downloadSource = React.useCallback(async () => {
    if (!projectId || deliveryBusy || !canDownloadSource) return;
    setDeliveryBusy(true);
    setDeliveryError(null);
    try {
      await downloadAcceptedSource(projectId, run.id);
    } catch (cause) {
      setDeliveryError(cause instanceof Error ? cause.message : 'Source download failed.');
    } finally {
      setDeliveryBusy(false);
    }
  }, [canDownloadSource, deliveryBusy, projectId, run.id]);

  return (
    <View style={styles.card} accessibilityLabel={`Progress: ${friendlyState(run)}`}>
      <View style={styles.kickerRow}>
        <Text style={styles.kicker}>PROGRESS</Text>
        <Text style={styles.stepCount}>{complete ? 'COMPLETE' : `STEP ${currentIndex + 1} OF ${JOURNEY.length}`}</Text>
      </View>
      <Text style={styles.title}>{friendlyState(run)}</Text>
      <Text style={[styles.planStatus, !bound && styles.planStatusWarning]}>
        {bound ? 'Following your approved plan' : 'Older work · view only'}
      </Text>

      <View style={styles.progressTrack} accessibilityLabel={`Current step: ${currentStep.label}`}>
        {JOURNEY.map((step, index) => {
          const status = journeyStatus(index, run);
          return <View key={step.key} style={[styles.progressSegment, status === 'complete' && styles.progressSegmentComplete, (status === 'current' || status === 'failed' || status === 'paused' || status === 'cancelled') && styles.progressSegmentCurrent]} />;
        })}
      </View>

      <View style={styles.journey}>
        {JOURNEY.map((step, index) => {
          const status = journeyStatus(index, run);
          const stateText = status === 'complete' ? 'Done' : status === 'current' ? 'In progress' : status === 'failed' ? 'Needs attention' : status === 'paused' ? 'Paused' : status === 'cancelled' ? 'Stopped' : 'Later';
          return (
            <View key={step.key} style={styles.journeyStep}>
              <View style={[styles.journeyDot, status === 'complete' && styles.journeyDotComplete, status !== 'pending' && status !== 'complete' && styles.journeyDotCurrent]} />
              <View style={styles.journeyCopy}>
                <Text style={styles.journeyTitle}>{step.label}</Text>
                <Text style={styles.journeyMeta}>{stateText}</Text>
              </View>
            </View>
          );
        })}
      </View>

      <Text style={styles.currentDescription}>{complete ? 'Parallax finished the work and the result is ready.' : currentStep.description}</Text>
      {boundary ? <Text style={styles.boundary} accessibilityLiveRegion="polite">{boundary}</Text> : null}
      {requestError ? <Text style={styles.requestError} accessibilityLiveRegion="polite">{requestError}</Text> : null}
      {!bound ? <Text style={styles.warning}>This older work is saved for reference, but it cannot continue as approved work.</Text> : null}

      {projectId && deliveryMode ? (
        <View style={styles.deliveryPanel} accessibilityLabel="Project delivery">
          <View style={styles.deliveryHeader}>
            <Text style={styles.deliveryKicker}>DELIVERY</Text>
            {!canChangeDelivery ? <Text style={styles.deliveryLocked}>SET FOR THIS BUILD</Text> : null}
          </View>
          <Text style={styles.deliveryTitle}>
            {deliveryMode === 'source-only' ? 'Download source' : 'Vercel Preview'}
          </Text>
          <Text style={styles.deliveryCopy}>
            {deliveryMode === 'source-only'
              ? 'Keep the verified result in Parallax so it can be downloaded and deployed to IIS, locally, or somewhere else.'
              : 'Publish the verified result through the configured Vercel Preview path.'}
          </Text>
          {canChangeDelivery ? (
            <View style={styles.deliveryChoices}>
              <TouchableOpacity
                accessibilityRole="button"
                accessibilityLabel="Use downloadable source delivery"
                accessibilityState={{ selected: deliveryMode === 'source-only', disabled: deliveryBusy }}
                disabled={deliveryBusy}
                onPress={() => void chooseDelivery('source-only')}
                style={[styles.deliveryChoice, deliveryMode === 'source-only' && styles.deliveryChoiceSelected]}
              >
                <Text style={[styles.deliveryChoiceText, deliveryMode === 'source-only' && styles.deliveryChoiceTextSelected]}>Download source</Text>
                <Text style={styles.deliveryChoiceMeta}>IIS · local · other</Text>
              </TouchableOpacity>
              <TouchableOpacity
                accessibilityRole="button"
                accessibilityLabel="Use Vercel Preview delivery"
                accessibilityState={{ selected: deliveryMode === 'vercel-preview', disabled: deliveryBusy }}
                disabled={deliveryBusy}
                onPress={() => void chooseDelivery('vercel-preview')}
                style={[styles.deliveryChoice, deliveryMode === 'vercel-preview' && styles.deliveryChoiceSelected]}
              >
                <Text style={[styles.deliveryChoiceText, deliveryMode === 'vercel-preview' && styles.deliveryChoiceTextSelected]}>Vercel Preview</Text>
                <Text style={styles.deliveryChoiceMeta}>Hosted preview</Text>
              </TouchableOpacity>
            </View>
          ) : null}
          {canDownloadSource ? (
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Download verified source"
              disabled={deliveryBusy}
              onPress={() => void downloadSource()}
              style={[styles.downloadButton, deliveryBusy && styles.disabledButton]}
            >
              <Text style={styles.downloadButtonText}>{deliveryBusy ? 'Preparing download…' : 'Download verified source'}</Text>
            </TouchableOpacity>
          ) : null}
          {run.state === 'REVIEW' && deliveryMode === 'source-only' && Platform.OS !== 'web' ? (
            <Text style={styles.deliveryHint}>Open this project on web or desktop to download the verified source package.</Text>
          ) : null}
          {deliveryError ? <Text accessibilityLiveRegion="polite" style={styles.requestError}>{deliveryError}</Text> : null}
        </View>
      ) : null}

      {run.state === 'REVIEW' ? (
        <ReviewReworkPanel run={run} busy={busy} onRequestChanges={onRequestChanges} />
      ) : null}

      <View style={styles.actions}>
        {canRunAutonomously && <TouchableOpacity accessibilityRole="button" accessibilityLabel={effectiveError ? 'Try again' : 'Continue work'} accessibilityState={{ disabled: busy }} disabled={busy} onPress={onResume} style={[styles.actionButton, styles.primaryButton]}><Text style={styles.primaryAction}>{busy ? 'Continuing…' : effectiveError ? 'Try again' : 'Continue work'}</Text></TouchableOpacity>}
        {canPause && <TouchableOpacity accessibilityRole="button" accessibilityLabel="Pause work" disabled={busy} onPress={onPause} style={styles.actionButton}><Text style={styles.action}>Pause</Text></TouchableOpacity>}
        {canResume && <TouchableOpacity accessibilityRole="button" accessibilityLabel={run.state === 'FAILED' ? 'Try again' : 'Continue work'} disabled={busy} onPress={onResume} style={[styles.actionButton, styles.primaryButton]}><Text style={styles.primaryAction}>{busy ? 'Continuing…' : run.state === 'FAILED' ? 'Try again' : 'Continue work'}</Text></TouchableOpacity>}
        {bound && !['COMPLETE', 'CANCELLED', 'SPEC_AMENDMENT'].includes(run.state) && <TouchableOpacity accessibilityRole="button" accessibilityLabel="Stop work" disabled={busy} onPress={onCancel} style={styles.actionButton}><Text style={styles.action}>Stop</Text></TouchableOpacity>}
      </View>

      <TechnicalDetails run={run} stopReason={stopReason} error={effectiveError} />
    </View>
  );
}

const mono = Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' : undefined;

const styles = StyleSheet.create({
  card: { marginLeft: 28, marginRight: 28, marginTop: 16, padding: 20, borderRadius: 20, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, backgroundColor: 'rgba(245,238,223,0.88)', shadowColor: '#564B38', shadowOpacity: 0.055, shadowRadius: 16, shadowOffset: { width: 0, height: 7 } },
  kickerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 8 },
  kicker: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.8 },
  stepCount: { color: palette.charcoal600, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  title: { color: palette.charcoal950, fontSize: 22, lineHeight: 28, fontWeight: '600', letterSpacing: -0.5 },
  planStatus: { color: palette.olive700, fontSize: 14, lineHeight: 20, marginTop: 6, fontWeight: '700' },
  planStatusWarning: { color: palette.warning },
  progressTrack: { height: 8, flexDirection: 'row', gap: 5, marginTop: 16 },
  progressSegment: { flex: 1, borderRadius: 999, backgroundColor: palette.stone300 },
  progressSegmentComplete: { backgroundColor: palette.olive500 },
  progressSegmentCurrent: { backgroundColor: palette.teal600 },
  journey: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 14 },
  journeyStep: { minWidth: 112, flex: 1, flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 6 },
  journeyDot: { width: 9, height: 9, borderRadius: 5, backgroundColor: palette.stone300 },
  journeyDotComplete: { backgroundColor: palette.olive500 },
  journeyDotCurrent: { backgroundColor: palette.teal600 },
  journeyCopy: { flex: 1, minWidth: 0 },
  journeyTitle: { color: palette.charcoal950, fontSize: 14, lineHeight: 19, fontWeight: '800' },
  journeyMeta: { color: palette.charcoal600, fontSize: 12, lineHeight: 17, marginTop: 1 },
  currentDescription: { color: palette.charcoal600, marginTop: 14, fontSize: 14, lineHeight: 21, maxWidth: 740 },
  boundary: { color: palette.teal700, marginTop: 10, fontSize: 14, lineHeight: 21, fontWeight: '700', maxWidth: 740 },
  requestError: { color: palette.danger, marginTop: 10, fontSize: 14, lineHeight: 21, fontWeight: '700', maxWidth: 740 },
  warning: { color: palette.warning, marginTop: 10, fontSize: 14, lineHeight: 21, maxWidth: 740 },
  deliveryPanel: { marginTop: 16, padding: 14, borderRadius: 15, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, backgroundColor: palette.cream150 },
  deliveryHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  deliveryKicker: { color: palette.olive700, fontSize: 11, lineHeight: 15, fontWeight: '800', letterSpacing: 0.8 },
  deliveryLocked: { color: palette.charcoal600, fontSize: 10, lineHeight: 14, fontWeight: '800', letterSpacing: 0.5 },
  deliveryTitle: { color: palette.charcoal950, fontSize: 16, lineHeight: 21, fontWeight: '800', marginTop: 5 },
  deliveryCopy: { color: palette.charcoal600, fontSize: 13, lineHeight: 19, marginTop: 4, maxWidth: 720 },
  deliveryChoices: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12 },
  deliveryChoice: { minWidth: 150, flexGrow: 1, flexBasis: 180, minHeight: 62, paddingHorizontal: 12, paddingVertical: 10, borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.ivory50 },
  deliveryChoiceSelected: { borderColor: palette.teal600, backgroundColor: 'rgba(36,139,139,0.08)' },
  deliveryChoiceText: { color: palette.charcoal800, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  deliveryChoiceTextSelected: { color: palette.teal700 },
  deliveryChoiceMeta: { color: palette.charcoal600, fontSize: 11, lineHeight: 16, marginTop: 3 },
  downloadButton: { alignSelf: 'flex-start', minHeight: 44, justifyContent: 'center', marginTop: 12, paddingHorizontal: 15, borderRadius: 12, backgroundColor: palette.teal600 },
  downloadButtonText: { color: palette.ivory50, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  disabledButton: { opacity: 0.62 },
  deliveryHint: { color: palette.charcoal600, fontSize: 12, lineHeight: 18, marginTop: 10 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 16 },
  actionButton: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 15, borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.ivory50 },
  primaryButton: { borderColor: palette.teal600, backgroundColor: palette.teal600 },
  action: { color: palette.charcoal800, fontSize: 13, lineHeight: 18, fontWeight: '700' },
  primaryAction: { color: palette.ivory50, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  technicalWrap: { marginTop: 14, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border, paddingTop: 5 },
  technicalToggle: { minHeight: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  technicalToggleText: { color: palette.teal700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  technicalChevron: { color: palette.teal700, fontSize: 18, lineHeight: 20, fontWeight: '800' },
  technicalBody: { padding: 12, borderRadius: 13, backgroundColor: palette.cream150 },
  technicalLine: { color: palette.charcoal800, fontSize: 12, lineHeight: 18, fontFamily: mono, marginBottom: 3 },
});