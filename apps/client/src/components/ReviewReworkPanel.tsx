import React from 'react';
import { StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { EngineeringRunDto } from '../lib/api';
import { palette } from '../theme';

export function ReviewReworkPanel({ run, busy, onRequestChanges }: {
  run: EngineeringRunDto;
  busy: boolean;
  onRequestChanges(acceptanceIds: string[], finding: string): void;
}) {
  const [selected, setSelected] = React.useState<string[]>([]);
  const [finding, setFinding] = React.useState('');

  React.useEffect(() => {
    setSelected([]);
    setFinding('');
  }, [run.id, run.revision]);

  if (run.state !== 'REVIEW' || run.binding_status !== 'APPROVED_SPEC_BOUND') return null;

  const toggle = (id: string) => {
    if (busy) return;
    setSelected((current) => current.includes(id)
      ? current.filter((value) => value !== id)
      : [...current, id]);
  };
  const normalized = finding.trim();
  const canSubmit = selected.length > 0 && normalized.length > 0 && !busy;

  return (
    <View style={styles.panel} testID="review-rework-panel" accessibilityLabel="Request changes to reviewed work">
      <Text style={styles.kicker}>REVIEW FEEDBACK</Text>
      <Text style={styles.title}>Something still needs work?</Text>
      <Text style={styles.copy}>Choose what needs attention and tell Parallax what should change. The approved goal stays the same.</Text>
      <Text style={styles.label}>What needs attention</Text>
      <View style={styles.criteria}>
        {run.acceptance_criteria.map((criterion) => {
          const checked = selected.includes(criterion.id);
          return (
            <TouchableOpacity
              key={criterion.id}
              accessibilityRole="checkbox"
              accessibilityLabel={`${criterion.id}: ${criterion.text}`}
              accessibilityState={{ checked, disabled: busy }}
              disabled={busy}
              onPress={() => toggle(criterion.id)}
              style={[styles.criterion, checked && styles.criterionSelected]}
            >
              <View style={[styles.check, checked && styles.checkSelected]}><Text style={styles.checkText}>{checked ? '✓' : ''}</Text></View>
              <View style={styles.criterionCopy}>
                <Text style={styles.criterionId}>{criterion.id}</Text>
                <Text style={styles.criterionText}>{criterion.text}</Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>
      <Text style={styles.label}>What should change</Text>
      <TextInput
        accessibilityLabel="What should Parallax change"
        value={finding}
        onChangeText={setFinding}
        editable={!busy}
        multiline
        maxLength={1200}
        placeholder="Describe the problem and the correction you want within the approved plan."
        placeholderTextColor={palette.muted}
        style={styles.input}
      />
      <View style={styles.footer}>
        <Text style={styles.hint}>{selected.length ? `${selected.length} success check${selected.length === 1 ? '' : 's'} selected` : 'Select at least one success check'}</Text>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityLabel="Request changes"
          accessibilityState={{ disabled: !canSubmit }}
          disabled={!canSubmit}
          onPress={() => onRequestChanges([...selected].sort(), normalized)}
          style={[styles.button, !canSubmit && styles.buttonDisabled]}
        >
          <Text style={styles.buttonText}>{busy ? 'Requesting…' : 'Request changes'}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: { marginTop: 16, padding: 16, borderRadius: 16, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, backgroundColor: palette.ivory50 },
  kicker: { color: palette.rust600, fontSize: 11, lineHeight: 15, fontWeight: '800', letterSpacing: 0.8 },
  title: { color: palette.charcoal950, fontSize: 18, lineHeight: 24, fontWeight: '800', marginTop: 5 },
  copy: { color: palette.charcoal600, fontSize: 13, lineHeight: 20, marginTop: 5, maxWidth: 720 },
  label: { color: palette.charcoal800, fontSize: 12, lineHeight: 17, fontWeight: '800', marginTop: 14, marginBottom: 6 },
  criteria: { gap: 7 },
  criterion: { minHeight: 48, flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 11, paddingVertical: 9, borderRadius: 12, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.border, backgroundColor: palette.cream100 },
  criterionSelected: { borderColor: palette.teal600, backgroundColor: 'rgba(36,139,139,0.08)' },
  check: { width: 24, height: 24, borderRadius: 7, borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.ivory50 },
  checkSelected: { borderColor: palette.teal600, backgroundColor: palette.teal600 },
  checkText: { color: palette.ivory50, fontSize: 14, fontWeight: '900' },
  criterionCopy: { flex: 1, minWidth: 0 },
  criterionId: { color: palette.olive700, fontSize: 11, lineHeight: 15, fontWeight: '800' },
  criterionText: { color: palette.charcoal800, fontSize: 13, lineHeight: 19, marginTop: 1 },
  input: { minHeight: 92, maxHeight: 180, textAlignVertical: 'top', borderWidth: StyleSheet.hairlineWidth, borderColor: palette.borderStrong, borderRadius: 12, backgroundColor: palette.cream100, color: palette.charcoal950, fontSize: 14, lineHeight: 20, paddingHorizontal: 12, paddingVertical: 11 },
  footer: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, alignItems: 'center', justifyContent: 'space-between', marginTop: 12 },
  hint: { color: palette.charcoal600, fontSize: 12, lineHeight: 17 },
  button: { minHeight: 44, paddingHorizontal: 16, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.rust600 },
  buttonDisabled: { opacity: 0.48 },
  buttonText: { color: palette.ivory50, fontSize: 13, lineHeight: 18, fontWeight: '800' },
});
