import React from 'react';
import { Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { ConversationDto } from '../lib/api';
import { palette } from '../theme';

type Props = {
  conversation: ConversationDto | undefined;
  onStartCodeWork(): void;
};

function Fact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <View style={styles.fact}>
      <Text style={styles.factLabel}>{label}</Text>
      <Text selectable={mono} numberOfLines={mono ? 2 : 1} style={[styles.factValue, mono && styles.mono]}>{value}</Text>
    </View>
  );
}

export function EditorialProjectWorkspace({ conversation, onStartCodeWork }: Props) {
  const binding = conversation?.project_binding_status ?? null;
  const projectId = conversation?.project_id ?? null;
  const bound = binding === 'PROJECT_BOUND' && Boolean(projectId);
  const historical = binding === 'HISTORICAL_UNBOUND' && conversation?.mode === 'code';

  return (
    <View style={styles.wrap} testID="editorial-project-workspace">
      <View style={styles.intro}>
        <Text style={styles.kicker}>Canonical project context</Text>
        <Text style={styles.title}>Projects stay explicit.</Text>
        <Text style={styles.copy}>The shell reflects the authenticated conversation’s canonical Project binding. Repository, workspace and execution authority remain server-owned.</Text>
      </View>

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View>
            <Text style={styles.cardKicker}>Current conversation</Text>
            <Text numberOfLines={1} style={styles.cardTitle}>{conversation?.title ?? 'No conversation selected'}</Text>
          </View>
          <View style={[styles.statePill, bound ? styles.stateBound : historical ? styles.stateHistorical : styles.stateNeutral]}>
            <Text style={styles.stateText}>{bound ? 'PROJECT BOUND' : historical ? 'HISTORICAL UNBOUND' : 'NO PROJECT REQUIRED'}</Text>
          </View>
        </View>

        <View style={styles.factGrid}>
          <Fact label="Mode" value={conversation?.mode === 'code' ? 'Code' : 'Reason'} />
          <Fact label="Binding" value={binding ?? 'Unavailable'} />
          <Fact label="Project ID" value={projectId ?? 'Unavailable'} mono />
          <Fact label="Specification" value={conversation?.spec_id ?? 'Unavailable'} mono />
        </View>

        <View style={styles.boundary}>
          <Text style={styles.boundaryTitle}>Authority boundary</Text>
          <Text style={styles.boundaryCopy}>Project identity does not itself grant filesystem, provider, merge or deployment authority. Those controls remain behind the existing protected runtime contracts.</Text>
        </View>
      </View>

      <View style={styles.actionRow}>
        <View style={styles.actionCopy}>
          <Text style={styles.actionTitle}>Start governed Code work</Text>
          <Text style={styles.actionText}>Uses the existing protected Project selection/create flow when a canonical Project is required.</Text>
        </View>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Start Code work" onPress={onStartCodeWork} style={styles.actionButton}>
          <Text style={styles.actionButtonText}>Start Code work</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const serif = Platform.OS === 'web' ? 'Georgia, ui-serif, Charter, serif' : undefined;

const styles = StyleSheet.create({
  wrap: { flex: 1, minHeight: 0, width: '100%', maxWidth: 980, alignSelf: 'center', paddingHorizontal: 30, paddingTop: 34, paddingBottom: 30 },
  intro: { maxWidth: 700, marginBottom: 24 },
  kicker: { color: palette.olive700, fontSize: 9, fontWeight: '800', letterSpacing: 1.05, textTransform: 'uppercase', marginBottom: 7 },
  title: { color: palette.charcoal950, fontSize: 30, lineHeight: 35, fontWeight: '500', letterSpacing: -0.9, fontFamily: serif },
  copy: { color: palette.charcoal600, fontSize: 12, lineHeight: 19, marginTop: 8, maxWidth: 660 },
  card: { borderRadius: 22, padding: 22, backgroundColor: 'rgba(245,238,223,0.88)', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, shadowColor: '#5B4C36', shadowOpacity: 0.065, shadowRadius: 18, shadowOffset: { width: 0, height: 8 } },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: 18, marginBottom: 22 },
  cardKicker: { color: palette.charcoal450, fontSize: 8, fontWeight: '800', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 4 },
  cardTitle: { color: palette.charcoal950, fontSize: 18, lineHeight: 23, fontWeight: '700', maxWidth: 620 },
  statePill: { minHeight: 28, maxWidth: 190, paddingHorizontal: 10, borderRadius: 999, alignItems: 'center', justifyContent: 'center' },
  stateBound: { backgroundColor: palette.olive200 },
  stateHistorical: { backgroundColor: palette.rust100 },
  stateNeutral: { backgroundColor: palette.cream200 },
  stateText: { color: palette.charcoal800, fontSize: 8, fontWeight: '800', letterSpacing: 0.55 },
  factGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  fact: { minWidth: 190, flexGrow: 1, flexBasis: 220, padding: 14, borderRadius: 15, backgroundColor: palette.ivory50, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  factLabel: { color: palette.charcoal450, fontSize: 8, lineHeight: 11, textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 5 },
  factValue: { color: palette.charcoal800, fontSize: 11, lineHeight: 16, fontWeight: '600' },
  mono: { fontFamily: Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : undefined, fontWeight: '500' },
  boundary: { marginTop: 18, paddingTop: 17, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border },
  boundaryTitle: { color: palette.charcoal950, fontSize: 11, fontWeight: '800', marginBottom: 5 },
  boundaryCopy: { color: palette.charcoal600, fontSize: 10, lineHeight: 16, maxWidth: 720 },
  actionRow: { marginTop: 16, minHeight: 82, borderRadius: 18, paddingHorizontal: 18, paddingVertical: 15, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 18, backgroundColor: palette.teal100, borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(0,132,135,0.18)' },
  actionCopy: { flex: 1, minWidth: 0 },
  actionTitle: { color: palette.teal700, fontSize: 12, fontWeight: '800', marginBottom: 4 },
  actionText: { color: palette.charcoal600, fontSize: 10, lineHeight: 15 },
  actionButton: { minHeight: 44, paddingHorizontal: 16, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust600 },
  actionButtonText: { color: palette.ivory50, fontSize: 9, fontWeight: '800' },
});
