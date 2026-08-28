import React from 'react';
import { Platform, ScrollView, StyleSheet, Text, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import { api, type WorkSpecificationDto } from '../lib/api';
import { palette } from '../theme';

function Section({ label, items }: { label: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <View style={styles.section}>
      <Text style={styles.sectionLabel}>{label}</Text>
      {items.map((item, index) => (
        <Text selectable key={`${label}-${index}`} style={styles.item}>• {item}</Text>
      ))}
    </View>
  );
}

function TechnicalDetails({ specification, error }: { specification: WorkSpecificationDto; error: string | null }) {
  const [open, setOpen] = React.useState(false);
  return (
    <View style={styles.technicalWrap}>
      <TouchableOpacity
        accessibilityRole="button"
        accessibilityLabel={open ? 'Hide technical details' : 'Show technical details'}
        accessibilityState={{ expanded: open }}
        onPress={() => setOpen((value) => !value)}
        style={styles.technicalToggle}
      >
        <Text style={styles.technicalToggleText}>{open ? 'Hide technical details' : 'Technical details'}</Text>
        <Text style={styles.technicalChevron}>{open ? '⌃' : '⌄'}</Text>
      </TouchableOpacity>
      {open ? (
        <View style={styles.technicalBody}>
          <Text selectable style={styles.technicalLine}>System object: Work Specification</Text>
          <Text selectable style={styles.technicalLine}>Revision: {specification.revision}</Text>
          <Text selectable style={styles.technicalLine}>Status: {specification.status}</Text>
          <Text selectable style={styles.technicalLine}>Confidence: {Math.round(specification.confidence * 100)}%</Text>
          {error ? <Text selectable style={styles.technicalLine}>System message: {error}</Text> : null}
        </View>
      ) : null}
    </View>
  );
}

export function WorkSpecificationStatus({
  specification,
  busy,
  error,
  canDraft,
  onDraft,
  onApprove,
  reducedGraphics = false,
}: {
  specification: WorkSpecificationDto | null;
  busy: boolean;
  error: string | null;
  canDraft: boolean;
  onDraft(): void;
  onApprove(): void;
  reducedGraphics?: boolean;
}) {
  const { width, height } = useWindowDimensions();
  const compact = width < 760;
  const compactBodyMaxHeight = Math.max(220, Math.min(380, height * 0.42));
  const [expanded, setExpanded] = React.useState(false);
  const [conversationStatus, setConversationStatus] = React.useState<string | null>(null);
  const [resumeBusy, setResumeBusy] = React.useState(false);
  const [resumeError, setResumeError] = React.useState<string | null>(null);

  React.useEffect(() => { setExpanded(false); }, [specification?.id, specification?.status]);

  React.useEffect(() => {
    if (!specification || specification.status !== 'APPROVED') {
      setConversationStatus(null);
      setResumeError(null);
      return;
    }

    let cancelled = false;
    void api.getConversation(specification.conversation_id).then((conversation) => {
      if (!cancelled) setConversationStatus(conversation.status);
    }).catch(() => {
      if (!cancelled) setConversationStatus(null);
    });
    return () => { cancelled = true; };
  }, [specification?.conversation_id, specification?.id, specification?.status]);

  if (!specification && !canDraft && !error) return null;

  const approved = specification?.status === 'APPROVED';
  const resumable = approved && conversationStatus === 'SPEC_AMENDMENT';
  const working = busy || resumeBusy;
  void reducedGraphics;

  const resumeApprovedScope = async () => {
    if (!specification || !resumable || working) return;
    setResumeBusy(true);
    setResumeError(null);
    try {
      const conversation = await api.resumeApprovedScope(specification.conversation_id);
      setConversationStatus(conversation.status);
      if (Platform.OS === 'web' && typeof globalThis.location?.reload === 'function') {
        globalThis.location.reload();
      }
    } catch (caught) {
      setResumeError(caught instanceof Error ? caught.message : 'Approved work could not be continued.');
    } finally {
      setResumeBusy(false);
    }
  };

  const specificationBody = specification ? (
    <>
      <View style={styles.section}>
        <Text style={styles.sectionLabel}>WHAT YOU WANT</Text>
        <Text selectable style={styles.objective}>{specification.objective}</Text>
      </View>
      <Section label="WHAT SUCCESS LOOKS LIKE" items={specification.acceptance_criteria} />
      <Section label="IMPORTANT LIMITS" items={specification.constraints} />
      <Section label="QUESTIONS TO RESOLVE" items={specification.open_questions} />
      <Section label="THINGS TO WATCH" items={specification.risks} />
      <TechnicalDetails specification={specification} error={error ?? resumeError} />
    </>
  ) : null;

  const stateLabel = !specification
    ? 'Build plan not created'
    : approved
      ? 'Plan approved'
      : 'Ready for your review';

  return (
    <View style={[styles.wrap, compact && styles.wrapCompact]} accessibilityLabel="Build plan">
      <View pointerEvents="none" style={styles.softGlow} />
      <View style={[styles.kickerRow, compact && styles.kickerRowCompact]}>
        <View style={[styles.statusPill, approved && styles.statusPillApproved]}>
          <View style={[styles.statusDot, approved && styles.statusDotApproved]} />
          <Text style={[styles.status, approved && styles.statusApproved]}>{stateLabel}</Text>
        </View>
        {specification ? <Text style={styles.revision}>Version {specification.revision}</Text> : null}
      </View>

      <View style={[styles.header, compact && styles.headerCompact]}>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityLabel={specification ? (expanded ? 'Hide build plan details' : 'Show build plan details') : 'Build plan not created'}
          accessibilityState={{ expanded: specification ? expanded : undefined }}
          disabled={!specification}
          onPress={() => specification && setExpanded((value) => !value)}
          style={styles.identity}
        >
          <View style={styles.identityCopy}>
            <Text numberOfLines={compact ? 2 : 2} style={[styles.title, compact && styles.titleCompact]}>
              {specification ? specification.title : 'Create a clear plan before building'}
            </Text>
            {(!compact || !expanded) ? (
              <Text numberOfLines={compact ? 2 : 2} style={[styles.subtitle, compact && styles.subtitleCompact]}>
                {specification ? specification.objective : 'Parallax will summarize what you want, what success looks like, and important limits before making changes.'}
              </Text>
            ) : null}
          </View>
        </TouchableOpacity>

        <View style={[styles.actions, compact && styles.actionsCompact]}>
          {resumable && (
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Continue approved work"
              accessibilityHint="Return to the work in the plan you already approved"
              disabled={working}
              onPress={() => void resumeApprovedScope()}
              style={[styles.actionButton, styles.resumeButton, compact && styles.actionButtonCompact]}
            >
              <Text style={styles.resumeText}>{resumeBusy ? 'Continuing…' : 'Continue approved work'}</Text>
            </TouchableOpacity>
          )}
          {specification?.status === 'DRAFT' && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel="Approve build plan" disabled={working} onPress={onApprove} style={[styles.actionButton, styles.approveButton, compact && styles.actionButtonCompact]}>
              <Text style={styles.approveText}>{busy ? 'Approving…' : 'Approve plan'}</Text>
            </TouchableOpacity>
          )}
          {canDraft && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel={specification ? 'Update build plan' : 'Create build plan'} disabled={working} onPress={onDraft} style={[styles.actionButton, compact && styles.actionButtonCompact]}>
              <Text style={styles.actionText}>{busy ? 'Working…' : specification ? 'Update plan' : 'Create plan'}</Text>
            </TouchableOpacity>
          )}
          {specification && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel={expanded ? 'Hide build plan details' : 'Show build plan details'} onPress={() => setExpanded((value) => !value)} style={[styles.disclosure, compact && styles.disclosureCompact]}>
              <Text style={styles.disclosureText}>{expanded ? '−' : '+'}</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {resumable ? (
        <View style={styles.resumeNotice}>
          <Text style={styles.resumeNoticeTitle}>Your newer request is different from this approved plan.</Text>
          <Text style={styles.resumeHint}>Continue only if you want Parallax to return to the work you already approved.</Text>
        </View>
      ) : null}
      {error ? <Text style={styles.error}>Parallax couldn’t update the build plan. Your current plan is still here.</Text> : null}
      {resumeError ? <Text style={styles.error}>Parallax couldn’t continue the approved work. Your plan has not changed.</Text> : null}

      {specification && expanded ? (
        compact ? (
          <ScrollView
            accessibilityLabel="Build plan details"
            nestedScrollEnabled
            showsVerticalScrollIndicator
            style={[styles.bodyScroll, { maxHeight: compactBodyMaxHeight }]}
            contentContainerStyle={styles.bodyScrollContent}
          >
            {specificationBody}
          </ScrollView>
        ) : (
          <View style={styles.body}>{specificationBody}</View>
        )
      ) : null}
    </View>
  );
}

