import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto } from '../lib/api';
import { palette } from '../theme';
import { EditorialTrace } from './EditorialTrace';

const STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'];

export function EngineeringRunStatus({ run, busy, onPause, onResume, onCancel }: {
  run: EngineeringRunDto;
  busy: boolean;
  onPause(): void;
  onResume(): void;
  onCancel(): void;
}) {
  const passed = new Set(run.attempts.filter((item) => item.status === 'PASSED').map((item) => item.stage));
  const bound = run.binding_status === 'APPROVED_SPEC_BOUND';
  const canPause = bound && STAGES.includes(run.state);
  const canResume = bound && (run.state === 'PAUSED' || run.state === 'FAILED');
  const evidence = ['BUILD', 'TEST', 'VERIFY', 'REVIEW'].filter((stage) => passed.has(stage));

  return (
    <View style={styles.card} accessibilityLabel={`Engineering run ${run.state}`}>
      <EditorialTrace active={busy || STAGES.includes(run.state)} tone={bound ? 'sage' : 'peach'} />
      <View style={styles.kickerRow}>
        <Text style={styles.kicker}>EXECUTION</Text>
        <Text style={styles.spec}>{run.spec_id}</Text>
      </View>
      <View style={styles.row}>
        <View style={styles.copy}>
          <Text style={styles.title}>Code run · {run.state}</Text>
          <Text style={[styles.binding, !bound && styles.bindingWarning]}>
            {bound
              ? `BOUND · WORK SPEC R${run.work_specification_revision ?? '?'} · ${run.acceptance_criteria.length} ACCEPTANCE CRITERIA`
              : 'HISTORICAL · NO APPROVED WORK-SPEC BINDING'}
          </Text>
        </View>
      </View>
      <Text style={styles.progress}>{STAGES.map((stage) => passed.has(stage) ? '●' : stage === run.state ? '◉' : '○').join('  ')}</Text>
      <Text style={styles.caption}>Evidence: {evidence.length ? evidence.join(' · ') : 'none yet'}{run.last_failure_code ? ` · ${run.last_failure_code}` : ''}</Text>
      {bound ? (
        <Text style={styles.boundary}>Locked to this approved Work Specification revision. Newer drafts cannot retarget this run.</Text>
      ) : (
        <Text style={styles.warning}>Historical runs remain readable but cannot resume as approved-spec execution evidence.</Text>
      )}
      <View style={styles.actions}>
        {canPause && <TouchableOpacity disabled={busy} onPress={onPause} style={styles.actionButton}><Text style={styles.action}>Pause</Text></TouchableOpacity>}
        {canResume && <TouchableOpacity disabled={busy} onPress={onResume} style={styles.actionButton}><Text style={styles.action}>Resume</Text></TouchableOpacity>}
        {bound && !['COMPLETE', 'CANCELLED', 'SPEC_AMENDMENT'].includes(run.state) && <TouchableOpacity disabled={busy} onPress={onCancel} style={styles.actionButton}><Text style={styles.action}>Cancel</Text></TouchableOpacity>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    position: 'relative',
    marginHorizontal: 28,
    marginTop: 20,
    paddingTop: 14,
    paddingRight: 16,
    paddingBottom: 16,
    paddingLeft: 18,
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(159,185,165,0.58)',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: palette.border,
    backgroundColor: 'rgba(13,16,29,0.26)',
    overflow: 'hidden',
  },
  kickerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 7 },
  kicker: { color: palette.sage, fontSize: 8, fontWeight: '800', letterSpacing: 1.1 },
  spec: { color: palette.muted, fontSize: 8, letterSpacing: 0.7 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { color: palette.cream, fontSize: 20, lineHeight: 24, fontWeight: '600', letterSpacing: -0.4 },
  binding: { color: palette.sage, fontSize: 9, marginTop: 5, letterSpacing: 0.62, fontWeight: '800' },
  bindingWarning: { color: palette.warning },
  progress: { color: palette.indigo, marginTop: 13, letterSpacing: 1.4, fontSize: 12 },
  caption: { color: palette.textSecondary, marginTop: 8, fontSize: 11 },
  boundary: { color: palette.indigo, marginTop: 8, fontSize: 10, lineHeight: 16, maxWidth: 720 },
  warning: { color: palette.warning, marginTop: 8, fontSize: 10, lineHeight: 16, maxWidth: 720 },
  actions: { flexDirection: 'row', gap: 8, marginTop: 13 },
  actionButton: { minHeight: 34, justifyContent: 'center', paddingHorizontal: 10, borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.indigoWash },
  action: { color: palette.cyan, fontSize: 10, fontWeight: '700' },
});
