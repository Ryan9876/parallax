import React from 'react';
import { Platform, ScrollView, StyleSheet, Text, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import type { EngineeringRunDto } from '../../lib/api';
import {
  observerHealth,
  projectPipeline,
  providerIdentities,
  recentAlerts,
  safeEventMetadata,
  type PipelineItem,
} from '../../lib/observabilityProjection';
import { useRunObservability, type LiveBuildTab } from '../../hooks/useRunObservability';
import { palette } from '../../theme';
import { RunEventStream } from './RunEventStream';
import { RunPipeline } from './RunPipeline';

const TABS: LiveBuildTab[] = ['Code', 'Diff', 'Terminal', 'Tests', 'Events', 'Evidence'];
const MOBILE_SECTIONS = ['Run', 'Activity', 'Code', 'Tests', 'Evidence', 'Health'] as const;
type MobileSection = typeof MOBILE_SECTIONS[number];

type Observer = ReturnType<typeof useRunObservability>;

function TinyPill({ children, tone = 'neutral' }: React.PropsWithChildren<{ tone?: 'neutral' | 'olive' | 'teal' | 'rust' }>) {
  return <View style={[styles.pill, tone === 'olive' ? styles.pillOlive : tone === 'teal' ? styles.pillTeal : tone === 'rust' ? styles.pillRust : null]}><Text style={styles.pillText}>{children}</Text></View>;
}

function Empty({ children }: React.PropsWithChildren) {
  return <View style={styles.empty}><Text style={styles.emptyText}>{children}</Text></View>;
}

function TechnicalText({ children }: React.PropsWithChildren) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator nestedScrollEnabled style={styles.technicalScroll} contentContainerStyle={styles.technicalContent}>
      <Text selectable style={styles.monospace}>{children}</Text>
    </ScrollView>
  );
}

function CodeView({ observer, compact = false }: { observer: Observer; compact?: boolean }) {
  const { view } = observer;
  React.useEffect(() => {
    if (compact && !view.selectedLineage && view.candidateLineage) void observer.loadTree(view.candidateLineage);
  }, [compact, observer, view.candidateLineage, view.selectedLineage]);

  return (
    <View style={[styles.splitView, compact && styles.splitViewCompact]}>
      <ScrollView style={[styles.fileColumn, compact && styles.fileColumnCompact]} contentContainerStyle={styles.fileColumnContent} nestedScrollEnabled>
        <Text style={styles.sectionLabel}>ACCEPTED LINEAGE</Text>
        {view.lineages.length ? view.lineages.map((lineage) => (
          <TouchableOpacity key={lineage} accessibilityRole="button" accessibilityLabel={`Inspect lineage ${lineage}`} onPress={() => void observer.loadTree(lineage)} style={[styles.lineageButton, view.selectedLineage === lineage && styles.selectedButton]}>
            <Text numberOfLines={1} style={styles.lineageText}>{lineage}</Text>
          </TouchableOpacity>
        )) : <Text style={styles.muted}>No source lineage has been observed for this run.</Text>}
        {view.sourceTree ? (
          <>
            <Text style={[styles.sectionLabel, styles.sectionSpacing]}>FILES · {view.sourceTree.file_count}</Text>
            {view.sourceTree.files.map((file) => (
              <TouchableOpacity key={file.path} accessibilityRole="button" accessibilityLabel={`Inspect file ${file.path}`} onPress={() => void observer.loadFile(file.path)} style={[styles.fileButton, view.selectedPath === file.path && styles.selectedButton]}>
                <Text numberOfLines={2} style={styles.fileText}>{file.path}</Text>
              </TouchableOpacity>
            ))}
          </>
        ) : null}
      </ScrollView>
      <ScrollView style={[styles.codeColumn, compact && styles.codeColumnCompact]} contentContainerStyle={styles.codeContent} nestedScrollEnabled>
        {view.sourceFile ? (
          <>
            <View style={styles.codeHead}><Text style={styles.codePath}>{view.sourceFile.path}</Text><TinyPill>{view.sourceFile.availability}</TinyPill></View>
            {view.sourceFile.availability === 'TEXT' && view.sourceFile.text !== null ? <TechnicalText>{view.sourceFile.text}</TechnicalText> : <Empty>Protected content is {view.sourceFile.availability.toLowerCase().replace('_', ' ')}.</Empty>}
          </>
        ) : <Empty>Select an observed lineage and file. Parallax does not browse outside exact run lineage.</Empty>}
      </ScrollView>
    </View>
  );
}

