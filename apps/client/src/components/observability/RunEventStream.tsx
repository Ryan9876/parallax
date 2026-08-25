import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import {
  componentHealth,
  evidenceAuditFacts,
  observabilitySummary,
  providerIdentities,
  type ComponentHealthItem,
} from '../../lib/observabilityProjection';
import type { RunEventDto, RunTransportState } from '../../lib/runObservability';
import { palette } from '../../theme';

function toneStyle(tone: ComponentHealthItem['tone']) {
  if (tone === 'rust') return styles.toneRust;
  if (tone === 'olive') return styles.toneOlive;
  if (tone === 'teal') return styles.toneTeal;
  return styles.toneNeutral;
}

function EventRow({ event }: { event: RunEventDto }) {
  const failed = event.outcome === 'FAILED' || event.outcome === 'DENIED';
  const review = event.outcome === 'HUMAN_REQUIRED';
  const recovering = event.outcome === 'RECOVERING' || event.outcome === 'REPLAYED';
  const attemptNumber = event.metadata.attempt_number;
  const retryCount = event.metadata.retry_count;
  return (
    <View style={styles.eventRow} testID={`run-event-${event.sequence}`}>
      <View style={[styles.dot, failed ? styles.dotFailed : review ? styles.dotReview : recovering ? styles.dotRecovering : styles.dotNormal]} />
      <View style={styles.eventCopy}>
        <View style={styles.eventHead}>
          <Text style={styles.sequence}>#{event.sequence}</Text>
          <Text style={styles.type}>{event.event_type.replaceAll('_', ' ')}</Text>
          {event.stage ? <Text style={styles.stage}>{event.stage}</Text> : null}
          <Text style={[styles.outcome, failed ? styles.outcomeFailed : review ? styles.outcomeReview : recovering ? styles.outcomeRecovering : null]}>{event.outcome.replaceAll('_', ' ')}</Text>
        </View>
        <Text style={styles.summary}>{event.summary || `${event.subsystem}${event.stage ? ` · ${event.stage}` : ''}`}</Text>
        <View style={styles.eventMetaRow}>
          <Text style={styles.time}>{new Date(event.occurred_at).toLocaleTimeString()} · {event.subsystem}</Text>
          {typeof attemptNumber === 'number' || typeof attemptNumber === 'string' ? <Text style={styles.metaChip}>attempt {String(attemptNumber)}</Text> : null}
          {typeof retryCount === 'number' || typeof retryCount === 'string' ? <Text style={styles.metaChip}>retry {String(retryCount)}</Text> : null}
          {event.failure_code ? <Text style={[styles.metaChip, styles.metaChipFailed]}>{event.failure_code}</Text> : null}
        </View>
      </View>
    </View>
  );
}

function SummaryStrip({ events }: { events: RunEventDto[] }) {
  const metrics = observabilitySummary(events);
  return (
    <View style={styles.summaryStrip} testID="observability-summary-strip">
      {metrics.map((metric) => (
        <View key={metric.key} style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>{metric.label}</Text>
          <Text style={[styles.summaryValue, metric.tone === 'rust' ? styles.summaryValueRust : metric.tone === 'teal' ? styles.summaryValueTeal : metric.tone === 'olive' ? styles.summaryValueOlive : null]}>{metric.value}</Text>
          <Text style={styles.summaryNote}>{metric.note}</Text>
        </View>
      ))}
    </View>
  );
}

