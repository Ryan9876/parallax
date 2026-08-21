import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto } from '../lib/api';
import { palette } from '../theme';
import { EditorialTrace } from './EditorialTrace';

const STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'];

export function EngineeringRunStatus({ run, busy, onPause, onResume, onCancel, reducedGraphics = false }: {
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
  const evidence = ['BUILD', 'TEST', 'VERIFY', 'REVIEW'].filter((stage) => passed.has(stage));

  return (
    <View style={styles.card} accessibilityLabel={`Engineering run ${run.state}`}>
      {!reducedGraphics && <EditorialTrace active={busy || STAGES.includes(run.state)} tone={bound ? 'sage' : 'peach'} />}
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
  card: { position: 'relative', marginLeft: 52, marginRight: 34, marginTop: 22, paddingTop: 17, paddingRight: 20, paddingBottom: 20, paddingLeft: 22, borderRightWidth: 3, borderRightColor: 'rgba(159,185,165,0.78)', borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(240,228,207,0.14)', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.borderStrong, backgroundColor: 'rgba(13,18,30,0.44)', overflow: 'hidden' },
  kickerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 9 },
  kicker: { color: palette.sage, fontSize: 9, fontWeight: '800', letterSpacing: 1.2 },
  spec: { color: palette.muted, fontSize: 8, letterSpacing: 0.8 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { color: palette.cream, fontSize: 23, lineHeight: 27, fontWeight: '600', letterSpacing: -0.6 },
  binding: { color: palette.sage, fontSize: 9, marginTop: 7, letterSpacing: 0.7, fontWeight: '800' },
  bindingWarning: { color: palette.warning },
  progress: { color: palette.indigo, marginTop: 15, letterSpacing: 1.6, fontSize: 13 },
  caption: { color: palette.textSecondary, marginTop: 9, fontSize: 11 },
  boundary: { color: palette.indigo, marginTop: 9, fontSize: 10, lineHeight: 16, maxWidth: 740 },
  warning: { color: palette.warning, marginTop: 9, fontSize: 10, lineHeight: 16, maxWidth: 740 },
  actions: { flexDirection: 'row', gap: 9, marginTop: 15 },
  actionButton: { minHeight: 36, justifyContent: 'center', paddingHorizontal: 12, borderRadius: 13, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.indigoWash },
  action: { color: palette.cyan, fontSize: 10, fontWeight: '700' },
});