function DiffView({ observer }: { observer: Observer }) {
  const { view } = observer;
  React.useEffect(() => {
    if (!view.sourceDiff && view.parentLineage && view.candidateLineage) void observer.loadDiff();
  }, [observer, view.candidateLineage, view.parentLineage, view.sourceDiff]);
  if (!view.parentLineage || !view.candidateLineage) return <Empty>A parent and candidate lineage have not both been persisted for this run.</Empty>;
  if (!view.sourceDiff) return <Empty>{view.readBusy ? 'Loading protected lineage diff…' : 'Protected diff is not available yet.'}</Empty>;
  return (
    <ScrollView style={styles.detailScroll} contentContainerStyle={styles.detailContent} nestedScrollEnabled>
      <View style={styles.factRow}><Text style={styles.factLabel}>FROM</Text><Text numberOfLines={1} style={styles.factValue}>{view.sourceDiff.from_lineage}</Text></View>
      <View style={styles.factRow}><Text style={styles.factLabel}>TO</Text><Text numberOfLines={1} style={styles.factValue}>{view.sourceDiff.to_lineage}</Text></View>
      {view.sourceDiff.files.length ? view.sourceDiff.files.map((file) => (
        <View key={`${file.change_type}:${file.path}`} style={styles.diffFile}>
          <View style={styles.codeHead}><Text style={styles.codePath}>{file.change_type} · {file.path}</Text><TinyPill>{file.availability}</TinyPill></View>
          {file.diff_text ? <TechnicalText>{file.diff_text}</TechnicalText> : <Text style={styles.muted}>No bounded text diff is available for this file.</Text>}
          {file.truncated ? <Text style={styles.warning}>Diff truncated by protected response bounds.</Text> : null}
        </View>
      )) : <Empty>No changed files were returned by the protected diff.</Empty>}
    </ScrollView>
  );
}

function AttemptView({ observer, testsOnly, compact = false }: { observer: Observer; testsOnly?: boolean; compact?: boolean }) {
  const { view } = observer;
  const eligible = view.events.filter((event) => event.attempt_id && (!testsOnly || event.stage === 'TEST'));
  return (
    <View style={[styles.splitView, compact && styles.splitViewCompact]}>
      <ScrollView style={[styles.fileColumn, compact && styles.fileColumnCompact]} contentContainerStyle={styles.fileColumnContent} nestedScrollEnabled>
        <Text style={styles.sectionLabel}>{testsOnly ? 'TEST ATTEMPTS' : 'BOUNDED ATTEMPTS'}</Text>
        {eligible.length ? eligible.map((event) => (
          <TouchableOpacity key={`${event.attempt_id}:${event.sequence}`} accessibilityRole="button" accessibilityLabel={`Inspect ${event.stage || event.subsystem} attempt sequence ${event.sequence}`} onPress={() => event.attempt_id && void observer.loadEvidence(event.attempt_id)} style={[styles.fileButton, view.selectedAttempt === event.attempt_id && styles.selectedButton]}>
            <Text style={styles.fileText}>{event.stage || event.subsystem} · #{event.sequence}</Text>
            <Text style={styles.mini}>{event.outcome}</Text>
          </TouchableOpacity>
        )) : <Text style={styles.muted}>No persisted {testsOnly ? 'test ' : ''}attempt evidence is available.</Text>}
      </ScrollView>
      <ScrollView style={[styles.codeColumn, compact && styles.codeColumnCompact]} contentContainerStyle={styles.codeContent} nestedScrollEnabled>
        {view.evidence ? (
          <>
            <View style={styles.codeHead}><Text style={styles.codePath}>{view.evidence.stage} · attempt {view.evidence.attempt_number}</Text><TinyPill tone={view.evidence.availability === 'AVAILABLE' ? 'olive' : 'rust'}>{view.evidence.availability}</TinyPill></View>
            <View style={styles.factRow}><Text style={styles.factLabel}>STATUS</Text><Text style={styles.factValue}>{view.evidence.status}</Text></View>
            {view.evidence.failure_code ? <View style={styles.factRow}><Text style={styles.factLabel}>FAILURE</Text><Text style={styles.factValue}>{view.evidence.failure_code}</Text></View> : null}
            <View style={styles.factRow}><Text style={styles.factLabel}>TOOL</Text><Text style={styles.factValue}>{view.evidence.tool_id || 'Not recorded'}</Text></View>
            <View style={styles.factRow}><Text style={styles.factLabel}>PROGRAM</Text><Text style={styles.factValue}>{view.evidence.program_id || 'Not recorded'}</Text></View>
            {view.evidence.availability === 'AVAILABLE' ? <TechnicalText>{JSON.stringify(view.evidence.evidence, null, 2)}</TechnicalText> : <Empty>Evidence is {view.evidence.availability.toLowerCase()} by the protected API.</Empty>}
          </>
        ) : <Empty>Select an observed attempt. This is read-only protected evidence, not an interactive shell.</Empty>}
      </ScrollView>
    </View>
  );
}

