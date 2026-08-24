import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { EngineeringRunDto, WorkSpecificationDto } from '../lib/api';
import { palette } from '../theme';

type Props = {
  apiOnline: boolean;
  phase: string;
  mode: 'reason' | 'code';
  run: EngineeringRunDto | null;
  specification: WorkSpecificationDto | null;
};

function Card({ title, children }: React.PropsWithChildren<{ title: string }>) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{title}</Text>
      {children}
    </View>
  );
}

function StatusRow({ label, value, tone = 'neutral' }: { label: string; value: string; tone?: 'neutral' | 'teal' | 'olive' | 'rust' }) {
  const toneStyle = tone === 'teal' ? styles.teal : tone === 'olive' ? styles.olive : tone === 'rust' ? styles.rust : styles.neutral;
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.pill, toneStyle]}><Text style={styles.pillText}>{value}</Text></View>
    </View>
  );
}

export function EditorialUtilityRail({ apiOnline, phase, mode, run, specification }: Props) {
  const bound = run?.binding_status === 'APPROVED_SPEC_BOUND';
  const passed = run ? new Set(run.attempts.filter((attempt) => attempt.status === 'PASSED').map((attempt) => attempt.stage)) : new Set<string>();
  const evidence = ['BUILD', 'TEST', 'VERIFY'].filter((stage) => passed.has(stage));

  return (
    <View style={styles.rail} testID="editorial-utility-rail">
      <Card title="System health">
        <StatusRow label="API" value={apiOnline ? 'Available' : 'Unavailable'} tone={apiOnline ? 'olive' : 'rust'} />
        <StatusRow label="Conversation" value={phase.toLowerCase()} tone={phase === 'ERROR' ? 'rust' : phase === 'IDLE' || phase === 'COMPLETE' ? 'olive' : 'teal'} />
        <Text style={styles.note}>Health reflects current client/server evidence. Missing telemetry is never interpreted as healthy.</Text>
      </Card>

      <Card title="Current session">
        <View style={styles.fact}><Text style={styles.factLabel}>Mode</Text><Text style={styles.factValue}>{mode === 'code' ? 'Code' : 'Reason'}</Text></View>
        <View style={styles.fact}><Text style={styles.factLabel}>Specification</Text><Text numberOfLines={1} style={styles.factValue}>{specification ? `R${specification.revision} · ${specification.status}` : 'Not available'}</Text></View>
        <View style={styles.fact}><Text style={styles.factLabel}>Engineering run</Text><Text numberOfLines={1} style={styles.factValue}>{run ? run.state : 'No active run'}</Text></View>
      </Card>

      <Card title="Execution evidence">
        {run ? (
          <>
            <StatusRow label="Binding" value={bound ? 'Approved spec' : 'Historical'} tone={bound ? 'olive' : 'neutral'} />
            <StatusRow label="Stage" value={run.state} tone={['FAILED', 'CANCELLED'].includes(run.state) ? 'rust' : 'teal'} />
            <View style={styles.fact}><Text style={styles.factLabel}>Passed evidence</Text><Text style={styles.factValue}>{evidence.length ? evidence.join(' · ') : 'None yet'}</Text></View>
          </>
        ) : (
          <Text style={styles.empty}>No authoritative engineering run is attached to this conversation.</Text>
        )}
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  rail: { width: 270, paddingHorizontal: 16, paddingTop: 88, paddingBottom: 18, gap: 12, backgroundColor: 'rgba(245,238,223,0.72)', borderLeftWidth: StyleSheet.hairlineWidth, borderLeftColor: palette.border },
  card: { borderRadius: 18, backgroundColor: 'rgba(251,247,238,0.94)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, padding: 15, shadowColor: '#564B38', shadowOpacity: 0.07, shadowRadius: 16, shadowOffset: { width: 0, height: 7 } },
  cardTitle: { color: palette.charcoal950, fontSize: 15, lineHeight: 19, fontWeight: '700', marginBottom: 12 },
  row: { minHeight: 32, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 7 },
  label: { flex: 1, color: palette.charcoal600, fontSize: 11 },
  pill: { minHeight: 24, maxWidth: 128, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 9, borderRadius: 999 },
  pillText: { color: palette.charcoal950, fontSize: 9, lineHeight: 12, fontWeight: '700' },
  neutral: { backgroundColor: palette.cream200 },
  teal: { backgroundColor: palette.teal100 },
  olive: { backgroundColor: palette.olive200 },
  rust: { backgroundColor: palette.rust100 },
  fact: { marginBottom: 10 },
  factLabel: { color: palette.charcoal450, fontSize: 9, textTransform: 'uppercase', letterSpacing: 0.65, marginBottom: 3 },
  factValue: { color: palette.charcoal800, fontSize: 11, lineHeight: 16, fontWeight: '600' },
  note: { color: palette.charcoal600, fontSize: 10, lineHeight: 15, marginTop: 3 },
  empty: { color: palette.charcoal600, fontSize: 10, lineHeight: 16 },
});
