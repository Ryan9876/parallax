import React from 'react';
import { StyleSheet, Text, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import type { WorkSpecificationDto } from '../lib/api';
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

export function WorkSpecificationStatus({
  specification,
  busy,
  error,
  canDraft,
  canResumeApprovedScope = false,
  onDraft,
  onApprove,
  onResumeApprovedScope,
  reducedGraphics = false,
}: {
  specification: WorkSpecificationDto | null;
  busy: boolean;
  error: string | null;
  canDraft: boolean;
  canResumeApprovedScope?: boolean;
  onDraft(): void;
  onApprove(): void;
  onResumeApprovedScope?(): void;
  reducedGraphics?: boolean;
}) {
  const { width } = useWindowDimensions();
  const compact = width < 760;
  const [expanded, setExpanded] = React.useState(false);

  React.useEffect(() => { setExpanded(false); }, [specification?.id]);

  if (!specification && !canDraft && !error) return null;

  const approved = specification?.status === 'APPROVED';
  const resumable = approved && canResumeApprovedScope && Boolean(onResumeApprovedScope);
  const statusLabel = specification ? `SPEC · ${specification.status}` : 'SPEC · NOT CAPTURED';
  void reducedGraphics;

  return (
    <View style={[styles.wrap, compact && styles.wrapCompact]} accessibilityLabel="Work specification">
      <View pointerEvents="none" style={styles.softGlow} />
      <View style={[styles.kickerRow, compact && styles.kickerRowCompact]}>
        <View style={[styles.statusPill, approved && styles.statusPillApproved]}>
          <View style={[styles.statusDot, approved && styles.statusDotApproved]} />
          <Text style={[styles.status, approved && styles.statusApproved]}>{statusLabel}</Text>
        </View>
        {specification ? <Text style={styles.revision}>REVISION {specification.revision}</Text> : null}
      </View>

      <View style={[styles.header, compact && styles.headerCompact]}>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityState={{ expanded }}
          disabled={!specification}
          onPress={() => specification && setExpanded((value) => !value)}
          style={styles.identity}
        >
          <View style={styles.identityCopy}>
            <Text numberOfLines={compact ? 1 : 2} style={[styles.title, compact && styles.titleCompact]}>
              {specification ? specification.title : 'Capture the implementation contract'}
            </Text>
            {(!compact || expanded) ? (
              <Text numberOfLines={compact ? 1 : 2} style={[styles.subtitle, compact && styles.subtitleCompact]}>
                {specification ? specification.objective : 'Turn the current objective into a durable specification before implementation.'}
              </Text>
            ) : null}
          </View>
        </TouchableOpacity>

        <View style={[styles.actions, compact && styles.actionsCompact]}>
          {resumable && (
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Resume approved scope"
              accessibilityHint="Return this conversation to its current approved work specification"
              disabled={busy}
              onPress={onResumeApprovedScope}
              style={[styles.actionButton, styles.resumeButton, compact && styles.actionButtonCompact]}
            >
              <Text style={styles.resumeText}>{busy ? 'WORKING…' : 'RESUME SCOPE'}</Text>
            </TouchableOpacity>
          )}
          {specification?.status === 'DRAFT' && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel="Approve work specification" disabled={busy} onPress={onApprove} style={[styles.actionButton, styles.approveButton, compact && styles.actionButtonCompact]}>
              <Text style={styles.approveText}>{busy ? 'WORKING…' : 'APPROVE'}</Text>
            </TouchableOpacity>
          )}
          {canDraft && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel={specification ? 'Refresh work specification draft' : 'Capture work specification'} disabled={busy} onPress={onDraft} style={[styles.actionButton, compact && styles.actionButtonCompact]}>
              <Text style={styles.actionText}>{busy ? 'DRAFTING…' : specification ? 'REFRESH DRAFT' : 'CAPTURE SPEC'}</Text>
            </TouchableOpacity>
          )}
          {specification && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel={expanded ? 'Collapse work specification' : 'Expand work specification'} onPress={() => setExpanded((value) => !value)} style={[styles.disclosure, compact && styles.disclosureCompact]}>
              <Text style={styles.disclosureText}>{expanded ? '−' : '+'}</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {resumable ? (
        <Text style={styles.resumeHint}>
          This conversation is paused at a specification amendment. Resume only if this approved scope is the contract you want Parallax to continue against.
        </Text>
      ) : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}

      {specification && expanded ? (
        <View style={[styles.body, compact && styles.bodyCompact]}>
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>OBJECTIVE</Text>
            <Text selectable style={styles.objective}>{specification.objective}</Text>
          </View>
          <Section label="ACCEPTANCE" items={specification.acceptance_criteria} />
          <Section label="CONSTRAINTS" items={specification.constraints} />
          <Section label="OPEN QUESTIONS" items={specification.open_questions} />
          <Section label="RISKS" items={specification.risks} />
          <Text style={styles.meta}>Confidence {Math.round(specification.confidence * 100)}% · {specification.status === 'APPROVED' ? 'operator approved' : 'operator approval required'}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'relative',
    marginLeft: 28,
    marginRight: 40,
    marginTop: 18,
    paddingTop: 16,
    paddingRight: 18,
    paddingBottom: 17,
    paddingLeft: 18,
    borderRadius: 24,
    borderWidth: 0,
    backgroundColor: 'rgba(115, 108, 139, 0.12)',
    shadowColor: '#8F63D8',
    shadowOpacity: 0.12,
    shadowRadius: 28,
    shadowOffset: { width: 0, height: 12 },
    overflow: 'hidden',
  },
  wrapCompact: {
    marginLeft: 10,
    marginRight: 10,
    marginTop: 8,
    paddingTop: 10,
    paddingRight: 12,
    paddingBottom: 11,
    paddingLeft: 12,
    borderRadius: 19,
    backgroundColor: 'rgba(115, 108, 139, 0.10)',
    shadowOpacity: 0.08,
    shadowRadius: 18,
  },
  softGlow: {
    position: 'absolute',
    width: 180,
    height: 90,
    borderRadius: 90,
    right: -40,
    top: -36,
    backgroundColor: 'rgba(139,156,255,0.08)',
  },
  kickerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  kickerRowCompact: { marginBottom: 5 },
  statusPill: {
    minHeight: 24,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 10,
    borderRadius: 999,
    backgroundColor: 'rgba(209,139,255,0.10)',
  },
  statusPillApproved: { backgroundColor: 'rgba(159,185,165,0.11)' },
  statusDot: { width: 5, height: 5, borderRadius: 3, backgroundColor: palette.violet },
  statusDotApproved: { backgroundColor: palette.sage },
  status: { color: '#D9B6FF', fontSize: 8, fontWeight: '800', letterSpacing: 1.05 },
  statusApproved: { color: palette.sage },
  revision: { color: palette.muted, fontSize: 8, letterSpacing: 0.9 },
  header: { minHeight: 60, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 20 },
  headerCompact: { minHeight: 0, flexDirection: 'column', alignItems: 'stretch', gap: 8 },
  identity: { flex: 1, minWidth: 0 },
  identityCopy: { flex: 1, minWidth: 0 },
  title: { color: palette.text, fontSize: 20, lineHeight: 25, fontWeight: '600', letterSpacing: -0.48 },
  titleCompact: { fontSize: 16, lineHeight: 20, letterSpacing: -0.3 },
  subtitle: { color: palette.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 5, maxWidth: 680 },
  subtitleCompact: { fontSize: 10, lineHeight: 15, marginTop: 4 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  actionsCompact: { width: '100%', justifyContent: 'flex-end', gap: 7, flexWrap: 'wrap' },
  actionButton: {
    minHeight: 38,
    paddingHorizontal: 13,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 14,
    borderWidth: 0,
    backgroundColor: 'rgba(139,156,255,0.12)',
  },
  actionButtonCompact: { minHeight: 44, paddingHorizontal: 12, borderRadius: 14 },
  resumeButton: { backgroundColor: 'rgba(125,231,255,0.10)' },
  approveButton: { backgroundColor: 'rgba(159,185,165,0.13)' },
  actionText: { color: palette.cyan, fontSize: 8, fontWeight: '800', letterSpacing: 0.75 },
  resumeText: { color: palette.cyan, fontSize: 8, fontWeight: '800', letterSpacing: 0.75 },
  approveText: { color: palette.sage, fontSize: 8, fontWeight: '800', letterSpacing: 0.75 },
  disclosure: { width: 38, height: 38, borderRadius: 14, alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(255,255,255,0.035)' },
  disclosureCompact: { width: 44, height: 44 },
  disclosureText: { color: palette.textSoft, fontSize: 20, lineHeight: 22 },
  resumeHint: { color: palette.textSecondary, fontSize: 9, lineHeight: 14, paddingTop: 8, maxWidth: 720 },
  error: { color: palette.danger, fontSize: 10, lineHeight: 15, paddingTop: 8 },
  body: { marginTop: 14, paddingTop: 16, paddingRight: 10, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(167,151,255,0.12)' },
  bodyCompact: { marginTop: 10, paddingTop: 12, paddingRight: 0 },
  section: { marginBottom: 18 },
  sectionLabel: { color: palette.indigo, fontSize: 8, fontWeight: '800', letterSpacing: 1.1, marginBottom: 7 },
  objective: { color: palette.text, fontSize: 14, lineHeight: 22, maxWidth: 740 },
  item: { color: palette.textSecondary, fontSize: 12, lineHeight: 20, marginBottom: 4, maxWidth: 740 },
  meta: { color: palette.muted, fontSize: 8, letterSpacing: 0.5, marginTop: 2 },
});
