import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { WorkflowGuidance } from '../lib/workflowGuidance';
import { palette } from '../theme';

type GuidedWorkflowCardProps = {
  guidance: WorkflowGuidance;
  busy?: boolean;
  onPrimaryAction?: (() => void) | null;
};

function toneStyle(guidance: WorkflowGuidance) {
  if (guidance.tone === 'attention') return styles.cardAttention;
  if (guidance.tone === 'ready') return styles.cardReady;
  if (guidance.tone === 'complete') return styles.cardComplete;
  if (guidance.tone === 'active') return styles.cardActive;
  return styles.cardNeutral;
}

export function GuidedWorkflowCard({ guidance, busy = false, onPrimaryAction = null }: GuidedWorkflowCardProps) {
  return (
    <View
      accessibilityLabel={`Next step: ${guidance.title}`}
      style={[styles.card, toneStyle(guidance)]}
      testID="guided-workflow-card"
    >
      <View style={styles.copy}>
        <Text style={styles.eyebrow}>{guidance.eyebrow}</Text>
        <Text accessibilityLiveRegion="polite" style={styles.title}>{guidance.title}</Text>
        <Text style={styles.description}>{guidance.description}</Text>
      </View>
      {guidance.actionLabel && onPrimaryAction ? (
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityLabel={guidance.actionLabel}
          disabled={busy}
          onPress={onPrimaryAction}
          style={[styles.action, busy && styles.actionDisabled]}
        >
          <Text style={styles.actionText}>{busy ? 'Please wait…' : guidance.actionLabel}</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    minHeight: 112,
    width: '100%',
    borderRadius: 22,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 22,
    paddingVertical: 18,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 18,
  },
  cardNeutral: {
    backgroundColor: palette.cream100,
    borderColor: palette.borderStrong,
  },
  cardActive: {
    backgroundColor: palette.teal100,
    borderColor: 'rgba(0, 132, 135, 0.34)',
  },
  cardReady: {
    backgroundColor: palette.cream150,
    borderColor: palette.borderStrong,
  },
  cardAttention: {
    backgroundColor: palette.rust100,
    borderColor: 'rgba(168, 59, 23, 0.34)',
  },
  cardComplete: {
    backgroundColor: palette.olive200,
    borderColor: palette.borderStrong,
  },
  copy: {
    flex: 1,
    minWidth: 0,
  },
  eyebrow: {
    color: palette.olive700,
    fontSize: 12,
    fontWeight: '800',
    letterSpacing: 1.1,
  },
  title: {
    color: palette.charcoal950,
    fontSize: 20,
    lineHeight: 25,
    fontWeight: '700',
    marginTop: 5,
  },
  description: {
    color: palette.charcoal600,
    fontSize: 15,
    lineHeight: 22,
    marginTop: 5,
    maxWidth: 680,
  },
  action: {
    minHeight: 44,
    minWidth: 132,
    paddingHorizontal: 18,
    paddingVertical: 12,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.teal700,
  },
  actionDisabled: {
    opacity: 0.55,
  },
  actionText: {
    color: palette.ivory50,
    fontSize: 14,
    fontWeight: '800',
  },
});
