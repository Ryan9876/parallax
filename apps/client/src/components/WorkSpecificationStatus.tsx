import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
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

  return (
    <View style={styles.wrap} accessibilityLabel="Work specification">
      <View style={styles.header}>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityState={{ expanded }}
          disabled={!specification}
          onPress={() => specification && setExpanded((value) => !value)}
          style={styles.identity}
        >
          <View style={[styles.dot, approved && styles.dotApproved]} />
          <View style={styles.identityCopy}>
            <Text style={[styles.status, approved && styles.statusApproved]}>{statusLabel}</Text>
            <Text numberOfLines={1} style={styles.title}>
              {specification ? `R${specification.revision} · ${specification.title}` : 'Turn this conversation into an explicit implementation contract.'}
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
    marginHorizontal: 24,
    marginTop: 10,
    borderRadius: 10,
    backgroundColor: palette.glass,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.border,
    overflow: 'hidden',
  },
  header: {
    minHeight: 52,
    paddingHorizontal: 14,
    paddingVertical: 9,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  identity: { flex: 1, minWidth: 0, flexDirection: 'row', alignItems: 'center', gap: 9 },
  identityCopy: { flex: 1, minWidth: 0 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: palette.indigo },
  dotApproved: { backgroundColor: palette.success },
  status: { color: palette.indigo, fontSize: 8, fontWeight: '800', letterSpacing: 0.9 },
  statusApproved: { color: palette.success },
  title: { color: palette.textSoft, fontSize: 11, marginTop: 3 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  actionButton: {
    minHeight: 34,
    paddingHorizontal: 10,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: palette.borderStrong,
    backgroundColor: palette.indigoWash,
  },
  approveButton: { backgroundColor: 'rgba(114,227,196,0.10)', borderColor: 'rgba(114,227,196,0.34)' },
  actionText: { color: palette.cyan, fontSize: 8, fontWeight: '800', letterSpacing: 0.65 },
  approveText: { color: palette.success, fontSize: 8, fontWeight: '800', letterSpacing: 0.65 },
  disclosure: { width: 34, height: 34, alignItems: 'center', justifyContent: 'center' },
  disclosureText: { color: palette.textSecondary, fontSize: 18, lineHeight: 20 },
  error: { color: palette.danger, fontSize: 10, lineHeight: 15, paddingHorizontal: 14, paddingBottom: 10 },
  body: { borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: palette.border, paddingHorizontal: 16, paddingVertical: 14 },
  section: { marginBottom: 13 },
  sectionLabel: { color: palette.muted, fontSize: 8, fontWeight: '800', letterSpacing: 0.85, marginBottom: 5 },
  objective: { color: palette.text, fontSize: 12, lineHeight: 19 },
  item: { color: palette.textSecondary, fontSize: 11, lineHeight: 18, marginBottom: 2 },
  meta: { color: palette.muted, fontSize: 8, letterSpacing: 0.45, marginTop: 1 },
});
