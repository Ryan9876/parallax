import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { WorkSpecificationDto } from '../lib/api';
import { palette } from '../theme';
import { EditorialTrace } from './EditorialTrace';

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
  onDraft,
  onApprove,
}: {
  specification: WorkSpecificationDto | null;
  busy: boolean;
  error: string | null;
  canDraft: boolean;
  onDraft(): void;
  onApprove(): void;
}) {
  const [expanded, setExpanded] = React.useState(false);

  React.useEffect(() => {
    setExpanded(false);
  }, [specification?.id]);

  if (!specification && !canDraft && !error) return null;

  const approved = specification?.status === 'APPROVED';
  const statusLabel = specification ? `SPEC · ${specification.status}` : 'SPEC · NOT CAPTURED';
  const traceTone = approved ? 'sage' : 'peach';

  return (
    <View style={styles.wrap} accessibilityLabel="Work specification">
      <EditorialTrace active={busy || Boolean(specification)} tone={traceTone} />
      <View style={styles.kickerRow}>
        <Text style={[styles.status, approved && styles.statusApproved]}>{statusLabel}</Text>
        {specification ? <Text style={styles.revision}>REVISION {specification.revision}</Text> : null}
      </View>

      <View style={styles.header}>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityState={{ expanded }}
          disabled={!specification}
          onPress={() => specification && setExpanded((value) => !value)}
          style={styles.identity}
        >
          <View style={styles.identityCopy}>
            <Text numberOfLines={2} style={styles.title}>
              {specification ? specification.title : 'Capture the implementation contract'}
            </Text>
            <Text numberOfLines={2} style={styles.subtitle}>
              {specification
                ? specification.objective
                : 'Turn the current objective into a durable specification before implementation.'}
            </Text>
          </View>
        </TouchableOpacity>

        <View style={styles.actions}>
          {specification?.status === 'DRAFT' && (
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Approve work specification"
              disabled={busy}
              onPress={onApprove}
              style={[styles.actionButton, styles.approveButton]}
            >
              <Text style={styles.approveText}>{busy ? 'WORKING…' : 'APPROVE'}</Text>
            </TouchableOpacity>
          )}
          {canDraft && (
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel={specification ? 'Refresh work specification draft' : 'Capture work specification'}
              disabled={busy}
              onPress={onDraft}
              style={styles.actionButton}
            >
              <Text style={styles.actionText}>{busy ? 'DRAFTING…' : specification ? 'REFRESH DRAFT' : 'CAPTURE SPEC'}</Text>
            </TouchableOpacity>
          )}
          {specification && (
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel={expanded ? 'Collapse work specification' : 'Expand work specification'}
              onPress={() => setExpanded((value) => !value)}
              style={styles.disclosure}
            >
              <Text style={styles.disclosureText}>{expanded ? '−' : '+'}</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {specification && expanded ? (
        <View style={styles.body}>
          <View style={styles.section}>
            <Text style={styles.sectionLabel}>OBJECTIVE</Text>
            <Text selectable style={styles.objective}>{specification.objective}</Text>
          </View>
          <Section label="ACCEPTANCE" items={specification.acceptance_criteria} />
          <Section label="CONSTRAINTS" items={specification.constraints} />
          <Section label="OPEN QUESTIONS" items={specification.open_questions} />
          <Section label="RISKS" items={specification.risks} />
          <Text style={styles.meta}>
            Confidence {Math.round(specification.confidence * 100)}% · {specification.status === 'APPROVED' ? 'operator approved' : 'operator approval required'}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'relative',
    marginHorizontal: 28,
    marginTop: 22,
    paddingTop: 12,
    paddingRight: 12,
    paddingBottom: 14,
    paddingLeft: 18,
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(223,167,143,0.62)',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: palette.border,
    backgroundColor: 'rgba(13,16,29,0.30)',
    overflow: 'hidden',
  },
  kickerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginBottom: 7,
  },
  status: { color: palette.peach, fontSize: 8, fontWeight: '800', letterSpacing: 1.05 },
  statusApproved: { color: palette.sage },
  revision: { color: palette.muted, fontSize: 8, letterSpacing: 0.8 },
  header: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 18,
  },
  identity: { flex: 1, minWidth: 0 },
  identityCopy: { flex: 1, minWidth: 0 },
  title: { color: palette.cream, fontSize: 18, lineHeight: 22, fontWeight: '600', letterSpacing: -0.35 },
  subtitle: { color: palette.textSecondary, fontSize: 11, lineHeight: 16, marginTop: 5, maxWidth: 660 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  actionButton: {
    minHeight: 36,
    paddingHorizontal: 11,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.borderStrong,
    backgroundColor: palette.indigoWash,
  },
  approveButton: { backgroundColor: palette.sageWash, borderColor: 'rgba(159,185,165,0.42)' },
  actionText: { color: palette.cyan, fontSize: 8, fontWeight: '800', letterSpacing: 0.65 },
  approveText: { color: palette.sage, fontSize: 8, fontWeight: '800', letterSpacing: 0.65 },
  disclosure: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  disclosureText: { color: palette.cream, fontSize: 18, lineHeight: 20 },
  error: { color: palette.danger, fontSize: 10, lineHeight: 15, paddingTop: 8 },
  body: { marginTop: 14, paddingTop: 16, paddingRight: 8, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(240,228,207,0.14)' },
  section: { marginBottom: 17 },
  sectionLabel: { color: palette.peach, fontSize: 8, fontWeight: '800', letterSpacing: 1.0, marginBottom: 6 },
  objective: { color: palette.text, fontSize: 13, lineHeight: 21, maxWidth: 720 },
  item: { color: palette.textSecondary, fontSize: 11, lineHeight: 19, marginBottom: 3, maxWidth: 720 },
  meta: { color: palette.muted, fontSize: 8, letterSpacing: 0.45, marginTop: 2 },
});