const mono = Platform.OS === 'web' ? 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace' : undefined;

const styles = StyleSheet.create({
  wrap: {
    position: 'relative',
    marginLeft: 28,
    marginRight: 40,
    marginTop: 18,
    paddingTop: 17,
    paddingRight: 18,
    paddingBottom: 18,
    paddingLeft: 18,
    borderRadius: 24,
    borderWidth: 0,
    backgroundColor: 'rgba(245, 238, 223, 0.90)',
    shadowColor: '#564B38',
    shadowOpacity: 0.12,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 12 },
    overflow: 'hidden',
  },
  wrapCompact: { marginLeft: 10, marginRight: 10, marginTop: 8, padding: 14, borderRadius: 19, backgroundColor: 'rgba(245, 238, 223, 0.92)', shadowOpacity: 0.08, shadowRadius: 18 },
  softGlow: { position: 'absolute', width: 180, height: 90, borderRadius: 90, right: -40, top: -36, backgroundColor: 'rgba(0,132,135,0.05)' },
  kickerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  kickerRowCompact: { marginBottom: 8 },
  statusPill: { minHeight: 32, flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 11, borderRadius: 999, backgroundColor: 'rgba(196,74,27,0.10)' },
  statusPillApproved: { backgroundColor: 'rgba(102,117,58,0.11)' },
  statusDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: palette.rust600 },
  statusDotApproved: { backgroundColor: palette.olive700 },
  status: { color: palette.rust700, fontSize: 12, lineHeight: 16, fontWeight: '800' },
  statusApproved: { color: palette.olive700 },
  revision: { color: palette.muted, fontSize: 12, lineHeight: 16 },
  header: { minHeight: 66, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 20 },
  headerCompact: { minHeight: 0, flexDirection: 'column', alignItems: 'stretch', gap: 12 },
  identity: { flex: 1, minWidth: 0, minHeight: 44, justifyContent: 'center' },
  identityCopy: { flex: 1, minWidth: 0 },
  title: { color: palette.text, fontSize: 21, lineHeight: 27, fontWeight: '600', letterSpacing: -0.48 },
  titleCompact: { fontSize: 19, lineHeight: 25, letterSpacing: -0.3 },
  subtitle: { color: palette.textSecondary, fontSize: 14, lineHeight: 21, marginTop: 5, maxWidth: 680 },
  subtitleCompact: { fontSize: 14, lineHeight: 21, marginTop: 4 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  actionsCompact: { width: '100%', justifyContent: 'flex-end', gap: 8, flexWrap: 'wrap' },
  actionButton: { minHeight: 44, paddingHorizontal: 14, alignItems: 'center', justifyContent: 'center', borderRadius: 14, borderWidth: 0, backgroundColor: 'rgba(196,74,27,0.08)' },
  actionButtonCompact: { minHeight: 46, paddingHorizontal: 14, borderRadius: 14 },
  resumeButton: { backgroundColor: 'rgba(0,132,135,0.09)' },
  approveButton: { backgroundColor: 'rgba(102,117,58,0.11)' },
  actionText: { color: palette.teal700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  resumeText: { color: palette.teal700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  approveText: { color: palette.olive700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  disclosure: { width: 44, height: 44, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.35)' },
  disclosureCompact: { width: 46, height: 46 },
  disclosureText: { color: palette.textSoft, fontSize: 22, lineHeight: 24 },
  resumeNotice: { marginTop: 10, padding: 13, borderRadius: 14, backgroundColor: palette.teal100 },
  resumeNoticeTitle: { color: palette.charcoal950, fontSize: 14, lineHeight: 20, fontWeight: '800' },
  resumeHint: { color: palette.textSecondary, fontSize: 13, lineHeight: 19, marginTop: 3, maxWidth: 720 },
  error: { color: palette.danger, fontSize: 13, lineHeight: 19, paddingTop: 9 },
  body: { marginTop: 16, paddingTop: 18, paddingRight: 10, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(102,117,58,0.16)' },
  bodyScroll: { marginTop: 12, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(102,117,58,0.16)' },
  bodyScrollContent: { paddingTop: 14, paddingRight: 2, paddingBottom: 10 },
  section: { marginBottom: 20 },
  sectionLabel: { color: palette.olive700, fontSize: 12, lineHeight: 16, fontWeight: '800', letterSpacing: 0.7, marginBottom: 8 },
  objective: { color: palette.text, fontSize: 16, lineHeight: 25, maxWidth: 740 },
  item: { color: palette.textSecondary, fontSize: 15, lineHeight: 24, marginBottom: 5, maxWidth: 740 },
  technicalWrap: { marginTop: 4, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border, paddingTop: 6 },
  technicalToggle: { minHeight: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 },
  technicalToggleText: { color: palette.teal700, fontSize: 13, lineHeight: 18, fontWeight: '800' },
  technicalChevron: { color: palette.teal700, fontSize: 18, lineHeight: 20, fontWeight: '800' },
  technicalBody: { padding: 12, borderRadius: 13, backgroundColor: palette.cream150 },
  technicalLine: { color: palette.charcoal800, fontSize: 12, lineHeight: 18, fontFamily: mono, marginBottom: 3 },
});
