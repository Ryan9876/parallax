import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto } from '../lib/api';
import { palette } from '../theme';

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
      <View style={styles.row}>
        <View style={styles.copy}>
          <Text style={styles.title}>Code run · {run.state}</Text>
          <Text style={[styles.binding, !bound && styles.bindingWarning]}>
            {bound
              ? `BOUND · WORK SPEC R${run.work_specification_revision ?? '?'} · ${run.acceptance_criteria.length} ACCEPTANCE CRITERIA`
              : 'HISTORICAL · NO APPROVED WORK-SPEC BINDING'}
          </Text>
        </View>
        <Text style={styles.spec}>{run.spec_id}</Text>
      </View>
      <Text style={styles.progress}>{STAGES.map((stage) => passed.has(stage) ? '●' : stage === run.state ? '◉' : '○').join('  ')}</Text>
      <Text style={styles.caption}>Evidence: {evidence.length ? evidence.join(' · ') : 'none yet'}{run.last_failure_code ? ` · ${run.last_failure_code}` : ''}</Text>
      {bound ? (
        <Text style={styles.boundary}>This run is locked to its approved Work Specification revision; newer drafts cannot retarget it.</Text>
      ) : (
        <Text style={styles.warning}>Historical runs remain readable but cannot resume as approved-spec execution evidence.</Text>
      )}
      <View style={styles.actions}>
        {canPause && <TouchableOpacity disabled={busy} onPress={onPause}><Text style={styles.action}>Pause</Text></TouchableOpacity>}
        {canResume && <TouchableOpacity disabled={busy} onPress={onResume}><Text style={styles.action}>Resume</Text></TouchableOpacity>}
        {bound && !['COMPLETE', 'CANCELLED', 'SPEC_AMENDMENT'].includes(run.state) && <TouchableOpacity disabled={busy} onPress={onCancel}><Text style={styles.action}>Cancel</Text></TouchableOpacity>}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 24,
    marginTop: 12,
    padding: 14,
    borderRadius: 12,
    backgroundColor: palette.glass,
    borderWidth: 1,
    borderColor: palette.borderStrong,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { color: palette.text, fontWeight: '700' },
  binding: { color: palette.success, fontSize: 9, marginTop: 4, letterSpacing: 0.5, fontWeight: '700' },
  bindingWarning: { color: palette.warning },
  spec: { color: palette.textSecondary, fontSize: 11 },
  progress: { color: palette.indigo, marginTop: 9, letterSpacing: 1 },
  caption: { color: palette.textSecondary, marginTop: 7, fontSize: 12 },
  boundary: { color: palette.indigo, marginTop: 7, fontSize: 10, lineHeight: 15 },
  warning: { color: palette.warning, marginTop: 7, fontSize: 10, lineHeight: 15 },
  actions: { flexDirection: 'row', gap: 18, marginTop: 10 },
  action: { color: palette.cyan, fontWeight: '600' },
});