function ComponentHealth({ events, transport }: { events: RunEventDto[]; transport: RunTransportState }) {
  const items = componentHealth(events, transport);
  return (
    <View style={styles.supportCard} testID="observability-component-health">
      <Text style={styles.supportKicker}>RUN-SCOPED SIGNALS</Text>
      <Text style={styles.supportTitle}>Component Health</Text>
      <Text style={styles.supportIntro}>Statuses reflect the latest persisted evidence for this run. Missing evidence stays unavailable.</Text>
      <View style={styles.supportRows}>
        {items.map((item) => (
          <View key={item.key} style={styles.healthRow}>
            <View style={styles.healthCopy}>
              <Text style={styles.healthLabel}>{item.label}</Text>
              <Text style={styles.healthDetail} numberOfLines={2}>{item.detail}</Text>
            </View>
            <View style={styles.healthStatusWrap}>
              <Text style={[styles.healthStatus, toneStyle(item.tone)]}>{item.status}</Text>
              {item.sequence ? <Text style={styles.healthSequence}>#{item.sequence}</Text> : null}
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

function EvidenceAudit({ events }: { events: RunEventDto[] }) {
  const facts = evidenceAuditFacts(events);
  const providers = providerIdentities(events);
  return (
    <View style={styles.supportCard} testID="observability-evidence-audit">
      <Text style={styles.supportKicker}>DURABLE REFERENCES</Text>
      <Text style={styles.supportTitle}>Evidence &amp; Audit</Text>
      <Text style={styles.supportIntro}>Only persisted identifiers are projected. Provider actions remain unavailable unless an accepted URL is explicitly present in evidence.</Text>
      <View style={styles.auditRows}>
        {facts.map((fact) => (
          <View key={fact.key} style={styles.auditRow}>
            <Text style={styles.auditLabel}>{fact.label}</Text>
            <Text selectable style={[styles.auditValue, !fact.available && styles.auditUnavailable]} numberOfLines={2}>{fact.value}</Text>
          </View>
        ))}
      </View>
      <View style={styles.providerBlock}>
        <Text style={styles.providerHeading}>Provider evidence</Text>
        {providers.length ? providers.map((provider) => (
          <View key={`${provider.provider}:${provider.sequence}`} style={styles.providerRow}>
            <Text style={styles.providerName}>{provider.provider}</Text>
            <View style={styles.providerRight}>
              <Text style={styles.providerIdentity}>{provider.identifier ?? 'Identifier unavailable'}</Text>
              <Text style={styles.providerStatus}>{provider.status} · #{provider.sequence}</Text>
            </View>
          </View>
        )) : <Text style={styles.auditUnavailable}>Unavailable — no persisted GitHub or Vercel provider result.</Text>}
      </View>
    </View>
  );
}

export function RunEventStream({
  events,
  transport,
  followLive,
  viewPaused,
  onFollowLive,
  onPauseView,
  onJumpLatest,
}: {
  events: RunEventDto[];
  transport: RunTransportState;
  followLive: boolean;
  viewPaused: boolean;
  onFollowLive: (value: boolean) => void;
  onPauseView: () => void;
  onJumpLatest: () => void;
}) {
  const ref = React.useRef<ScrollView>(null);
  const { width } = useWindowDimensions();
  const showSupportBesideStream = width >= 1120;

  React.useEffect(() => {
    if (followLive && !viewPaused) requestAnimationFrame(() => ref.current?.scrollToEnd({ animated: true }));
  }, [events.length, followLive, viewPaused]);

  return (
    <View style={styles.dashboard} accessibilityLabel="Run Event Stream" testID="observability-dashboard">
      <SummaryStrip events={events} />
      <View style={[styles.dashboardBody, showSupportBesideStream && styles.dashboardBodyWide]}>
        <View style={styles.streamPanel}>
          <View style={styles.toolbar}>
            <View style={styles.toolbarCopy}>
              <Text style={styles.eyebrow}>PRIMARY RUN NARRATIVE</Text>
              <Text style={styles.title}>Run Event Stream</Text>
              <Text style={styles.transport}>{transport.toLowerCase()} · {events.length ? `through durable sequence ${events.at(-1)?.sequence ?? '—'}` : 'no persisted events yet'}</Text>
            </View>
            <View style={styles.controls}>
              <TouchableOpacity accessibilityRole="button" accessibilityState={{ selected: followLive }} onPress={() => onFollowLive(!followLive)} style={[styles.control, followLive && styles.controlSelected]}>
                <Text style={styles.controlText}>Follow Live</Text>
              </TouchableOpacity>
              <TouchableOpacity accessibilityRole="button" accessibilityLabel="Pause View" onPress={onPauseView} style={[styles.control, viewPaused && styles.controlSelected]}>
                <Text style={styles.controlText}>{viewPaused ? 'Resume View' : 'Pause View'}</Text>
              </TouchableOpacity>
              <TouchableOpacity accessibilityRole="button" accessibilityLabel="Jump to Latest" onPress={onJumpLatest} style={styles.control}>
                <Text style={styles.controlText}>Latest</Text>
              </TouchableOpacity>
            </View>
          </View>
          {viewPaused ? (
            <View style={styles.pausedBanner} accessibilityRole="status">
              <Text style={styles.pausedTitle}>View paused</Text>
              <Text style={styles.pausedText}>Observation is paused locally. Run execution and persisted event capture are unchanged.</Text>
            </View>
          ) : null}
          <ScrollView ref={ref} style={styles.scroll} contentContainerStyle={styles.content} nestedScrollEnabled>
            {events.length ? events.map((event) => <EventRow event={event} key={`${event.id}:${event.sequence}`} />) : (
              <View style={styles.emptyState}>
                <Text style={styles.emptyTitle}>No persisted run events</Text>
                <Text style={styles.empty}>Parallax will not infer progress, health, retries, provider status or completion from an empty stream.</Text>
              </View>
            )}
          </ScrollView>
        </View>
        <View style={[styles.supportColumn, !showSupportBesideStream && styles.supportColumnStacked]}>
          <ComponentHealth events={events} transport={transport} />
          <EvidenceAudit events={events} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  dashboard: { flex: 1, minHeight: 520, gap: 12 },
  summaryStrip: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  summaryCard: { flexGrow: 1, flexBasis: 150, minHeight: 90, paddingHorizontal: 14, paddingVertical: 12, borderRadius: 16, backgroundColor: 'rgba(251,247,238,0.96)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  summaryLabel: { color: palette.charcoal600, fontSize: 9, fontWeight: '700', letterSpacing: 0.4, textTransform: 'uppercase' },
  summaryValue: { color: palette.charcoal950, fontSize: 23, lineHeight: 28, fontWeight: '800', marginTop: 5 },
  summaryValueRust: { color: palette.rust600 },
  summaryValueTeal: { color: palette.teal600 },
  summaryValueOlive: { color: palette.olive700 },
  summaryNote: { color: palette.charcoal450, fontSize: 8, lineHeight: 12, marginTop: 2 },
  dashboardBody: { flex: 1, minHeight: 410, gap: 12 },
  dashboardBodyWide: { flexDirection: 'row', alignItems: 'stretch' },
  streamPanel: { flex: 1, minWidth: 0, minHeight: 410, borderRadius: 18, backgroundColor: 'rgba(251,247,238,0.96)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, overflow: 'hidden' },
  toolbar: { minHeight: 82, paddingHorizontal: 16, paddingVertical: 12, flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  toolbarCopy: { flexGrow: 1, minWidth: 180 },
  eyebrow: { color: palette.rust600, fontSize: 8, fontWeight: '800', letterSpacing: 1.2 },
  title: { color: palette.charcoal950, fontSize: 18, fontWeight: '800', marginTop: 2 },
  transport: { color: palette.charcoal450, fontSize: 9, marginTop: 3 },
  controls: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 6 },
  control: { minHeight: 40, justifyContent: 'center', paddingHorizontal: 11, borderRadius: 12, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  controlSelected: { backgroundColor: palette.teal100, borderColor: palette.teal600 },
  controlText: { color: palette.charcoal800, fontSize: 9, fontWeight: '700' },
  pausedBanner: { paddingHorizontal: 16, paddingVertical: 10, backgroundColor: palette.teal100, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  pausedTitle: { color: palette.charcoal950, fontSize: 10, fontWeight: '800' },
  pausedText: { color: palette.charcoal600, fontSize: 9, lineHeight: 14, marginTop: 2 },
  scroll: { flex: 1, minHeight: 0 },
  content: { paddingHorizontal: 14, paddingBottom: 16 },
  eventRow: { minHeight: 72, flexDirection: 'row', gap: 11, paddingVertical: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  dot: { width: 8, height: 8, borderRadius: 4, marginTop: 7 },
  dotNormal: { backgroundColor: palette.teal600 },
  dotFailed: { backgroundColor: palette.rust600 },
  dotReview: { backgroundColor: palette.olive700 },
  dotRecovering: { backgroundColor: palette.teal600, borderWidth: 2, borderColor: palette.charcoal950 },
  eventCopy: { flex: 1, minWidth: 0 },
  eventHead: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 7 },
  sequence: { color: palette.charcoal450, fontSize: 8, fontWeight: '700' },
  type: { color: palette.charcoal950, fontSize: 9, fontWeight: '800' },
  stage: { color: palette.charcoal600, fontSize: 8, fontWeight: '800', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, backgroundColor: palette.cream100 },
  outcome: { color: palette.olive700, fontSize: 8, fontWeight: '800' },
  outcomeFailed: { color: palette.rust600 },
  outcomeReview: { color: palette.olive700 },
  outcomeRecovering: { color: palette.teal600 },
  summary: { color: palette.charcoal800, fontSize: 11, lineHeight: 16, marginTop: 5 },
  eventMetaRow: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 6, marginTop: 5 },
  time: { color: palette.charcoal450, fontSize: 8 },
  metaChip: { color: palette.charcoal600, fontSize: 8, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, backgroundColor: palette.cream100 },
  metaChipFailed: { color: palette.rust600 },
  emptyState: { minHeight: 220, alignItems: 'center', justifyContent: 'center', padding: 24 },
  emptyTitle: { color: palette.charcoal950, fontSize: 14, fontWeight: '800' },
  empty: { maxWidth: 430, color: palette.charcoal600, fontSize: 11, lineHeight: 18, textAlign: 'center', marginTop: 7 },
  supportColumn: { width: 310, gap: 12 },
  supportColumnStacked: { width: '100%' },
  supportCard: { padding: 14, borderRadius: 18, backgroundColor: 'rgba(251,247,238,0.96)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  supportKicker: { color: palette.rust600, fontSize: 7, fontWeight: '800', letterSpacing: 1.1 },
  supportTitle: { color: palette.charcoal950, fontSize: 15, fontWeight: '800', marginTop: 2 },
  supportIntro: { color: palette.charcoal450, fontSize: 8, lineHeight: 13, marginTop: 4, marginBottom: 8 },
  supportRows: { gap: 1 },
  healthRow: { minHeight: 47, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, paddingVertical: 7, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  healthCopy: { flex: 1, minWidth: 0 },
  healthLabel: { color: palette.charcoal800, fontSize: 9, fontWeight: '800' },
  healthDetail: { color: palette.charcoal450, fontSize: 7, lineHeight: 11, marginTop: 2 },
  healthStatusWrap: { alignItems: 'flex-end', maxWidth: 100 },
  healthStatus: { fontSize: 8, fontWeight: '800', textAlign: 'right' },
  healthSequence: { color: palette.charcoal450, fontSize: 7, marginTop: 2 },
  toneNeutral: { color: palette.charcoal450 },
  toneTeal: { color: palette.teal600 },
  toneOlive: { color: palette.olive700 },
  toneRust: { color: palette.rust600 },
  auditRows: { gap: 1 },
  auditRow: { paddingVertical: 6, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  auditLabel: { color: palette.charcoal450, fontSize: 7, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5 },
  auditValue: { color: palette.charcoal800, fontSize: 8, lineHeight: 12, marginTop: 2 },
  auditUnavailable: { color: palette.charcoal450, fontSize: 8, lineHeight: 12, fontStyle: 'italic' },
  providerBlock: { marginTop: 8, paddingTop: 8, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  providerHeading: { color: palette.charcoal950, fontSize: 9, fontWeight: '800', marginBottom: 4 },
  providerRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, paddingVertical: 5 },
  providerName: { color: palette.charcoal800, fontSize: 8, fontWeight: '800' },
  providerRight: { flex: 1, alignItems: 'flex-end' },
  providerIdentity: { color: palette.charcoal800, fontSize: 8, textAlign: 'right' },
  providerStatus: { color: palette.charcoal450, fontSize: 7, marginTop: 2 },
});
