import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto } from '../lib/api';
import { palette } from '../theme';

const STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'];
const AUTONOMOUS_STAGES = ['PLAN', 'BUILD', 'TEST', 'VERIFY'];
type EngineeringRunView = EngineeringRunDto & { autonomy_stop_reason?: string | null };

function autonomyBoundary(run: EngineeringRunDto, stopReason?: string | null): string | null {
  const reported = {
    EXECUTOR_UNAVAILABLE: 'Autonomy stopped · isolated executor unavailable; no plan state was changed',
    IMPLEMENTATION_REQUIRED: 'Autonomy boundary · implementation evidence required',
    REVIEW_REQUIRED: 'Autonomy boundary · independent review required',
    EXECUTION_FAILED: 'Autonomy stopped · protected execution failed; review the recorded evidence before resuming',
    PAUSED: 'Autonomy stopped · run is paused',
    FAILED: 'Autonomy stopped · run requires an explicit resume after failure',
    COMPLETE: 'Autonomy complete · no further execution is required',
    CANCELLED: 'Autonomy stopped · run was cancelled',
    SPEC_AMENDMENT: 'Autonomy stopped · Work Specification amendment required',
    MAX_STEPS_REACHED: 'Autonomy stopped · bounded cycle limit reached',
  } as const;
  if (stopReason && stopReason in reported) return reported[stopReason as keyof typeof reported];
  if (run.state === 'IMPLEMENT') return reported.IMPLEMENTATION_REQUIRED;
  if (run.state === 'REVIEW') return reported.REVIEW_REQUIRED;
  if (run.state === 'FAILED' && run.last_failure_code?.startsWith('AUTONOMOUS_')) return `Autonomy stopped · ${run.last_failure_code.toLowerCase().split('_').join(' ')}`;
  return null;
}

export function EngineeringRunStatus({ run, busy, onPause, onResume, onCancel }: {
  run: EngineeringRunDto;
  busy: boolean;
  onPause(): void;
  onResume(): void;
  onCancel(): void;
  reducedGraphics?: boolean;
}) {
  const passed = new Set(run.attempts.filter((item) => item.status === 'PASSED').map((item) => item.stage));
  const bound = run.binding_status === 'APPROVED_SPEC_BOUND';
  const canPause = bound && STAGES.includes(run.state);
  const canResume = bound && (run.state === 'PAUSED' || run.state === 'FAILED');
  const canRunAutonomously = bound && AUTONOMOUS_STAGES.includes(run.state);
  const evidence = ['BUILD', 'TEST', 'VERIFY', 'REVIEW'].filter((stage) => passed.has(stage));
  const boundary = autonomyBoundary(run, (run as EngineeringRunView).autonomy_stop_reason);

  return (
    <View style={styles.card} accessibilityLabel={`Engineering run ${run.state}`}>
      <View style={styles.kickerRow}><Text style={styles.kicker}>EXECUTION</Text><Text style={styles.spec}>{run.spec_id}</Text></View>
      <Text style={styles.title}>Code run · {run.state}</Text>
      <Text style={[styles.binding, !bound && styles.bindingWarning]}>
        {bound ? `BOUND · WORK SPEC R${run.work_specification_revision ?? '?'} · ${run.acceptance_criteria.length} ACCEPTANCE CRITERIA` : 'HISTORICAL · NO APPROVED WORK-SPEC BINDING'}
      </Text>
      <View style={styles.pipeline}>
        {STAGES.map((stage) => {
          const state = passed.has(stage) ? 'complete' : stage === run.state ? 'current' : 'pending';
          return (
            <View key={stage} style={styles.stage}>
              <View style={[styles.stageDot, state === 'complete' && styles.stageDotComplete, state === 'current' && styles.stageDotCurrent]} />
              <Text style={[styles.stageText, state === 'current' && styles.stageTextCurrent]}>{stage === 'SPECIFY' ? 'SPEC' : stage}</Text>
            </View>
          );
        })}
      </View>
      <Text style={styles.caption}>Evidence: {evidence.length ? evidence.join(' · ') : 'none yet'}{run.last_failure_code ? ` · ${run.last_failure_code}` : ''}</Text>
      {boundary ? <Text style={styles.autonomyStatus} accessibilityLiveRegion="polite">{boundary}</Text> : null}
      <Text style={bound ? styles.boundary : styles.warning}>{bound ? 'Locked to this approved Work Specification revision. Protected execution authority remains server-owned.' : 'Historical runs remain readable but cannot resume as approved-spec execution evidence.'}</Text>
      <View style={styles.actions}>
        {canRunAutonomously && <TouchableOpacity accessibilityRole="button" accessibilityLabel="Run autonomously" accessibilityState={{ disabled: busy }} disabled={busy} onPress={onResume} style={[styles.actionButton, styles.primaryButton]}><Text style={styles.primaryAction}>{busy ? 'Running…' : 'Run autonomously'}</Text></TouchableOpacity>}
        {canPause && <TouchableOpacity disabled={busy} onPress={onPause} style={styles.actionButton}><Text style={styles.action}>Pause</Text></TouchableOpacity>}
        {canResume && <TouchableOpacity disabled={busy} onPress={onResume} style={styles.actionButton}><Text style={styles.action}>Resume</Text></TouchableOpacity>}
        {bound && !['COMPLETE', 'CANCELLED', 'SPEC_AMENDMENT'].includes(run.state) && <TouchableOpacity disabled={busy} onPress={onCancel} style={styles.actionButton}><Text style={styles.action}>Cancel</Text></TouchableOpacity>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginLeft: 28, marginRight: 28, marginTop: 16, padding: 18, borderRadius: 20, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, backgroundColor: 'rgba(245,238,223,0.88)', shadowColor: '#564B38', shadowOpacity: 0.055, shadowRadius: 16, shadowOffset: { width: 0, height: 7 } },
  kickerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 8 },
  kicker: { color: palette.olive700, fontSize: 9, fontWeight: '800', letterSpacing: 1.1 },
  spec: { color: palette.charcoal450, fontSize: 8, letterSpacing: 0.7 },
  title: { color: palette.charcoal950, fontSize: 21, lineHeight: 26, fontWeight: '600', letterSpacing: -0.5 },
  binding: { color: palette.olive700, fontSize: 9, marginTop: 6, letterSpacing: 0.55, fontWeight: '800' },
  bindingWarning: { color: palette.warning },
  pipeline: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 11, marginTop: 15 },
  stage: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  stageDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: palette.stone300 },
  stageDotComplete: { backgroundColor: palette.olive500 },
  stageDotCurrent: { backgroundColor: palette.teal600 },
  stageText: { color: palette.charcoal450, fontSize: 8, fontWeight: '700', letterSpacing: 0.45 },
  stageTextCurrent: { color: palette.teal700 },
  caption: { color: palette.charcoal600, marginTop: 11, fontSize: 11 },
  autonomyStatus: { color: palette.teal700, marginTop: 8, fontSize: 10, lineHeight: 15, fontWeight: '700' },
  boundary: { color: palette.charcoal600, marginTop: 9, fontSize: 10, lineHeight: 16, maxWidth: 740 },
  warning: { color: palette.warning, marginTop: 9, fontSize: 10, lineHeight: 16, maxWidth: 740 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 14 },
  actionButton: { minHeight: 38, justifyContent: 'center', paddingHorizontal: 13, borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.ivory50 },
  primaryButton: { borderColor: palette.teal600, backgroundColor: palette.teal600 },
  action: { color: palette.charcoal800, fontSize: 10, fontWeight: '700' },
  primaryAction: { color: palette.ivory50, fontSize: 10, fontWeight: '800' },
});
