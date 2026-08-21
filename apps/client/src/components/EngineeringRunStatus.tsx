import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto } from '../lib/api';
import { palette } from '../theme';

const STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'];

function stageSummary(run: EngineeringRunDto): string {
  if (run.state === 'PLAN') return 'Specification bound · planning is the next protected stage';
  if (run.state === 'IMPLEMENT') return 'Plan accepted · implementation evidence required';
  if (run.state === 'BUILD') return 'Implementation recorded · protected build evidence required';
  if (run.state === 'TEST') return 'Build passed · protected test evidence required';
  if (run.state === 'VERIFY') return 'Tests passed · acceptance verification required';
  if (run.state === 'REVIEW') return 'Verification passed · protected review required';
  if (run.state === 'COMPLETE') return 'All protected engineering gates passed';
  if (run.state === 'PAUSED') return `Paused${run.resume_stage ? ` · resumes at ${run.resume_stage}` : ''}`;
  if (run.state === 'FAILED') return `Stopped at ${run.resume_stage ?? 'current stage'}${run.last_failure_code ? ` · ${run.last_failure_code}` : ''}`;
  if (run.state === 'SPEC_AMENDMENT') return 'Specification amendment required before engineering can continue';
  if (run.state === 'CANCELLED') return 'Run cancelled';
  return 'Validating specification binding';
}

export function EngineeringRunStatus({ run, busy, onPause, onResume, onCancel }: {
  run: EngineeringRunDto; busy: boolean; onPause(): void; onResume(): void; onCancel(): void;
}) {
  const passed = new Set(run.attempts.filter((item) => item.status === 'PASSED').map((item) => item.stage));
  const canPause = STAGES.includes(run.state);
  const canResume = run.state === 'PAUSED' || run.state === 'FAILED';
  const evidence = ['BUILD', 'TEST', 'VERIFY', 'REVIEW'].filter((stage) => passed.has(stage));
  const activeStage = STAGES.includes(run.state) ? run.state : run.resume_stage;
  const activeIndex = activeStage ? STAGES.indexOf(activeStage) : -1;
  const progressLabel = activeIndex >= 0 ? `Stage ${activeIndex + 1} of ${STAGES.length}` : run.state;

  return (
    <View style={styles.card} accessibilityLabel={`Engineering run ${run.state}`}>
      <View style={styles.row}>
        <View style={styles.titleGroup}>
          <Text style={styles.eyebrow}>CODE RUN · {progressLabel}</Text>
          <Text style={styles.title}>{run.state}</Text>
        </View>
        <Text style={styles.spec}>{run.spec_id}</Text>
      </View>
      <Text accessibilityLabel={`Engineering progress ${run.state}`} style={styles.progress}>
        {STAGES.map((stage) => passed.has(stage) ? '●' : stage === activeStage ? '◉' : '○').join('  ')}
      </Text>
      <Text style={styles.caption}>{stageSummary(run)}</Text>
      <Text style={styles.evidence}>Verified evidence: {evidence.length ? evidence.join(' · ') : 'none yet'}</Text>
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
    padding: 15,
    borderRadius: 12,
    backgroundColor: palette.glass,
    borderWidth: 1,
    borderColor: palette.borderStrong,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 },
  titleGroup: { flex: 1 },
  eyebrow: { color: palette.muted, fontSize: 8, fontWeight: '700', letterSpacing: 0.8 },
  title: { color: palette.text, fontWeight: '700', fontSize: 15, marginTop: 4 },
  spec: { color: palette.indigo, fontSize: 10, letterSpacing: 0.3 },
  progress: { color: palette.indigo, marginTop: 11, letterSpacing: 1.2 },
  caption: { color: palette.textSecondary, marginTop: 9, fontSize: 12, lineHeight: 17 },
  evidence: { color: palette.muted, marginTop: 5, fontSize: 10 },
  actions: { flexDirection: 'row', gap: 18, marginTop: 12 },
  action: { color: palette.cyan, fontWeight: '600', fontSize: 12 },
});
