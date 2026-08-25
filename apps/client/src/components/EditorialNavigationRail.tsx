import React from 'react';
import { Platform, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { ConversationDto, ProjectBindingStatus } from '../lib/api';
import { palette } from '../theme';
import { ParallaxLogo } from './ParallaxLogo';

export type EditorialShellView = 'conversation' | 'observability' | 'projects';

type Props = {
  width: number;
  activeView: EditorialShellView;
  conversations: ConversationDto[];
  conversationId: string | null;
  observabilityAvailable: boolean;
  apiOnline: boolean;
  activeSpecId: string | null;
  projectId: string | null;
  projectBindingStatus: ProjectBindingStatus | null;
  onSelectView(view: EditorialShellView): void;
  onNewConversation(): void;
  onOpenConversation(conversation: ConversationDto): void;
};

type Destination = {
  id: EditorialShellView;
  label: string;
  glyph: string;
  supporting: string;
};

const DESTINATIONS: Destination[] = [
  { id: 'conversation', label: 'Conversations', glyph: 'C', supporting: 'Create and reason' },
  { id: 'observability', label: 'Observability', glyph: 'O', supporting: 'Inspect active execution' },
  { id: 'projects', label: 'Projects', glyph: 'P', supporting: 'Canonical project context' },
];

function shortIdentity(value: string | null): string {
  if (!value) return 'No Project bound';
  return value.length <= 18 ? value : `${value.slice(0, 8)}…${value.slice(-6)}`;
}

export function EditorialNavigationRail({
  width,
  activeView,
  conversations,
  conversationId,
  observabilityAvailable,
  apiOnline,
  activeSpecId,
  projectId,
  projectBindingStatus,
  onSelectView,
  onNewConversation,
  onOpenConversation,
}: Props) {
  return (
    <View style={[styles.rail, { width }]} testID="editorial-navigation-rail">
      <View style={styles.brandRow}>
        <View style={styles.logoWell}><ParallaxLogo size={52} /></View>
        <View style={styles.brandCopy}>
          <Text style={styles.brand}>Parallax</Text>
          <Text style={styles.brandSub}>Build with perspective.</Text>
        </View>
      </View>

      <Text style={styles.sectionLabel}>Workspace</Text>
      <View style={styles.navList}>
        {DESTINATIONS.map((item) => {
          const disabled = item.id === 'observability' && !observabilityAvailable;
          const active = activeView === item.id;
          return (
            <TouchableOpacity
              key={item.id}
              accessibilityRole="button"
              accessibilityLabel={item.label}
              accessibilityHint={disabled ? 'Requires an active Code engineering run' : item.supporting}
              accessibilityState={{ disabled, selected: active }}
              disabled={disabled}
              onPress={() => onSelectView(item.id)}
              style={[styles.navRow, active && styles.navRowActive, disabled && styles.navRowDisabled]}
            >
              <View style={[styles.navGlyph, active && styles.navGlyphActive]}>
                <Text style={[styles.navGlyphText, active && styles.navGlyphTextActive]}>{item.glyph}</Text>
              </View>
              <View style={styles.navCopy}>
                <Text style={[styles.navText, active && styles.navTextActive]}>{item.label}</Text>
                <Text numberOfLines={1} style={[styles.navSupporting, active && styles.navSupportingActive]}>
                  {disabled ? 'No active Code run' : item.supporting}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>

      <View style={styles.divider} />
      <View style={styles.recentHeading}>
        <Text style={styles.sectionLabel}>Recent conversations</Text>
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="New conversation" onPress={onNewConversation} style={styles.newButton}>
          <Text style={styles.newButtonText}>＋</Text>
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.recentList} contentContainerStyle={styles.recentContent} showsVerticalScrollIndicator={false}>
        {conversations.slice(0, 8).map((conversation) => {
          const active = conversation.id === conversationId;
          return (
            <TouchableOpacity
              key={conversation.id}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              onPress={() => onOpenConversation(conversation)}
              style={[styles.recentRow, active && styles.recentRowActive]}
            >
              <Text numberOfLines={2} style={styles.recentTitle}>{conversation.title}</Text>
              <View style={styles.recentMetaRow}>
                <Text style={styles.recentMeta}>{conversation.mode}</Text>
                {conversation.project_binding_status === 'PROJECT_BOUND' ? <Text style={styles.recentMeta}>project</Text> : null}
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      <View style={styles.railFooter}>
        <View style={styles.statusRow}>
          <View style={[styles.statusDot, !apiOnline && styles.statusDotUnavailable]} />
          <View style={styles.footerCopy}>
            <Text style={styles.footerPrimary}>{apiOnline ? 'Workspace available' : 'Workspace unavailable'}</Text>
            <Text numberOfLines={1} style={styles.footerSecondary}>{activeSpecId ?? 'No active specification'}</Text>
          </View>
        </View>
        <View style={styles.projectFact}>
          <Text style={styles.projectFactLabel}>Project</Text>
          <Text numberOfLines={1} style={styles.projectFactValue}>
            {projectBindingStatus === 'HISTORICAL_UNBOUND' ? 'Historical · unbound' : shortIdentity(projectId)}
          </Text>
        </View>
      </View>
    </View>
  );
}

const serif = Platform.OS === 'web' ? 'Georgia, ui-serif, Charter, serif' : undefined;

const styles = StyleSheet.create({
  rail: {
    backgroundColor: palette.forest950,
    paddingHorizontal: 18,
    paddingTop: 22,
    paddingBottom: 18,
    overflow: 'hidden',
    borderRightWidth: StyleSheet.hairlineWidth,
    borderRightColor: 'rgba(216,220,192,0.14)',
    shadowColor: '#10180E',
    shadowOpacity: 0.18,
    shadowRadius: 24,
    shadowOffset: { width: 7, height: 0 },
  },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 34 },
  logoWell: { width: 58, height: 58, alignItems: 'center', justifyContent: 'center' },
  brandCopy: { flex: 1, minWidth: 0 },
  brand: { color: palette.ivory50, fontSize: 24, lineHeight: 28, fontWeight: '600', letterSpacing: -0.7, fontFamily: serif },
  brandSub: { color: palette.olive200, fontSize: 9, lineHeight: 13, marginTop: 3, letterSpacing: 0.28 },
  sectionLabel: { color: '#AEB79A', fontSize: 8, fontWeight: '800', letterSpacing: 1.25, textTransform: 'uppercase' },
  navList: { gap: 6, marginTop: 10 },
  navRow: { minHeight: 52, borderRadius: 14, paddingHorizontal: 10, paddingVertical: 7, flexDirection: 'row', alignItems: 'center', gap: 10 },
  navRowActive: { backgroundColor: palette.rust600, shadowColor: '#10180E', shadowOpacity: 0.16, shadowRadius: 10, shadowOffset: { width: 0, height: 5 } },
  navRowDisabled: { opacity: 0.52 },
  navGlyph: { width: 30, height: 30, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(216,220,192,0.09)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(216,220,192,0.16)' },
  navGlyphActive: { backgroundColor: 'rgba(251,247,238,0.16)', borderColor: 'rgba(251,247,238,0.24)' },
  navGlyphText: { color: palette.olive200, fontSize: 10, fontWeight: '800' },
  navGlyphTextActive: { color: palette.ivory50 },
  navCopy: { flex: 1, minWidth: 0 },
  navText: { color: '#EEF0E2', fontSize: 12, lineHeight: 16, fontWeight: '700' },
  navTextActive: { color: palette.ivory50 },
  navSupporting: { color: '#9FA98D', fontSize: 8, lineHeight: 11, marginTop: 2 },
  navSupportingActive: { color: 'rgba(251,247,238,0.76)' },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: 'rgba(216,220,192,0.14)', marginTop: 22, marginBottom: 18 },
  recentHeading: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 2, marginBottom: 10 },
  newButton: { width: 32, height: 32, borderRadius: 11, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(21,153,154,0.14)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(21,153,154,0.24)' },
  newButtonText: { color: '#BFE4DD', fontSize: 16, lineHeight: 18, fontWeight: '600' },
  recentList: { flex: 1, minHeight: 90 },
  recentContent: { paddingBottom: 10 },
  recentRow: { borderRadius: 12, paddingHorizontal: 11, paddingVertical: 9, marginBottom: 4 },
  recentRowActive: { backgroundColor: 'rgba(196,74,27,0.18)' },
  recentTitle: { color: '#F3EEE1', fontSize: 11, lineHeight: 15 },
  recentMetaRow: { flexDirection: 'row', gap: 7, marginTop: 4 },
  recentMeta: { color: '#929D82', fontSize: 7, lineHeight: 10, textTransform: 'uppercase', letterSpacing: 0.55 },
  railFooter: { paddingTop: 14, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(216,220,192,0.14)', gap: 12 },
  statusRow: { minHeight: 38, flexDirection: 'row', alignItems: 'center', gap: 9 },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: palette.olive500 },
  statusDotUnavailable: { backgroundColor: palette.warning },
  footerCopy: { flex: 1, minWidth: 0 },
  footerPrimary: { color: '#EEF0E2', fontSize: 9, fontWeight: '700' },
  footerSecondary: { color: '#929D82', fontSize: 8, marginTop: 3 },
  projectFact: { borderRadius: 12, paddingHorizontal: 11, paddingVertical: 9, backgroundColor: 'rgba(216,220,192,0.07)', borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(216,220,192,0.12)' },
  projectFactLabel: { color: '#929D82', fontSize: 7, textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 3 },
  projectFactValue: { color: '#E2E5D4', fontSize: 9, lineHeight: 12, fontFamily: Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : undefined },
});