function EvidenceView({ observer }: { observer: Observer }) {
  const providers = providerIdentities(observer.view.events);
  const latest = observer.view.events[observer.view.events.length - 1];
  const metadata = latest ? safeEventMetadata(latest) : [];
  return (
    <ScrollView style={styles.detailScroll} contentContainerStyle={styles.detailContent} nestedScrollEnabled>
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

function ContextRail({ observer, run, stacked = false }: { observer: Observer; run: EngineeringRunDto; stacked?: boolean }) {
  const health = observerHealth(observer.view.transport, run, observer.view.events);
  const last = observer.view.events[observer.view.events.length - 1];
  const eventAlerts = recentAlerts(observer.view.events);
  const durableFailureAlert = run.state === 'FAILED'
    && !eventAlerts.some((alert) => Boolean(run.last_failure_code) && alert.detail.includes(run.last_failure_code || ''))
    ? {
        key: 'durable-run-failure',
        sequence: last?.sequence ?? 0,
        tone: 'rust' as const,
        title: 'Durable run failure',
        detail: `${run.resume_stage || 'Run'} failed${run.last_failure_code ? ` · ${run.last_failure_code}` : ''}.`,
      }
    : null;
  const alerts = durableFailureAlert ? [durableFailureAlert, ...eventAlerts].slice(0, 5) : eventAlerts;
  return (
    <View style={[styles.contextRail, stacked && styles.contextRailStacked]} accessibilityLabel="Live Build contextual health">
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
        {run.last_failure_code ? <View style={styles.factRow}><Text style={styles.factLabel}>FAILURE</Text><Text style={[styles.factValue, styles.failureValue]}>{run.resume_stage || 'FAILED'} · {run.last_failure_code}</Text></View> : null}
      </View>
      <View style={styles.contextCard}>
        <Text style={styles.contextTitle}>Recent Alerts</Text>
        {alerts.length ? alerts.map((alert) => <View key={alert.key} style={styles.alert}><View style={[styles.alertDot, alert.tone === 'rust' ? styles.alertRust : alert.tone === 'olive' ? styles.alertOlive : styles.alertTeal]} /><View style={styles.alertCopy}><Text style={styles.alertTitle}>{alert.title}</Text><Text style={styles.contextNote}>{alert.detail}</Text></View></View>) : <Text style={styles.contextNote}>No persisted failure, recovery or human-review alert is present.</Text>}
      </View>
    </View>
  );
}

function RunOverview({ observer, run, pipeline }: { observer: Observer; run: EngineeringRunDto; pipeline: PipelineItem[] }) {
  const current = pipeline.find((item) => ['ACTIVE', 'FAILED', 'RECOVERING', 'HUMAN_REQUIRED'].includes(item.status))
    ?? [...pipeline].reverse().find((item) => item.status === 'COMPLETE')
    ?? pipeline[0];
  const latestAttempt = [...observer.view.events].reverse().find((event) => event.attempt_id);
  const latestRecovery = [...observer.view.events].reverse().find((event) => ['RECOVERING', 'REPLAYED'].includes(event.outcome));
  const latest = observer.view.events.at(-1);

  return (
    <ScrollView style={styles.detailScroll} contentContainerStyle={styles.runOverview} nestedScrollEnabled>
      <View style={styles.runHero}>
        <View style={styles.runHeroCopy}>
          <Text style={styles.sectionLabel}>CURRENT AUTHORITATIVE STAGE</Text>
          <Text style={styles.runStage}>{current?.stage || run.state}</Text>
          <Text style={styles.runStageStatus}>{current?.status.replace('_', ' ') || run.state}</Text>
        </View>
        <TinyPill tone={current?.status === 'FAILED' ? 'rust' : current?.status === 'ACTIVE' || current?.status === 'RECOVERING' ? 'teal' : 'olive'}>{run.state}</TinyPill>
      </View>
      {run.state === 'FAILED' ? (
        <View style={styles.runFailure} accessibilityLiveRegion="polite" testID="live-build-durable-failure">
          <Text style={styles.runFailureTitle}>{run.resume_stage || 'Run'} failed</Text>
          <Text style={styles.runFailureCode}>{run.last_failure_code || 'Failure code unavailable'}</Text>
          <Text style={styles.contextNote}>This is authoritative Engineering Run state. Missing optional worker, provider, preview, lineage, or evaluation evidence does not mean the run is still waiting.</Text>
        </View>
      ) : null}
      <View style={styles.runCardGrid}>
        <View style={styles.runCard}><Text style={styles.factLabel}>LATEST EVENT</Text><Text style={styles.runCardValue}>{latest ? `#${latest.sequence} · ${latest.outcome.replaceAll('_', ' ')}` : 'No persisted event'}</Text><Text style={styles.contextNote}>{latest?.summary || 'Waiting for persisted run evidence.'}</Text></View>
        <View style={styles.runCard}><Text style={styles.factLabel}>LATEST ATTEMPT</Text><Text style={styles.runCardValue}>{latestAttempt ? `${latestAttempt.stage || latestAttempt.subsystem} · #${latestAttempt.sequence}` : 'Not recorded'}</Text><Text style={styles.contextNote}>{latestAttempt ? latestAttempt.outcome.replaceAll('_', ' ') : 'No bounded attempt evidence has been observed.'}</Text></View>
        <View style={styles.runCard}><Text style={styles.factLabel}>RECOVERY / RETRY</Text><Text style={styles.runCardValue}>{latestRecovery ? latestRecovery.outcome.replaceAll('_', ' ') : 'No active recovery fact'}</Text><Text style={styles.contextNote}>{latestRecovery?.summary || 'Retries and recovery appear only when persisted by the run.'}</Text></View>
        <View style={styles.runCard}><Text style={styles.factLabel}>SOURCE LINEAGE</Text><Text numberOfLines={2} selectable style={styles.runCardValue}>{observer.view.candidateLineage || 'Not observed yet'}</Text><Text style={styles.contextNote}>{observer.view.parentLineage ? 'Parent / last-known lineage is available for protected comparison.' : 'No persisted parent lineage is available.'}</Text></View>
      </View>
    </ScrollView>
  );
}

function FocusedSwitcher({
  first,
  second,
  active,
  onSelect,
}: {
  first: { key: LiveBuildTab; label: string; accessibilityLabel: string };
  second: { key: LiveBuildTab; label: string; accessibilityLabel: string };
  active: LiveBuildTab;
  onSelect: (tab: LiveBuildTab) => void;
}) {
  return (
    <View style={styles.focusedSwitcher} accessibilityRole="tablist">
      {[first, second].map((item) => (
        <TouchableOpacity key={item.key} accessibilityRole="tab" accessibilityLabel={item.accessibilityLabel} accessibilityState={{ selected: active === item.key }} onPress={() => onSelect(item.key)} style={[styles.focusedSwitch, active === item.key && styles.focusedSwitchActive]}>
          <Text style={[styles.focusedSwitchText, active === item.key && styles.focusedSwitchTextActive]}>{item.label}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

export function LiveBuildWorkspace({ run, onBack }: { run: EngineeringRunDto; onBack: () => void }) {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const focused = width < 1100;
  const showContext = width >= 1180;
  const observer = useRunObservability(run, true);
  const pipeline = React.useMemo(() => projectPipeline(run, observer.view.events), [observer.view.events, run]);
  const [mobileSection, setMobileSection] = React.useState<MobileSection>('Activity');

  const selectMobileSection = React.useCallback((section: MobileSection) => {
    setMobileSection(section);
    if (section === 'Activity') observer.setSelectedTab('Events');
    else if (section === 'Evidence') observer.setSelectedTab('Evidence');
    else if (section === 'Code' && !['Code', 'Diff'].includes(observer.view.selectedTab)) observer.setSelectedTab('Code');
    else if (section === 'Tests' && !['Tests', 'Terminal'].includes(observer.view.selectedTab)) observer.setSelectedTab('Tests');
  }, [observer]);

  const renderDesktopTab = () => {
    if (observer.view.selectedTab === 'Code') return <CodeView observer={observer} />;
    if (observer.view.selectedTab === 'Diff') return <DiffView observer={observer} />;
    if (observer.view.selectedTab === 'Terminal') return <AttemptView observer={observer} />;
    if (observer.view.selectedTab === 'Tests') return <AttemptView observer={observer} testsOnly />;
    if (observer.view.selectedTab === 'Evidence') return <EvidenceView observer={observer} />;
    return <RunEventStream run={run} events={observer.view.events} transport={observer.view.transport} followLive={observer.view.followLive} viewPaused={observer.view.viewPaused} onFollowLive={observer.setFollowLive} onPauseView={observer.pauseView} onJumpLatest={observer.jumpToLatest} />;
  };

  const renderFocusedSection = () => {
    if (mobileSection === 'Run') return <RunOverview observer={observer} run={run} pipeline={pipeline} />;
    if (mobileSection === 'Activity') return <RunEventStream compact run={run} events={observer.view.events} transport={observer.view.transport} followLive={observer.view.followLive} viewPaused={observer.view.viewPaused} onFollowLive={observer.setFollowLive} onPauseView={observer.pauseView} onJumpLatest={observer.jumpToLatest} />;
    if (mobileSection === 'Code') return (
      <View style={styles.focusedSection}>
        <FocusedSwitcher first={{ key: 'Code', label: 'Source', accessibilityLabel: 'Show source code' }} second={{ key: 'Diff', label: 'Diff', accessibilityLabel: 'Show source diff' }} active={observer.view.selectedTab} onSelect={observer.setSelectedTab} />
        <View style={styles.focusedContent}>{observer.view.selectedTab === 'Diff' ? <DiffView observer={observer} /> : <CodeView observer={observer} compact />}</View>
      </View>
    );
    if (mobileSection === 'Tests') return (
      <View style={styles.focusedSection}>
        <FocusedSwitcher first={{ key: 'Tests', label: 'Tests', accessibilityLabel: 'Show test evidence' }} second={{ key: 'Terminal', label: 'Command output', accessibilityLabel: 'Show bounded command output' }} active={observer.view.selectedTab} onSelect={observer.setSelectedTab} />
        <View style={styles.focusedContent}>{observer.view.selectedTab === 'Terminal' ? <AttemptView observer={observer} compact /> : <AttemptView observer={observer} testsOnly compact />}</View>
      </View>
    );
    if (mobileSection === 'Evidence') return <EvidenceView observer={observer} />;
    return <ScrollView style={styles.detailScroll} contentContainerStyle={styles.healthStack}><ContextRail observer={observer} run={run} stacked /></ScrollView>;
  };

  const workspaceContent = (
    <>
      <View style={[styles.header, compact && styles.headerCompact]}>
        <View style={styles.headerCopy}>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Back to conversation" onPress={onBack} style={styles.back}><Text style={styles.backText}>← Conversation</Text></TouchableOpacity>
          <Text style={styles.kicker}>LIVE BUILD · GOVERNED OBSERVER</Text>
          <Text style={styles.title}>Run observability</Text>
          <Text numberOfLines={2} style={styles.subtitle}>{run.id} · {run.state}{run.project_id ? ` · Project ${run.project_id}` : ''}</Text>
        </View>
        <View style={[styles.headerState, compact && styles.headerStateCompact]}><TinyPill tone={observer.view.transport === 'LIVE' ? 'olive' : observer.view.transport === 'ERROR' ? 'rust' : 'teal'}>{observer.view.transport}</TinyPill><Text style={styles.sequenceText}>{observer.view.events.length ? `Sequence ${observer.view.events.at(-1)?.sequence ?? '—'}` : 'Awaiting persisted events'}</Text></View>
      </View>

      <View style={[styles.pipelineWrap, compact && styles.pipelineWrapCompact]}><RunPipeline items={pipeline} /></View>

      {observer.view.unavailable ? (
        <View style={styles.unavailable} accessibilityLiveRegion="polite">
          <Text style={styles.unavailableTitle}>Live observation unavailable</Text>
          <Text style={styles.unavailableText}>{observer.view.error || 'The protected event routes are not active. Conversation and Engineering Run controls remain available.'}</Text>
          <TouchableOpacity accessibilityRole="button" onPress={observer.retry} style={styles.retry}><Text style={styles.retryText}>Retry observation</Text></TouchableOpacity>
        </View>
      ) : null}

      {focused ? (
        <View style={styles.mobileSectionBar} accessibilityRole="tablist" testID="live-build-focused-navigation">
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.mobileSectionContent}>
            {MOBILE_SECTIONS.map((section) => (
              <TouchableOpacity key={section} accessibilityRole="tab" accessibilityState={{ selected: mobileSection === section }} onPress={() => selectMobileSection(section)} style={[styles.mobileSectionTab, mobileSection === section && styles.mobileSectionTabActive]}>
                <Text style={[styles.mobileSectionText, mobileSection === section && styles.mobileSectionTextActive]}>{section}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      ) : (
        <View style={styles.tabBar} accessibilityRole="tablist">
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tabContent}>
            {TABS.map((tab) => <TouchableOpacity key={tab} accessibilityRole="tab" accessibilityState={{ selected: observer.view.selectedTab === tab }} onPress={() => observer.setSelectedTab(tab)} style={[styles.tab, observer.view.selectedTab === tab && styles.tabActive]}><Text style={[styles.tabText, observer.view.selectedTab === tab && styles.tabTextActive]}>{tab}</Text></TouchableOpacity>)}
          </ScrollView>
        </View>
      )}

      {observer.view.readError ? <View style={styles.readError}><Text style={styles.readErrorText}>{observer.view.readError}</Text></View> : null}
      <View style={[styles.body, focused && styles.bodyFocused]}>
        <View style={styles.primary}>{focused ? renderFocusedSection() : renderDesktopTab()}</View>
        {!focused && showContext ? <ContextRail observer={observer} run={run} /> : null}
      </View>
    </>
  );

  return (
    <View style={styles.root} testID="live-build-workspace">
      {compact ? (
        <ScrollView
          style={styles.mobileRootScroll}
          contentContainerStyle={styles.mobileRootContent}
          nestedScrollEnabled
          showsVerticalScrollIndicator={false}
          testID="live-build-mobile-scroll"
        >
          {workspaceContent}
        </ScrollView>
      ) : workspaceContent}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, minHeight: 0, backgroundColor: 'rgba(251,247,238,0.76)' },
  mobileRootScroll: { flex: 1, minHeight: 0 },
  mobileRootContent: { flexGrow: 1, paddingBottom: 18 },
  header: { minHeight: 116, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 18, paddingHorizontal: 26, paddingTop: 16, paddingBottom: 13, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  headerCompact: { minHeight: 148, paddingHorizontal: 14, flexDirection: 'column', gap: 8 },
  headerCopy: { flex: 1, minWidth: 0 },
  back: { minHeight: 44, alignSelf: 'flex-start', justifyContent: 'center', paddingRight: 12 },
  backText: { color: palette.teal700, fontSize: 10, fontWeight: '700' },
  kicker: { color: palette.olive700, fontSize: 8, fontWeight: '800', letterSpacing: 1.05, marginTop: 2 },
  title: { color: palette.charcoal950, fontSize: 27, lineHeight: 32, fontWeight: '500', letterSpacing: -0.8, fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined, marginTop: 3 },
  subtitle: { color: palette.charcoal600, fontSize: 10, lineHeight: 15, marginTop: 3 },
  headerState: { alignItems: 'flex-end', gap: 6, paddingTop: 31 },
  headerStateCompact: { alignItems: 'flex-start', paddingTop: 0, flexDirection: 'row' },
  sequenceText: { color: palette.charcoal450, fontSize: 8 },
  pipelineWrap: { minHeight: 72, paddingHorizontal: 20, backgroundColor: 'rgba(245,238,223,0.54)', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  pipelineWrapCompact: { paddingHorizontal: 10 },
  pill: { minHeight: 24, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 9, borderRadius: 999, backgroundColor: palette.cream200 },
  pillOlive: { backgroundColor: palette.olive200 },
  pillTeal: { backgroundColor: palette.teal100 },
  pillRust: { backgroundColor: palette.rust100 },
  pillText: { color: palette.charcoal800, fontSize: 8, lineHeight: 11, fontWeight: '800' },
  unavailable: { marginHorizontal: 20, marginTop: 12, borderRadius: 14, padding: 13, backgroundColor: palette.rust100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(196,74,27,0.28)' },
  unavailableTitle: { color: palette.rust700, fontSize: 12, fontWeight: '800' },
  unavailableText: { color: palette.charcoal800, fontSize: 10, lineHeight: 16, marginTop: 4 },
  retry: { minHeight: 44, alignSelf: 'flex-start', justifyContent: 'center', paddingHorizontal: 14, borderRadius: 11, backgroundColor: palette.rust600, marginTop: 9 },
  retryText: { color: palette.ivory50, fontSize: 9, fontWeight: '800' },
  tabBar: { minHeight: 54, justifyContent: 'center', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  tabContent: { alignItems: 'center', gap: 4, paddingHorizontal: 20 },
  tab: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 13, borderRadius: 12 },
  tabActive: { backgroundColor: palette.rust600 },
  tabText: { color: palette.charcoal600, fontSize: 9, fontWeight: '800' },
  tabTextActive: { color: palette.ivory50 },
  mobileSectionBar: { minHeight: 58, justifyContent: 'center', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border, backgroundColor: 'rgba(245,238,223,0.5)' },
  mobileSectionContent: { alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 7 },
  mobileSectionTab: { minHeight: 44, minWidth: 64, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 12, borderRadius: 13, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, backgroundColor: palette.ivory50 },
  mobileSectionTabActive: { backgroundColor: palette.rust600, borderColor: palette.rust600 },
  mobileSectionText: { color: palette.charcoal600, fontSize: 9, fontWeight: '800' },
  mobileSectionTextActive: { color: palette.ivory50 },
  body: { flex: 1, minHeight: 0, flexDirection: 'row', gap: 12, padding: 14 },
  bodyFocused: { padding: 10 },
  primary: { flex: 1, minWidth: 0, minHeight: 0 },
  contextRail: { width: 250, gap: 10 },
  contextRailStacked: { width: '100%' },
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
  splitViewCompact: { flexDirection: 'column', minHeight: 0, overflow: 'hidden' },
  fileColumn: { width: 240, flexGrow: 0, borderRightWidth: StyleSheet.hairlineWidth, borderRightColor: palette.border, backgroundColor: 'rgba(245,238,223,0.72)' },
  fileColumnCompact: { width: '100%', flexGrow: 0, flexShrink: 1, maxHeight: 188, borderRightWidth: 0, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  fileColumnContent: { padding: 12 },
  codeColumn: { flex: 1, minWidth: 0 },
  codeColumnCompact: { flex: 1, minHeight: 0 },
  codeContent: { padding: 16 },
  sectionLabel: { color: palette.olive700, fontSize: 8, fontWeight: '800', letterSpacing: 0.85, marginBottom: 8 },
  sectionSpacing: { marginTop: 20 },
  lineageButton: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 9, borderRadius: 10, marginBottom: 5 },
  lineageText: { color: palette.charcoal800, fontSize: 8 },
  fileButton: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 9, borderRadius: 10, marginBottom: 4 },
  fileText: { color: palette.charcoal800, fontSize: 10, lineHeight: 14, fontWeight: '600' },
  mini: { color: palette.charcoal450, fontSize: 7, marginTop: 2 },
  selectedButton: { backgroundColor: palette.teal100 },
  codeHead: { minHeight: 40, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginBottom: 10 },
  codePath: { flex: 1, color: palette.charcoal950, fontSize: 11, fontWeight: '700' },
  technicalScroll: { flexGrow: 0, maxWidth: '100%' },
  technicalContent: { minWidth: '100%', paddingBottom: 8 },
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
  providerRow: { minHeight: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  provider: { color: palette.charcoal950, fontSize: 10, fontWeight: '800' },
  providerValue: { flex: 1, textAlign: 'right', color: palette.charcoal600, fontSize: 9 },
  readError: { marginHorizontal: 14, marginTop: 8, borderRadius: 10, padding: 9, backgroundColor: palette.rust100 },
  readErrorText: { color: palette.rust700, fontSize: 9 },
  focusedSection: { flex: 1, minHeight: 0, gap: 10 },
  focusedSwitcher: { minHeight: 52, flexDirection: 'row', gap: 8, padding: 4, borderRadius: 15, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  focusedSwitch: { flex: 1, minHeight: 44, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 12, borderRadius: 11 },
  focusedSwitchActive: { backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.teal600 },
  focusedSwitchText: { color: palette.charcoal600, fontSize: 9, fontWeight: '800' },
  focusedSwitchTextActive: { color: palette.teal700 },
  focusedContent: { flex: 1, minHeight: 0 },
  runOverview: { padding: 14, gap: 12 },
  runHero: { minHeight: 104, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, padding: 16, borderRadius: 17, backgroundColor: palette.cream100 },
  runHeroCopy: { flex: 1, minWidth: 0 },
  runStage: { color: palette.charcoal950, fontSize: 24, lineHeight: 29, fontWeight: '700', fontFamily: Platform.OS === 'web' ? 'Georgia, ui-serif, serif' : undefined },
  runStageStatus: { color: palette.teal700, fontSize: 10, fontWeight: '800', marginTop: 4 },
  runFailure: { padding: 14, borderRadius: 15, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(196,74,27,0.32)', backgroundColor: palette.rust100 },
  runFailureTitle: { color: palette.rust700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  runFailureCode: { color: palette.rust700, fontSize: 10, lineHeight: 15, fontWeight: '700', marginTop: 3, marginBottom: 5 },
  failureValue: { color: palette.rust700 },
  runCardGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  runCard: { minWidth: 220, flexGrow: 1, flexBasis: 260, minHeight: 108, justifyContent: 'space-between', gap: 8, padding: 14, borderRadius: 15, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, backgroundColor: palette.ivory50 },
  runCardValue: { color: palette.charcoal950, fontSize: 12, lineHeight: 17, fontWeight: '700' },
  healthStack: { padding: 2 },
});
