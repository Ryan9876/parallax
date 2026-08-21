import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto } from '../lib/api';
import { palette } from '../theme';

const STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'];

export function EngineeringRunStatus({ run, busy, onPause, onResume, onCancel }: {
  run: EngineeringRunDto; busy: boolean; onPause(): void; onResume(): void; onCancel(): void;
}) {
  const passed = new Set(run.attempts.filter((item) => item.status === 'PASSED').map((item) => item.stage));
  const canPause = STAGES.includes(run.state);
  const canResume = run.state === 'PAUSED' || run.state === 'FAILED';
  const evidence = ['BUILD', 'TEST', 'VERIFY', 'REVIEW'].filter((stage) => passed.has(stage));
  return (
    <View style={styles.card} accessibilityLabel={`Engineering run ${run.state}`}>
      <View style={styles.row}><Text style={styles.title}>Code run · {run.state}</Text><Text style={styles.spec}>{run.spec_id}</Text></View>
      <Text style={styles.progress}>{STAGES.map((stage) => passed.has(stage) ? '●' : stage === run.state ? '◉' : '○').join('  ')}</Text>
      <Text style={styles.caption}>Evidence: {evidence.length ? evidence.join(' · ') : 'none yet'}{run.last_failure_code ? ` · ${run.last_failure_code}` : ''}</Text>
      <View style={styles.actions}>
        {canPause && <TouchableOpacity disabled={busy} onPress={onPause}><Text style={styles.action}>Pause</Text></TouchableOpacity>}
        {canResume && <TouchableOpacity disabled={busy} onPress={onResume}><Text style={styles.action}>Resume</Text></TouchableOpacity>}
        {!['COMPLETE', 'CANCELLED', 'SPEC_AMENDMENT'].includes(run.state) && <TouchableOpacity disabled={busy} onPress={onCancel}><Text style={styles.action}>Cancel</Text></TouchableOpacity>}
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
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  title: { color: palette.text, fontWeight: '700' },
  spec: { color: palette.textSecondary, fontSize: 12 },
  progress: { color: palette.indigo, marginTop: 9, letterSpacing: 1 },
  caption: { color: palette.textSecondary, marginTop: 7, fontSize: 12 },
  actions: { flexDirection: 'row', gap: 18, marginTop: 10 },
  action: { color: palette.cyan, fontWeight: '600' },
});
