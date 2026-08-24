import React from 'react';
import { Platform, ScrollView, StyleSheet, Text, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import type { EngineeringRunDto } from '../../lib/api';
import {
  observerHealth,
  projectPipeline,
  providerIdentities,
  recentAlerts,
  safeEventMetadata,
} from '../../lib/observabilityProjection';
import { useRunObservability, type LiveBuildTab } from '../../hooks/useRunObservability';
import { palette } from '../../theme';
import { RunEventStream } from './RunEventStream';
import { RunPipeline } from './RunPipeline';

const TABS: LiveBuildTab[] = ['Code', 'Diff', 'Terminal', 'Tests', 'Events', 'Evidence'];

function TinyPill({ children, tone = 'neutral' }: React.PropsWithChildren<{ tone?: 'neutral' | 'olive' | 'teal' | 'rust' }>) {
  return <View style={[styles.pill, tone === 'olive' ? styles.pillOlive : tone === 'teal' ? styles.pillTeal : tone === 'rust' ? styles.pillRust : null]}><Text style={styles.pillText}>{children}</Text></View>;
}

function Empty({ children }: React.PropsWithChildren) {
  return <View style={styles.empty}><Text style={styles.emptyText}>{children}</Text></View>;
}

function CodeView({ observer }: { observer: ReturnType<typeof useRunObservability> }) {
  const { view } = observer;
  return (
    <View style={styles.splitView}>
      <ScrollView style={styles.fileColumn} contentContainerStyle={styles.fileColumnContent}>
        <Text style={styles.sectionLabel}>ACCEPTED LINEAGE</Text>
        {view.lineages.length ? view.lineages.map((lineage) => (
          <TouchableOpacity key={lineage} accessibilityRole="button" onPress={() => void observer.loadTree(lineage)} style={[styles.lineageButton, view.selectedLineage === lineage && styles.selectedButton]}>
            <Text numberOfLines={1} style={styles.lineageText}>{lineage}</Text>
          </TouchableOpacity>
        )) : <Text style={styles.muted}>No source lineage has been observed for this run.</Text>}
        {view.sourceTree ? (
          <>
            <Text style={[styles.sectionLabel, styles.sectionSpacing]}>FILES · {view.sourceTree.file_count}</Text>
            {view.sourceTree.files.map((file) => (
              <TouchableOpacity key={file.path} accessibilityRole="button" onPress={() => void observer.loadFile(file.path)} style={[styles.fileButton, view.selectedPath === file.path && styles.selectedButton]}>
                <Text numberOfLines={2} style={styles.fileText}>{file.path}</Text>
              </TouchableOpacity>
            ))}
          </>
        ) : null}
      </ScrollView>
      <ScrollView style={styles.codeColumn} contentContainerStyle={styles.codeContent}>
        {view.sourceFile ? (
          <>
            <View style={styles.codeHead}><Text style={styles.codePath}>{view.sourceFile.path}</Text><TinyPill>{view.sourceFile.availability}</TinyPill></View>
            {view.sourceFile.availability === 'TEXT' && view.sourceFile.text !== null ? <Text selectable style={styles.monospace}>{view.sourceFile.text}</Text> : <Empty>Protected content is {view.sourceFile.availability.toLowerCase().replace('_', ' ')}.</Empty>}
          </>
        ) : <Empty>Select an observed lineage and file. Parallax does not browse outside exact run lineage.</Empty>}
      </ScrollView>
    </View>
  );
}

function DiffView({ observer }: { observer: ReturnType<typeof useRunObservability> }) {
  const { view } = observer;
  React.useEffect(() => {
    if (!view.sourceDiff && view.parentLineage && view.candidateLineage) void observer.loadDiff();
  }, [observer, view.candidateLineage, view.parentLineage, view.sourceDiff]);
  if (!view.parentLineage || !view.candidateLineage) return <Empty>A parent and candidate lineage have not both been persisted for this run.</Empty>;
  if (!view.sourceDiff) return <Empty>{view.readBusy ? 'Loading protected lineage diff…' : 'Protected diff is not available yet.'}</Empty>;
  return (
    <ScrollView style={styles.detailScroll} contentContainerStyle={styles.detailContent}>
      <View style={styles.factRow}><Text style={styles.factLabel}>FROM</Text><Text numberOfLines={1} style={styles.factValue}>{view.sourceDiff.from_lineage}</Text></View>
      <View style={styles.factRow}><Text style={styles.factLabel}>TO</Text><Text numberOfLines={1} style={styles.factValue}>{view.sourceDiff.to_lineage}</Text></View>
      {view.sourceDiff.files.length ? view.sourceDiff.files.map((file) => (
        <View key={`${file.change_type}:${file.path}`} style={styles.diffFile}>
          <View style={styles.codeHead}><Text style={styles.codePath}>{file.change_type} · {file.path}</Text><TinyPill>{file.availability}</TinyPill></View>
          {file.diff_text ? <Text selectable style={styles.monospace}>{file.diff_text}</Text> : <Text style={styles.muted}>No bounded text diff is available for this file.</Text>}
          {file.truncated ? <Text style={styles.warning}>Diff truncated by protected response bounds.</Text> : null}
        </View>
      )) : <Empty>No changed files were returned by the protected diff.</Empty>}
    </ScrollView>
  );
}

function AttemptView({ observer, testsOnly }: { observer: ReturnType<typeof useRunObservability>; testsOnly?: boolean }) {
  const { view } = observer;
  const eligible = view.events.filter((event) => event.attempt_id && (!testsOnly || event.stage === 'TEST'));
  return (
    <View style={styles.splitView}>
      <ScrollView style={styles.fileColumn} contentContainerStyle={styles.fileColumnContent}>
        <Text style={styles.sectionLabel}>{testsOnly ? 'TEST ATTEMPTS' : 'BOUNDED ATTEMPTS'}</Text>
        {eligible.length ? eligible.map((event) => (
          <TouchableOpacity key={`${event.attempt_id}:${event.sequence}`} accessibilityRole="button" onPress={() => event.attempt_id && void observer.loadEvidence(event.attempt_id)} style={[styles.fileButton, view.selectedAttempt === event.attempt_id && styles.selectedButton]}>
            <Text style={styles.fileText}>{event.stage || event.subsystem} · #{event.sequence}</Text>
            <Text style={styles.mini}>{event.outcome}</Text>
          </TouchableOpacity>
        )) : <Text style={styles.muted}>No persisted {testsOnly ? 'test ' : ''}attempt evidence is available.</Text>}
      </ScrollView>
      <ScrollView style={styles.codeColumn} contentContainerStyle={styles.codeContent}>
        {view.evidence ? (
          <>
            <View style={styles.codeHead}><Text style={styles.codePath}>{view.evidence.stage} · attempt {view.evidence.attempt_number}</Text><TinyPill tone={view.evidence.availability === 'AVAILABLE' ? 'olive' : 'rust'}>{view.evidence.availability}</TinyPill></View>
            <View style={styles.factRow}><Text style={styles.factLabel}>STATUS</Text><Text style={styles.factValue}>{view.evidence.status}</Text></View>
            {view.evidence.failure_code ? <View style={styles.factRow}><Text style={styles.factLabel}>FAILURE</Text><Text style={styles.factValue}>{view.evidence.failure_code}</Text></View> : null}
            <View style={styles.factRow}><Text style={styles.factLabel}>TOOL</Text><Text style={styles.factValue}>{view.evidence.tool_id || 'Not recorded'}</Text></View>
            <View style={styles.factRow}><Text style={styles.factLabel}>PROGRAM</Text><Text style={styles.factValue}>{view.evidence.program_id || 'Not recorded'}</Text></View>
            {view.evidence.availability === 'AVAILABLE' ? <Text selectable style={styles.monospace}>{JSON.stringify(view.evidence.evidence, null, 2)}</Text> : <Empty>Evidence is {view.evidence.availability.toLowerCase()} by the protected API.</Empty>}
          </>
        ) : <Empty>Select an observed attempt. This is read-only protected evidence, not an interactive shell.</Empty>}
      </ScrollView>
    </View>
  );
}

function EvidenceView({ observer }: { observer: ReturnType<typeof useRunObservability> }) {
  const providers = providerIdentities(observer.view.events);
  const latest = observer.view.events[observer.view.events.length - 1];
  const metadata = latest ? safeEventMetadata(latest) : [];
  return (
    <ScrollView style={styles.detailScroll} contentContainerStyle={styles.detailContent}>
      <Text style={styles.sectionLabel}>DURABLE REFERENCES</Text>
      <View style={styles.evidenceGrid}>
        <View style={styles.evidenceCard}><Text style={styles.factLabel}>RUN</Text><Text selectable style={styles.factValue}>{latest?.run_id || 'Not available'}</Text></View>
        <View style={styles.evidenceCard}><Text style={styles.factLabel}>CANDIDATE LINEAGE</Text><Text selectable style={styles.factValue}>{observer.view.candidateLineage || 'Not available'}</Text></View>
        <View style={styles.evidenceCard}><Text style={styles.factLabel}>PARENT / LAST KNOWN</Text><Text selectable style={styles.factValue}>{observer.view.parentLineage || 'Not available'}</Text></View>
        <View style={styles.evidenceCard}><Text style={styles.factLabel}>LATEST SEQUENCE</Text><Text style={styles.factValue}>{latest?.sequence ?? 'Not available'}</Text></View>
      </View>
      <Text style={[styles.sectionLabel, styles.sectionSpacing]}>PROVIDER EVIDENCE</Text>
      {providers.length ? providers.map((provider) => <View key={`${provider.provider}:${provider.sequence}`} style={styles.providerRow}><Text style={styles.provider}>{provider.provider}</Text><Text style={styles.providerValue}>{provider.identifier || 'Identity recorded'} · {provider.status}</Text></View>) : <Text style={styles.muted}>No GitHub PR or Vercel Preview fact has been persisted for this run yet.</Text>}
      <Text style={[styles.sectionLabel, styles.sectionSpacing]}>SAFE LATEST METADATA</Text>
      {metadata.length ? metadata.map((item) => <View key={item.key} style={styles.factRow}><Text style={styles.factLabel}>{item.key.replaceAll('_', ' ')}</Text><Text selectable style={styles.factValue}>{item.value}</Text></View>) : <Text style={styles.muted}>No allowlisted metadata is available. Raw provider payloads are intentionally not rendered.</Text>}
    </ScrollView>
  );
}

function ContextRail({ observer, run }: { observer: ReturnType<typeof useRunObservability>; run: EngineeringRunDto }) {
  const health = observerHealth(observer.view.transport, run, observer.view.events);
  const alerts = recentAlerts(observer.view.events);
  const last = observer.view.events[observer.view.events.length - 1];
  return (
    <View style={styles.contextRail} accessibilityLabel="Live Build contextual health">
      <View style={styles.contextCard}>
        <Text style={styles.contextTitle}>System Health</Text>
        <View style={styles.factRow}><Text style={styles.factLabel}>OBSERVER</Text><TinyPill tone={health.tone === 'neutral' ? 'neutral' : health.tone}>{health.transport}</TinyPill></View>
        <View style={styles.factRow}><Text style={styles.factLabel}>RUN</Text><Text style={styles.factValue}>{health.run}</Text></View>
        <Text style={styles.contextNote}>Health reflects persisted run and transport facts only.</Text>
      </View>
      <View style={styles.contextCard}>
        <Text style={styles.contextTitle}>Active Run</Text>
        <View style={styles.factRow}><Text style={styles.factLabel}>STATE</Text><Text style={styles.factValue}>{run.state}</Text></View>
        <View style={styles.factRow}><Text style={styles.factLabel}>REVISION</Text><Text style={styles.factValue}>{run.revision}</Text></View>
        <View style={styles.factRow}><Text style={styles.factLabel}>SEQUENCE</Text><Text style={styles.factValue}>{last?.sequence ?? 'No event yet'}</Text></View>
        <View style={styles.factRow}><Text style={styles.factLabel}>PROJECT</Text><Text numberOfLines={1} style={styles.factValue}>{run.project_id || 'Historical unbound'}</Text></View>
      </View>
      <View style={styles.contextCard}>
        <Text style={styles.contextTitle}>Recent Alerts</Text>
        {alerts.length ? alerts.map((alert) => <View key={alert.key} style={styles.alert}><View style={[styles.alertDot, alert.tone === 'rust' ? styles.alertRust : alert.tone === 'olive' ? styles.alertOlive : styles.alertTeal]} /><View style={styles.alertCopy}><Text style={styles.alertTitle}>{alert.title}</Text><Text style={styles.contextNote}>{alert.detail}</Text></View></View>) : <Text style={styles.contextNote}>No persisted failure, recovery or human-review alert is present.</Text>}
      </View>
    </View>
  );
}

export function LiveBuildWorkspace({ run, onBack }: { run: EngineeringRunDto; onBack: () => void }) {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const showContext = width >= 1180;
  const observer = useRunObservability(run, true);
  const pipeline = React.useMemo(() => projectPipeline(run, observer.view.events), [observer.view.events, run]);

  const renderTab = () => {
    if (observer.view.selectedTab === 'Code') return <CodeView observer={observer} />;
    if (observer.view.selectedTab === 'Diff') return <DiffView observer={observer} />;
    if (observer.view.selectedTab === 'Terminal') return <AttemptView observer={observer} />;
    if (observer.view.selectedTab === 'Tests') return <AttemptView observer={observer} testsOnly />;
    if (observer.view.selectedTab === 'Evidence') return <EvidenceView observer={observer} />;
    return <RunEventStream events={observer.view.events} transport={observer.view.transport} followLive={observer.view.followLive} viewPaused={observer.view.viewPaused} onFollowLive={observer.setFollowLive} onPauseView={observer.pauseView} onJumpLatest={observer.jumpToLatest} />;
  };

  return (
    <View style={styles.root} testID="live-build-workspace">
      <View style={[styles.header, compact && styles.headerCompact]}>
        <View style={styles.headerCopy}>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Back to conversation" onPress={onBack} style={styles.back}><Text style={styles.backText}>← Conversation</Text></TouchableOpacity>
          <Text style={styles.kicker}>LIVE BUILD · GOVERNED OBSERVER</Text>
          <Text style={styles.title}>Run observability</Text>
          <Text numberOfLines={2} style={styles.subtitle}>{run.id} · {run.state}{run.project_id ? ` · Project ${run.project_id}` : ''}</Text>
        </View>
        <View style={styles.headerState}><TinyPill tone={observer.view.transport === 'LIVE' ? 'olive' : observer.view.transport === 'ERROR' ? 'rust' : 'teal'}>{observer.view.transport}</TinyPill><Text style={styles.sequenceText}>{observer.view.events.length ? `Sequence ${observer.view.events[observer.view.events.length - 1].sequence}` : 'Awaiting persisted events'}</Text></View>
      </View>

      <View style={styles.pipelineWrap}><RunPipeline items={pipeline} /></View>

      {observer.view.unavailable ? (
        <View style={styles.unavailable} accessibilityLiveRegion="polite">
          <Text style={styles.unavailableTitle}>Live observation unavailable</Text>
          <Text style={styles.unavailableText}>{observer.view.error || 'The protected event routes are not active. Conversation and Engineering Run controls remain available.'}</Text>
          <TouchableOpacity accessibilityRole="button" onPress={observer.retry} style={styles.retry}><Text style={styles.retryText}>Retry observation</Text></TouchableOpacity>
        </View>
      ) : null}

      <View style={styles.tabBar} accessibilityRole="tablist">
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabContent}>
          {TABS.map((tab) => <TouchableOpacity key={tab} accessibilityRole="tab" accessibilityState={{ selected: observer.view.selectedTab === tab }} onPress={() => observer.setSelectedTab(tab)} style={[styles.tab, observer.view.selectedTab === tab && styles.tabActive]}><Text style={[styles.tabText, observer.view.selectedTab === tab && styles.tabTextActive]}>{tab}</Text></TouchableOpacity>)}
        </ScrollView>
      </View>

      {observer.view.readError ? <View style={styles.readError}><Text style={styles.readErrorText}>{observer.view.readError}</Text></View> : null}
      <View style={styles.body}>
        <View style={styles.primary}>{renderTab()}</View>
        {showContext ? <ContextRail observer={observer} run={run} /> : null}
      </View>
      {!showContext ? <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.mobileFacts}><Text style={styles.mobileFact}>Run {run.state}</Text><Text style={styles.mobileFact}>{observer.view.events.length} persisted events</Text><Text style={styles.mobileFact}>{observer.view.candidateLineage ? 'Candidate lineage observed' : 'No candidate lineage yet'}</Text></ScrollView> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, minHeight: 0, backgroundColor: 'rgba(251,247,238,0.76)' },
  header: { minHeight: 116, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 18, paddingHorizontal: 26, paddingTop: 16, paddingBottom: 13, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  headerCompact: { minHeight: 148, paddingHorizontal: 14, flexDirection: 'column', gap: 8 },
  headerCopy: { flex: 1, minWidth: 0 },
  back: { minHeight: 36, alignSelf: 'flex-start', justifyContent: 'center', paddingRight: 12 },
  backText: { color: palette.teal700, fontSize: 10, fontWeight: '700' },
  kicker: { color: palette.olive700, fontSize: 8, fontWeight: '800', letterSpacing: 1.05, marginTop: 2 },
  title: { color: palette.charcoal950, fontSize: 27, lineHeight: 32, fontWeight: '500', letterSpacing: -0.8, fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined, marginTop: 3 },
  subtitle: { color: palette.charcoal600, fontSize: 10, lineHeight: 15, marginTop: 3 },
  headerState: { alignItems: 'flex-end', gap: 6, paddingTop: 31 },
  sequenceText: { color: palette.charcoal450, fontSize: 8 },
  pipelineWrap: { minHeight: 72, paddingHorizontal: 20, backgroundColor: 'rgba(245,238,223,0.54)', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  pill: { minHeight: 24, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 9, borderRadius: 999, backgroundColor: palette.cream200 },
  pillOlive: { backgroundColor: palette.olive200 },
  pillTeal: { backgroundColor: palette.teal100 },
  pillRust: { backgroundColor: palette.rust100 },
  pillText: { color: palette.charcoal800, fontSize: 8, lineHeight: 11, fontWeight: '800' },
  unavailable: { marginHorizontal: 20, marginTop: 12, borderRadius: 14, padding: 13, backgroundColor: palette.rust100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(196,74,27,0.28)' },
  unavailableTitle: { color: palette.rust700, fontSize: 12, fontWeight: '800' },
  unavailableText: { color: palette.charcoal700, fontSize: 10, lineHeight: 16, marginTop: 4 },
  retry: { minHeight: 40, alignSelf: 'flex-start', justifyContent: 'center', paddingHorizontal: 12, borderRadius: 11, backgroundColor: palette.rust600, marginTop: 9 },
  retryText: { color: palette.ivory50, fontSize: 9, fontWeight: '800' },
  tabBar: { minHeight: 54, justifyContent: 'center', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  tabContent: { alignItems: 'center', gap: 4, paddingHorizontal: 20 },
  tab: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 13, borderRadius: 12 },
  tabActive: { backgroundColor: palette.rust600 },
  tabText: { color: palette.charcoal600, fontSize: 9, fontWeight: '800' },
  tabTextActive: { color: palette.ivory50 },
  body: { flex: 1, minHeight: 0, flexDirection: 'row', gap: 12, padding: 14 },
  primary: { flex: 1, minWidth: 0, minHeight: 0 },
  contextRail: { width: 250, gap: 10 },
  contextCard: { borderRadius: 17, backgroundColor: 'rgba(251,247,238,0.96)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, padding: 13 },
  contextTitle: { color: palette.charcoal950, fontSize: 14, fontWeight: '700', marginBottom: 10 },
  contextNote: { color: palette.charcoal600, fontSize: 9, lineHeight: 14 },
  alert: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  alertDot: { width: 7, height: 7, borderRadius: 4, marginTop: 4 },
  alertRust: { backgroundColor: palette.rust600 },
  alertOlive: { backgroundColor: palette.olive700 },
  alertTeal: { backgroundColor: palette.teal600 },
  alertCopy: { flex: 1, minWidth: 0 },
  alertTitle: { color: palette.charcoal800, fontSize: 10, fontWeight: '700', marginBottom: 2 },
  splitView: { flex: 1, minHeight: 300, flexDirection: 'row', borderRadius: 18, overflow: 'hidden', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, backgroundColor: 'rgba(251,247,238,0.96)' },
  fileColumn: { width: 240, flexGrow: 0, borderRightWidth: StyleSheet.hairlineWidth, borderRightColor: palette.border, backgroundColor: 'rgba(245,238,223,0.72)' },
  fileColumnContent: { padding: 12 },
  codeColumn: { flex: 1, minWidth: 0 },
  codeContent: { padding: 16 },
  sectionLabel: { color: palette.olive700, fontSize: 8, fontWeight: '800', letterSpacing: 0.85, marginBottom: 8 },
  sectionSpacing: { marginTop: 20 },
  lineageButton: { minHeight: 42, justifyContent: 'center', paddingHorizontal: 9, borderRadius: 10, marginBottom: 5 },
  lineageText: { color: palette.charcoal700, fontSize: 8 },
  fileButton: { minHeight: 42, justifyContent: 'center', paddingHorizontal: 9, borderRadius: 10, marginBottom: 4 },
  fileText: { color: palette.charcoal800, fontSize: 10, lineHeight: 14, fontWeight: '600' },
  mini: { color: palette.charcoal450, fontSize: 7, marginTop: 2 },
  selectedButton: { backgroundColor: palette.teal100 },
  codeHead: { minHeight: 40, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 10 },
  codePath: { flex: 1, color: palette.charcoal950, fontSize: 11, fontWeight: '700' },
  monospace: { color: palette.charcoal950, fontSize: 11, lineHeight: 18, fontFamily: Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : undefined },
  empty: { padding: 18, borderRadius: 14, backgroundColor: palette.cream100 },
  emptyText: { color: palette.charcoal600, fontSize: 10, lineHeight: 17 },
  muted: { color: palette.charcoal600, fontSize: 10, lineHeight: 16 },
  warning: { color: palette.rust700, fontSize: 9, marginTop: 8 },
  detailScroll: { flex: 1, minHeight: 300, borderRadius: 18, backgroundColor: 'rgba(251,247,238,0.96)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  detailContent: { padding: 16 },
  diffFile: { marginTop: 14, paddingTop: 14, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  factRow: { minHeight: 30, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 6 },
  factLabel: { flexShrink: 0, color: palette.charcoal450, fontSize: 8, fontWeight: '800', letterSpacing: 0.55, textTransform: 'uppercase' },
  factValue: { flex: 1, textAlign: 'right', color: palette.charcoal800, fontSize: 9, lineHeight: 13, fontWeight: '600' },
  evidenceGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  evidenceCard: { minWidth: 190, flexGrow: 1, flexBasis: 220, minHeight: 76, borderRadius: 13, padding: 11, backgroundColor: palette.cream100, justifyContent: 'space-between' },
  providerRow: { minHeight: 42, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  provider: { color: palette.charcoal950, fontSize: 10, fontWeight: '800' },
  providerValue: { flex: 1, textAlign: 'right', color: palette.charcoal600, fontSize: 9 },
  readError: { marginHorizontal: 14, marginTop: 8, borderRadius: 10, padding: 9, backgroundColor: palette.rust100 },
  readErrorText: { color: palette.rust700, fontSize: 9 },
  mobileFacts: { paddingHorizontal: 14, paddingBottom: 10, gap: 7 },
  mobileFact: { minHeight: 30, textAlignVertical: 'center', color: palette.charcoal600, fontSize: 8, paddingHorizontal: 10, paddingVertical: 7, borderRadius: 999, backgroundColor: palette.cream100 },
});
