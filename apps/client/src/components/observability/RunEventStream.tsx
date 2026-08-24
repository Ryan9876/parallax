import React from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { RunEventDto, RunTransportState } from '../../lib/runObservability';
import { palette } from '../../theme';

function EventRow({ event }: { event: RunEventDto }) {
  const attention = ['FAILED', 'DENIED'].includes(event.outcome);
  const review = event.outcome === 'HUMAN_REQUIRED';
  return (
    <View style={styles.eventRow} testID={`run-event-${event.sequence}`}>
      <View style={[styles.dot, attention ? styles.dotFailed : review ? styles.dotReview : styles.dotNormal]} />
      <View style={styles.eventCopy}>
        <View style={styles.eventHead}>
          <Text style={styles.sequence}>#{event.sequence}</Text>
          <Text style={styles.type}>{event.event_type.replaceAll('_', ' ')}</Text>
          <Text style={styles.outcome}>{event.outcome.replaceAll('_', ' ')}</Text>
        </View>
        <Text style={styles.summary}>{event.summary || `${event.subsystem}${event.stage ? ` · ${event.stage}` : ''}`}</Text>
        <Text style={styles.time}>{new Date(event.occurred_at).toLocaleTimeString()} · {event.subsystem}</Text>
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
  React.useEffect(() => {
    if (followLive && !viewPaused) requestAnimationFrame(() => ref.current?.scrollToEnd({ animated: true }));
  }, [events.length, followLive, viewPaused]);

  return (
    <View style={styles.wrap} accessibilityLabel="Run Event Stream">
      <View style={styles.toolbar}>
        <View>
          <Text style={styles.title}>Run Event Stream</Text>
          <Text style={styles.transport}>{transport.toLowerCase()} · {events.length ? `through sequence ${events[events.length - 1].sequence}` : 'no persisted events yet'}</Text>
        </View>
        <View style={styles.controls}>
          <TouchableOpacity accessibilityRole="button" accessibilityState={{ selected: followLive }} onPress={() => onFollowLive(!followLive)} style={[styles.control, followLive && styles.controlSelected]}>
            <Text style={styles.controlText}>Follow Live</Text>
          </TouchableOpacity>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Pause View" onPress={onPauseView} style={[styles.control, viewPaused && styles.controlSelected]}>
            <Text style={styles.controlText}>Pause View</Text>
          </TouchableOpacity>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="Jump to Latest" onPress={onJumpLatest} style={styles.control}>
            <Text style={styles.controlText}>Latest</Text>
          </TouchableOpacity>
        </View>
      </View>
      <ScrollView ref={ref} style={styles.scroll} contentContainerStyle={styles.content} nestedScrollEnabled>
        {events.length ? events.map((event) => <EventRow event={event} key={`${event.id}:${event.sequence}`} />) : <Text style={styles.empty}>No persisted run events are available yet. Parallax will not infer progress from an empty stream.</Text>}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, minHeight: 300, borderRadius: 18, backgroundColor: 'rgba(251,247,238,0.96)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, overflow: 'hidden' },
  toolbar: { minHeight: 72, paddingHorizontal: 16, paddingVertical: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  title: { color: palette.charcoal950, fontSize: 16, fontWeight: '700' },
  transport: { color: palette.charcoal450, fontSize: 9, marginTop: 3 },
  controls: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'flex-end', gap: 6 },
  control: { minHeight: 40, justifyContent: 'center', paddingHorizontal: 11, borderRadius: 12, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  controlSelected: { backgroundColor: palette.teal100, borderColor: palette.teal600 },
  controlText: { color: palette.charcoal800, fontSize: 9, fontWeight: '700' },
  scroll: { flex: 1, minHeight: 0 },
  content: { padding: 14 },
  eventRow: { minHeight: 64, flexDirection: 'row', gap: 11, paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.border },
  dot: { width: 8, height: 8, borderRadius: 4, marginTop: 6 },
  dotNormal: { backgroundColor: palette.teal600 },
  dotFailed: { backgroundColor: palette.rust600 },
  dotReview: { backgroundColor: palette.olive700 },
  eventCopy: { flex: 1, minWidth: 0 },
  eventHead: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: 7 },
  sequence: { color: palette.charcoal450, fontSize: 8, fontWeight: '700' },
  type: { color: palette.charcoal950, fontSize: 9, fontWeight: '800' },
  outcome: { color: palette.olive700, fontSize: 8, fontWeight: '700' },
  summary: { color: palette.charcoal800, fontSize: 11, lineHeight: 16, marginTop: 4 },
  time: { color: palette.charcoal450, fontSize: 8, marginTop: 4 },
  empty: { color: palette.charcoal600, fontSize: 11, lineHeight: 18, padding: 12 },
});
