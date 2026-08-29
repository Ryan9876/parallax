import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto, ResponsePhase, WorkSpecificationDto } from '../../lib/api';
import {
  getEngineeringRunFailure,
  subscribeEngineeringRunFailures,
} from '../../lib/engineeringRunEvents';
import { getWorkflowGuidance, type WorkflowActionIntent } from '../../lib/workflowGuidance';
import { palette } from '../../theme';

type Props = {
  mode: 'reason' | 'code';
  phase: ResponsePhase | string;
  conversationStatus?: string | null;
  specification: WorkSpecificationDto | null;
  run: EngineeringRunDto | null;
  canDraft: boolean;
  hasApprovedSpecification: boolean;
  busy: boolean;
  error: string | null;
  onCapture(): void;
  onReviewSpecification(): void;
  onOpenBuild(): void;
  onContinueWork(): void;
};

function useEngineeringRunFailure(conversationId: string | null | undefined) {
  const subscribe = React.useCallback((listener: () => void) => subscribeEngineeringRunFailures(listener), []);
  const getSnapshot = React.useCallback(() => getEngineeringRunFailure(conversationId ?? null), [conversationId]);
  return React.useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

function plainError(error: string | null): string | null {
  if (!error) return null;
  const normalized = error.toLowerCase();
  if (normalized.includes("couldn't prepare this project") || normalized.includes('couldn’t prepare this project')) {
    return 'Parallax couldn’t prepare this project for the next step yet. Your saved work is still here. Try again.';
  }
  return 'Parallax couldn’t continue that step. Your saved work is still here. Try again.';
}

function TechnicalDetails({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);
  return (
    <View style={styles.technicalDisclosure}>
      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide technical details' : 'Show technical details'}
        accessibilityState={{ expanded: open }}
        onPress={() => setOpen((current) => !current)}
        style={styles.technicalToggle}
      >
        <Text style={styles.technicalToggleText}>{open ? 'Hide technical details' : 'Technical details'}</Text>
        <Text aria-hidden style={styles.technicalChevron}>{open ? '⌃' : '⌄'}</Text>
      </TouchableOpacity>
      {open ? <View style={styles.technicalBody}>{children}</View> : null}
    </View>
  );
}

export function MobileGuidedContextCard({
  mode,
  phase,
  conversationStatus,
  specification,
  run,
  canDraft,
  hasApprovedSpecification,
  busy,
  error,
  onCapture,
  onReviewSpecification,
  onOpenBuild,
  onContinueWork,
}: Props) {
  const runFailure = useEngineeringRunFailure(run?.conversation_id);
  const effectiveError = runFailure?.message ?? error;
  const guidance = getWorkflowGuidance({
    mode,
    phase,
    conversationStatus,
    specification,
    run,
    canDraft,
    hasApprovedSpecification,
    runError: runFailure?.message ?? (run ? error : null),
  });

  if (mode !== 'code') return null;

  const actionFor = (intent: WorkflowActionIntent): (() => void) | null => {
    if (intent === 'create-plan') return onCapture;
    if (intent === 'review-plan') return onReviewSpecification;
    if (intent === 'view-progress' || intent === 'open-activity') return onOpenBuild;
    if (intent === 'continue-work') return onContinueWork;
    return null;
  };
  const primaryAction = actionFor(guidance.actionIntent);

  return (
    <View
      accessibilityLabel={`Next step: ${guidance.title}`}
      style={styles.contextCard}
      testID="mobile-context-card"
    >
      <Text style={styles.eyebrow}>{guidance.eyebrow}</Text>
      <Text accessibilityLiveRegion="polite" style={styles.title}>{guidance.title}</Text>
      <Text style={styles.copy}>{guidance.description}</Text>
      {plainError(effectiveError) ? <Text accessibilityLiveRegion="polite" style={styles.error}>{plainError(effectiveError)}</Text> : null}
      {guidance.actionLabel && primaryAction ? (
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityLabel={guidance.actionLabel}
          disabled={busy}
          onPress={primaryAction}
          style={[styles.primaryButton, busy && styles.primaryButtonDisabled]}
        >
          <Text style={styles.primaryButtonText}>{busy ? 'Please wait…' : guidance.actionLabel}</Text>
        </TouchableOpacity>
      ) : null}
      {specification && specification.status !== 'DRAFT' && guidance.actionIntent !== 'review-plan' ? (
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Review build plan" onPress={onReviewSpecification} style={styles.textButton}>
          <Text style={styles.textButtonText}>Review build plan</Text>
        </TouchableOpacity>
      ) : null}
      {effectiveError || run?.last_failure_code ? (
        <TechnicalDetails>
          {effectiveError ? <Text selectable style={styles.technicalLine}>System message: {effectiveError}</Text> : null}
          {run?.last_failure_code ? <Text selectable style={styles.technicalLine}>Issue code: {run.last_failure_code}</Text> : null}
        </TechnicalDetails>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  contextCard: {
    borderRadius: 20,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.borderStrong,
    backgroundColor: palette.cream100,
    padding: 17,
    marginBottom: 18,
  },
  eyebrow: {
    color: palette.olive700,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '800',
    letterSpacing: 1.05,
  },
  title: {
    color: palette.charcoal950,
    fontSize: 20,
    lineHeight: 25,
    fontWeight: '800',
    marginTop: 6,
  },
  copy: {
    color: palette.charcoal600,
    fontSize: 16,
    lineHeight: 23,
    marginTop: 7,
  },
  error: {
    color: palette.danger,
    fontSize: 15,
    lineHeight: 21,
    marginTop: 10,
  },
  primaryButton: {
    minHeight: 48,
    borderRadius: 14,
    paddingHorizontal: 16,
    paddingVertical: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: palette.teal700,
    marginTop: 14,
  },
  primaryButtonDisabled: { opacity: 0.55 },
  primaryButtonText: {
    color: palette.ivory50,
    fontSize: 15,
    fontWeight: '800',
  },
  textButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
  },
  textButtonText: {
    color: palette.teal700,
    fontSize: 14,
    fontWeight: '800',
  },
  technicalDisclosure: {
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: palette.border,
    marginTop: 12,
    paddingTop: 4,
  },
  technicalToggle: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  technicalToggleText: {
    color: palette.charcoal600,
    fontSize: 13,
    fontWeight: '700',
  },
  technicalChevron: { color: palette.charcoal450, fontSize: 14 },
  technicalBody: { paddingBottom: 4 },
  technicalLine: {
    color: palette.charcoal600,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 4,
  },
});
