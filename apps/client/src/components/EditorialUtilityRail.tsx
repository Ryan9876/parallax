import React from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import type { EngineeringRunDto, ProjectBindingStatus, WorkSpecificationDto } from '../lib/api';
import { palette } from '../theme';

type Props = {
  width?: number;
  apiOnline: boolean;
  phase: string;
  mode: 'reason' | 'code';
  run: EngineeringRunDto | null;
  specification: WorkSpecificationDto | null;
  projectId: string | null;
  projectBindingStatus: ProjectBindingStatus | null;
};

function Card({ eyebrow, title, children }: React.PropsWithChildren<{ eyebrow: string; title: string }>) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardEyebrow}>{eyebrow}</Text>
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

function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <View style={styles.fact}>
      <Text style={styles.factLabel}>{label}</Text>
      <Text numberOfLines={2} selectable={mono} style={[styles.factValue, mono && styles.mono]}>{value}</Text>
    </View>
  );
}

function shortId(value: string | null): string {
  if (!value) return 'Unavailable';
  return value.length <= 22 ? value : `${value.slice(0, 9)}…${value.slice(-7)}`;
}

export function EditorialUtilityRail({ width = 296, apiOnline, phase, mode, run, specification, projectId, projectBindingStatus }: Props) {
  const bound = run?.binding_status === 'APPROVED_SPEC_BOUND';
  const passed = run ? new Set(run.attempts.filter((attempt) => attempt.status === 'PASSED').map((attempt) => attempt.stage)) : new Set<string>();
  const evidence = ['BUILD', 'TEST', 'VERIFY'].filter((stage) => passed.has(stage));
  const phaseTone = phase === 'ERROR' ? 'rust' : phase === 'IDLE' || phase === 'COMPLETE' ? 'olive' : 'teal';
  const projectValue = projectBindingStatus === 'HISTORICAL_UNBOUND'
    ? 'Historical · unbound'
    : projectId
      ? shortId(projectId)
      : mode === 'reason'
        ? 'Not required'
        : 'Unavailable';

  return (
    <View style={[styles.rail, { width }]} testID="editorial-utility-rail">
      <View style={styles.railHeading}>
        <Text style={styles.railKicker}>Context</Text>
        <Text style={styles.railTitle}>Workspace facts</Text>
        <Text style={styles.railIntro}>Only current application and protected run evidence appears here.</Text>
      </View>

      <Card eyebrow="Connection" title="Workspace status">
        <StatusRow label="API" value={apiOnline ? 'Available' : 'Unavailable'} tone={apiOnline ? 'olive' : 'rust'} />
        <StatusRow label="Response" value={phase.toLowerCase()} tone={phaseTone} />
        <Text style={styles.note}>Unavailable evidence is not interpreted as healthy or complete.</Text>
      </Card>

      <Card eyebrow="Identity" title="Active context">
        <Fact label="Mode" value={mode === 'code' ? 'Code' : 'Reason'} />
        <Fact label="Project" value={projectValue} mono={Boolean(projectId)} />
        <Fact label="Specification" value={specification ? `R${specification.revision} · ${specification.status}` : 'Unavailable'} />
      </Card>

      <Card eyebrow="Execution" title="Engineering run">
        {run ? (
          <>
            <StatusRow label="Binding" value={bound ? 'Approved spec' : 'Historical'} tone={bound ? 'olive' : 'neutral'} />
            <StatusRow label="Stage" value={run.state} tone={['FAILED', 'CANCELLED'].includes(run.state) ? 'rust' : 'teal'} />
            <Fact label="Run ID" value={shortId(run.id)} mono />
            <Fact label="Passed evidence" value={evidence.length ? evidence.join(' · ') : 'None yet'} />
            {run.last_failure_code ? <Fact label="Latest failure" value={run.last_failure_code} mono /> : null}
          </>
        ) : (
          <Text style={styles.empty}>No authoritative Engineering Run is attached to this conversation.</Text>
        )}
      </Card>
    </View>
  );
}

const serif = Platform.OS === 'web' ? 'Georgia, ui-serif, Charter, serif' : undefined;

const styles = StyleSheet.create({
  rail: {
    paddingHorizontal: 16,
    paddingTop: 24,
    paddingBottom: 18,
    gap: 12,
    backgroundColor: 'rgba(245,238,223,0.80)',
    borderLeftWidth: StyleSheet.hairlineWidth,
    borderLeftColor: palette.border,
  },
  railHeading: { paddingHorizontal: 3, marginBottom: 4 },
  railKicker: { color: palette.olive700, fontSize: 8, fontWeight: '800', letterSpacing: 1.05, textTransform: 'uppercase', marginBottom: 4 },
  railTitle: { color: palette.charcoal950, fontSize: 20, lineHeight: 24, fontWeight: '600', letterSpacing: -0.45, fontFamily: serif },
  railIntro: { color: palette.charcoal600, fontSize: 9, lineHeight: 14, marginTop: 5 },
  card: {
    borderRadius: 18,
    backgroundColor: 'rgba(251,247,238,0.96)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.border,
    padding: 15,
    shadowColor: '#564B38',
    shadowOpacity: 0.065,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 7 },
  },
  cardEyebrow: { color: palette.charcoal450, fontSize: 7, lineHeight: 10, textTransform: 'uppercase', letterSpacing: 0.8, fontWeight: '800', marginBottom: 3 },
  cardTitle: { color: palette.charcoal950, fontSize: 15, lineHeight: 19, fontWeight: '700', marginBottom: 12, fontFamily: serif },
  row: { minHeight: 32, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 7 },
  label: { flex: 1, color: palette.charcoal600, fontSize: 10 },
  pill: { minHeight: 24, maxWidth: 136, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 9, borderRadius: 999 },
  pillText: { color: palette.charcoal950, fontSize: 8, lineHeight: 11, fontWeight: '800' },
  neutral: { backgroundColor: palette.cream200 },
  teal: { backgroundColor: palette.teal100 },
  olive: { backgroundColor: palette.olive200 },
  rust: { backgroundColor: palette.rust100 },
  fact: { marginBottom: 10 },
  factLabel: { color: palette.charcoal450, fontSize: 8, textTransform: 'uppercase', letterSpacing: 0.65, marginBottom: 3 },
  factValue: { color: palette.charcoal800, fontSize: 10, lineHeight: 15, fontWeight: '600' },
  mono: { fontFamily: Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : undefined, fontWeight: '500' },
  note: { color: palette.charcoal600, fontSize: 9, lineHeight: 14, marginTop: 3 },
  empty: { color: palette.charcoal600, fontSize: 10, lineHeight: 16 },
});
