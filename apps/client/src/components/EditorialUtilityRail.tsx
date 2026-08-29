import React from 'react';
import { Platform, StyleSheet, Text, View } from 'react-native';
import type { EngineeringRunDto, ProjectBindingStatus, WorkSpecificationDto } from '../lib/api';
import { getWorkflowGuidance } from '../lib/workflowGuidance';
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

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.fact}>
      <Text style={styles.factLabel}>{label}</Text>
      <Text numberOfLines={2} style={styles.factValue}>{value}</Text>
    </View>
  );
}

function responseStatus(phase: string): string {
  if (phase === 'ERROR') return 'Needs attention';
  if (phase === 'SPEC_AMENDMENT' || phase === 'HUMAN_REQUIRED') return 'Ready for you';
  if (phase === 'IDLE' || phase === 'COMPLETE') return 'Ready';
  return 'Working';
}

function runStatus(run: EngineeringRunDto): string {
  const stage = (run.state === 'FAILED' || run.state === 'PAUSED' || run.state === 'CANCELLED') && run.resume_stage
    ? run.resume_stage
    : run.state;
  const labels: Record<string, string> = {
    SPECIFY: 'Defining the goal',
    PLAN: 'Planning',
    IMPLEMENT: 'Creating',
    BUILD: 'Preparing the result',
    TEST: 'Checking',
    VERIFY: 'Final checks',
    REVIEW: 'Ready for review',
    COMPLETE: 'Complete',
  };
  if (run.state === 'FAILED') return 'Needs attention';
  if (run.state === 'PAUSED') return 'Paused';
  if (run.state === 'CANCELLED') return 'Stopped';
  return labels[stage] ?? 'In progress';
}

export function EditorialUtilityRail({ width = 296, apiOnline, phase, mode, run, specification, projectId, projectBindingStatus }: Props) {
  const bound = run?.binding_status === 'APPROVED_SPEC_BOUND';
  const phaseTone = phase === 'ERROR' ? 'rust' : phase === 'IDLE' || phase === 'COMPLETE' ? 'olive' : 'teal';
  const projectValue = projectBindingStatus === 'HISTORICAL_UNBOUND'
    ? 'Older conversation'
    : projectId
      ? 'Project selected'
      : mode === 'reason'
        ? 'Not needed for this chat'
        : 'Choose a project';
  const planValue = specification
    ? specification.status === 'APPROVED' ? 'Approved' : 'Ready for review'
    : mode === 'reason' ? 'Not needed yet' : 'Not created';
  const showGuidance = mode === 'code' && Boolean(run || specification || phase === 'SPEC_AMENDMENT' || phase === 'ERROR');
  const guidance = showGuidance
    ? getWorkflowGuidance({
        mode,
        phase,
        specification,
        run,
        hasApprovedSpecification: specification?.status === 'APPROVED',
        runError: phase === 'ERROR' ? 'response-error' : null,
      })
    : null;

  return (
    <View style={[styles.rail, { width }]} testID="editorial-utility-rail">
      <View style={styles.railHeading}>
        <Text style={styles.railKicker}>At a glance</Text>
        <Text style={styles.railTitle}>What’s happening</Text>
        <Text style={styles.railIntro}>A simple view of the current conversation and build progress.</Text>
      </View>

      {guidance ? (
        <Card eyebrow="Next" title={guidance.title}>
          <Text style={styles.guidanceCopy}>{guidance.description}</Text>
        </Card>
      ) : null}

      <Card eyebrow="Parallax" title="Current status">
        <StatusRow label="Service" value={apiOnline ? 'Available' : 'Unavailable'} tone={apiOnline ? 'olive' : 'rust'} />
        <StatusRow label="Conversation" value={responseStatus(phase)} tone={phaseTone} />
        {!apiOnline ? <Text style={styles.note}>Some actions may not work until the service is available again.</Text> : null}
      </Card>

      <Card eyebrow="Your work" title="Current context">
        <Fact label="Activity" value={mode === 'code' ? 'Build' : 'Ask'} />
        <Fact label="Project" value={projectValue} />
        <Fact label="Build plan" value={planValue} />
      </Card>

      <Card eyebrow="Progress" title="Build status">
        {run ? (
          <>
            <StatusRow label="Plan" value={bound ? 'Approved' : 'View only'} tone={bound ? 'olive' : 'neutral'} />
            <StatusRow label="Right now" value={runStatus(run)} tone={['FAILED', 'CANCELLED'].includes(run.state) ? 'rust' : run.state === 'COMPLETE' ? 'olive' : 'teal'} />
            {run.last_failure_code ? <Text style={styles.note}>Something needs attention before the work can continue. Open Progress for details.</Text> : null}
          </>
        ) : (
          <Text style={styles.empty}>{mode === 'code' ? 'No build is running yet.' : 'Start a build when you are ready to create or change an application.'}</Text>
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
  railKicker: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 4 },
  railTitle: { color: palette.charcoal950, fontSize: 21, lineHeight: 26, fontWeight: '600', letterSpacing: -0.45, fontFamily: serif },
  railIntro: { color: palette.charcoal600, fontSize: 13, lineHeight: 19, marginTop: 5 },
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
  cardEyebrow: { color: palette.charcoal450, fontSize: 11, lineHeight: 15, textTransform: 'uppercase', letterSpacing: 0.7, fontWeight: '800', marginBottom: 3 },
  cardTitle: { color: palette.charcoal950, fontSize: 16, lineHeight: 21, fontWeight: '700', marginBottom: 12, fontFamily: serif },
  guidanceCopy: { color: palette.charcoal600, fontSize: 13, lineHeight: 20 },
  row: { minHeight: 38, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 7 },
  label: { flex: 1, color: palette.charcoal600, fontSize: 13, lineHeight: 18 },
  pill: { minHeight: 30, maxWidth: 150, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 10, borderRadius: 999 },
  pillText: { color: palette.charcoal950, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  neutral: { backgroundColor: palette.cream200 },
  teal: { backgroundColor: palette.teal100 },
  olive: { backgroundColor: palette.olive200 },
  rust: { backgroundColor: palette.rust100 },
  fact: { marginBottom: 11 },
  factLabel: { color: palette.charcoal450, fontSize: 11, lineHeight: 15, textTransform: 'uppercase', letterSpacing: 0.55, marginBottom: 3 },
  factValue: { color: palette.charcoal800, fontSize: 13, lineHeight: 19, fontWeight: '600' },
  note: { color: palette.charcoal600, fontSize: 12, lineHeight: 18, marginTop: 4 },
  empty: { color: palette.charcoal600, fontSize: 13, lineHeight: 20 },
});
