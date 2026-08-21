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
  const [expanded, setExpanded] = React.useState(false);

  React.useEffect(() => { setExpanded(false); }, [specification?.id]);

  if (!specification && !canDraft && !error) return null;

  const approved = specification?.status === 'APPROVED';
  const statusLabel = specification ? `SPEC · ${specification.status}` : 'SPEC · NOT CAPTURED';
  const traceTone = approved ? 'sage' : 'peach';

  return (
    <View style={styles.wrap} accessibilityLabel="Work specification">
      {!reducedGraphics && <EditorialTrace active={busy || Boolean(specification)} tone={traceTone} />}
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
              {specification ? specification.objective : 'Turn the current objective into a durable specification before implementation.'}
            </Text>
          </View>
        </TouchableOpacity>

        <View style={styles.actions}>
          {specification?.status === 'DRAFT' && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel="Approve work specification" disabled={busy} onPress={onApprove} style={[styles.actionButton, styles.approveButton]}>
              <Text style={styles.approveText}>{busy ? 'WORKING…' : 'APPROVE'}</Text>
            </TouchableOpacity>
          )}
          {canDraft && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel={specification ? 'Refresh work specification draft' : 'Capture work specification'} disabled={busy} onPress={onDraft} style={styles.actionButton}>
              <Text style={styles.actionText}>{busy ? 'DRAFTING…' : specification ? 'REFRESH DRAFT' : 'CAPTURE SPEC'}</Text>
            </TouchableOpacity>
          )}
          {specification && (
            <TouchableOpacity accessibilityRole="button" accessibilityLabel={expanded ? 'Collapse work specification' : 'Expand work specification'} onPress={() => setExpanded((value) => !value)} style={styles.disclosure}>
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
          <Text style={styles.meta}>Confidence {Math.round(specification.confidence * 100)}% · {specification.status === 'APPROVED' ? 'operator approved' : 'operator approval required'}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'relative', marginLeft: 34, marginRight: 52, marginTop: 24, paddingTop: 16, paddingRight: 18, paddingBottom: 18, paddingLeft: 22, borderLeftWidth: 3, borderLeftColor: 'rgba(223,167,143,0.82)', borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(240,228,207,0.18)', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.borderStrong, backgroundColor: 'rgba(18,18,35,0.46)', overflow: 'hidden' },
  kickerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 9 },
  status: { color: palette.peach, fontSize: 9, fontWeight: '800', letterSpacing: 1.2 },
  statusApproved: { color: palette.sage },
  revision: { color: palette.muted, fontSize: 8, letterSpacing: 0.9 },
  header: { minHeight: 66, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 20 },
  identity: { flex: 1, minWidth: 0 },
  identityCopy: { flex: 1, minWidth: 0 },
  title: { color: palette.cream, fontSize: 22, lineHeight: 26, fontWeight: '600', letterSpacing: -0.55 },
  subtitle: { color: palette.textSecondary, fontSize: 12, lineHeight: 18, marginTop: 6, maxWidth: 680 },
  actions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  actionButton: { minHeight: 38, paddingHorizontal: 13, alignItems: 'center', justifyContent: 'center', borderRadius: 14, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.indigoWash },
  approveButton: { backgroundColor: palette.sageWash, borderColor: 'rgba(159,185,165,0.52)' },
  actionText: { color: palette.cyan, fontSize: 8, fontWeight: '800', letterSpacing: 0.75 },
  approveText: { color: palette.sage, fontSize: 8, fontWeight: '800', letterSpacing: 0.75 },
  disclosure: { width: 38, height: 38, alignItems: 'center', justifyContent: 'center' },
  disclosureText: { color: palette.cream, fontSize: 20, lineHeight: 22 },
  error: { color: palette.danger, fontSize: 10, lineHeight: 15, paddingTop: 8 },
  body: { marginTop: 16, paddingTop: 18, paddingRight: 10, borderTopWidth: StyleSheet.hairlineWidth, borderTopColor: 'rgba(240,228,207,0.18)' },
  section: { marginBottom: 18 },
  sectionLabel: { color: palette.peach, fontSize: 8, fontWeight: '800', letterSpacing: 1.1, marginBottom: 7 },
  objective: { color: palette.text, fontSize: 14, lineHeight: 22, maxWidth: 740 },
  item: { color: palette.textSecondary, fontSize: 12, lineHeight: 20, marginBottom: 4, maxWidth: 740 },
  meta: { color: palette.muted, fontSize: 8, letterSpacing: 0.5, marginTop: 2 },
});
