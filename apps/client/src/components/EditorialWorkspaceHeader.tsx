import React from 'react';
import { Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { ProjectBindingStatus } from '../lib/api';
import { palette } from '../theme';
import { ParallaxLogo } from './ParallaxLogo';

type Props = {
  compact: boolean;
  mode: 'reason' | 'code';
  eyebrow: string;
  title: string;
  subtitle: string;
  projectId: string | null;
  projectBindingStatus: ProjectBindingStatus | null;
  onModeChange(mode: 'reason' | 'code'): void;
  onNewConversation(): void;
};

function projectLabel(projectId: string | null, binding: ProjectBindingStatus | null): string | null {
  if (binding !== 'PROJECT_BOUND' || !projectId) return null;
  return 'Project selected';
}

export function EditorialWorkspaceHeader({
  compact,
  mode,
  eyebrow,
  title,
  subtitle,
  projectId,
  projectBindingStatus,
  onModeChange,
  onNewConversation,
}: Props) {
  const project = projectLabel(projectId, projectBindingStatus);
  return (
    <View style={[styles.header, compact && styles.headerCompact]} testID="editorial-workspace-header">
      <View style={styles.identityRow}>
        {compact ? <ParallaxLogo size={40} /> : null}
        <View style={styles.copy}>
          <Text style={styles.eyebrow}>{eyebrow}</Text>
          <Text style={[styles.title, compact && styles.titleCompact]}>{title}</Text>
          <Text numberOfLines={compact ? 2 : 1} style={styles.subtitle}>{subtitle}</Text>
          {project ? (
            <View style={styles.projectPill}>
              <View style={styles.projectDot} />
              <Text numberOfLines={1} style={styles.projectText}>{project}</Text>
            </View>
          ) : null}
        </View>
      </View>

      <View style={[styles.controls, compact && styles.controlsCompact]}>
        {!compact ? (
          <TouchableOpacity accessibilityRole="button" accessibilityLabel="New conversation" onPress={onNewConversation} style={styles.newButton}>
            <Text style={styles.newButtonText}>New conversation</Text>
            <Text style={styles.newButtonGlyph}>＋</Text>
          </TouchableOpacity>
        ) : null}
        <View style={styles.modeSwitch} accessibilityLabel="Choose what you want to do">
          {(['reason', 'code'] as const).map((item) => {
            const label = item === 'reason' ? 'Ask' : 'Build';
            return (
              <TouchableOpacity
                key={item}
                accessibilityRole="button"
                accessibilityLabel={label}
                accessibilityState={{ selected: mode === item }}
                onPress={() => onModeChange(item)}
                style={[styles.modeButton, mode === item && styles.modeButtonActive]}
              >
                <Text style={[styles.modeText, mode === item && styles.modeTextActive]}>{label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>
    </View>
  );
}

const serif = Platform.OS === 'web' ? 'Georgia, ui-serif, Charter, serif' : undefined;

const styles = StyleSheet.create({
  header: {
    minHeight: 146,
    paddingHorizontal: 34,
    paddingTop: 24,
    paddingBottom: 20,
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 24,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: palette.border,
    backgroundColor: 'rgba(251,247,238,0.78)',
  },
  headerCompact: { minHeight: 150, paddingHorizontal: 16, paddingTop: 16, paddingBottom: 14, gap: 12, flexDirection: 'column' },
  identityRow: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  eyebrow: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.8, textTransform: 'uppercase', marginBottom: 5 },
  title: { color: palette.charcoal950, fontSize: 40, lineHeight: 43, fontWeight: '500', letterSpacing: -1.35, fontFamily: serif },
  titleCompact: { fontSize: 27, lineHeight: 31, letterSpacing: -0.8 },
  subtitle: { color: palette.charcoal600, fontSize: 15, lineHeight: 22, marginTop: 6, maxWidth: 690 },
  projectPill: { alignSelf: 'flex-start', maxWidth: 330, minHeight: 32, marginTop: 10, paddingHorizontal: 11, borderRadius: 999, flexDirection: 'row', alignItems: 'center', gap: 7, backgroundColor: palette.cream100, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  projectDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: palette.olive500 },
  projectText: { flexShrink: 1, color: palette.charcoal600, fontSize: 12, lineHeight: 16, fontWeight: '700' },
  controls: { flexShrink: 0, flexDirection: 'row', alignItems: 'center', gap: 10 },
  controlsCompact: { alignSelf: 'stretch', justifyContent: 'flex-end' },
  newButton: { minHeight: 44, paddingHorizontal: 16, borderRadius: 14, flexDirection: 'row', alignItems: 'center', gap: 9, backgroundColor: palette.rust600, shadowColor: '#704026', shadowOpacity: 0.15, shadowRadius: 12, shadowOffset: { width: 0, height: 5 } },
  newButtonText: { color: palette.ivory50, fontSize: 14, lineHeight: 19, fontWeight: '800' },
  newButtonGlyph: { color: palette.ivory50, fontSize: 17, lineHeight: 20 },
  modeSwitch: { minHeight: 50, flexDirection: 'row', alignItems: 'center', borderRadius: 14, padding: 3, backgroundColor: palette.cream200, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border },
  modeButton: { minHeight: 44, minWidth: 68, paddingHorizontal: 13, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  modeButtonActive: { backgroundColor: palette.teal700, shadowColor: '#1D5B5B', shadowOpacity: 0.12, shadowRadius: 8, shadowOffset: { width: 0, height: 3 } },
  modeText: { color: palette.charcoal600, fontSize: 14, lineHeight: 19, fontWeight: '800' },
  modeTextActive: { color: palette.ivory50 },
});
