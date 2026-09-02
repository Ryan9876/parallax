from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:110]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Client API uses the same exact run revision + idempotent operation contract.
replace_once(
    "apps/client/src/lib/api.ts",
    """  resumeEngineeringRun: (run: EngineeringRunDto, operationKey: string) =>
    json<{ run: EngineeringRunDto }>(`/v1/engineering-runs/${run.id}/resume`, {
      method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
  cancelEngineeringRun: (run: EngineeringRunDto, operationKey: string) =>
""",
    """  resumeEngineeringRun: (run: EngineeringRunDto, operationKey: string) =>
    json<{ run: EngineeringRunDto }>(`/v1/engineering-runs/${run.id}/resume`, {
      method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
  reviewReworkEngineeringRun: (run: EngineeringRunDto, operationKey: string, acceptanceIds: string[], finding: string) =>
    json<{ run: EngineeringRunDto }>(`/v1/engineering-runs/${run.id}/review-rework`, {
      method: 'POST',
      body: JSON.stringify({
        operation_key: operationKey,
        expected_revision: run.revision,
        acceptance_ids: acceptanceIds,
        finding,
      }),
    }),
  cancelEngineeringRun: (run: EngineeringRunDto, operationKey: string) =>
""",
)

# Hook explicitly triggers rework, reconciles a split run/worker transaction, then uses normal autonomy.
review_hook = '''
  const requestReviewRework = React.useCallback(async (acceptanceIds: string[], finding: string) => {
    if (!run || busy || run.state !== 'REVIEW') return;
    const reviewed = run;
    const operationKey = `review-rework-${reviewed.id}-${reviewed.revision}-${Date.now()}`;
    const normalizedIds = [...acceptanceIds].sort();
    const normalizedFinding = finding.trim();
    if (!normalizedIds.length || !normalizedFinding) return;

    setBusy(true);
    clearFailure();
    try {
      let result: { run: EngineeringRunDto };
      try {
        result = await api.reviewReworkEngineeringRun(
          reviewed,
          operationKey,
          normalizedIds,
          normalizedFinding,
        );
      } catch (firstError) {
        // REVIEW rework spans the durable run transition and the worker reset.
        // If the first request advanced the exact run to PLAN before returning
        // an error, replay the same operation key once so only the pending
        // worker preparation can complete. Never invent a new correction op.
        const latest = conversationId ? await api.latestEngineeringRun(conversationId).catch(() => null) : null;
        if (
          !latest
          || latest.id !== reviewed.id
          || latest.revision <= reviewed.revision
          || latest.state !== 'PLAN'
        ) {
          throw firstError;
        }
        setRun(latest);
        result = await api.reviewReworkEngineeringRun(
          reviewed,
          operationKey,
          normalizedIds,
          normalizedFinding,
        );
      }

      const reworked = result.run;
      setRun(reworked);
      clearFailure();
      if (!canContinueEngineeringRunAutonomously(reworked)) return;
      try {
        await applyAutonomyResult(reworked, automaticAutonomyOperationKey(reworked));
      } catch (caught) {
        recordFailure(
          caught instanceof Error ? caught.message : 'Autonomous Code run failed after REVIEW rework.',
          reworked.id,
          caught instanceof EngineeringAutonomyError ? caught.code : null,
        );
      }
    } catch (caught) {
      recordFailure(
        caught instanceof Error ? caught.message : 'REVIEW changes could not be requested.',
        reviewed.id,
      );
    } finally {
      setBusy(false);
    }
  }, [applyAutonomyResult, busy, clearFailure, conversationId, recordFailure, run]);

'''
replace_once(
    "apps/client/src/hooks/useEngineeringRun.ts",
    """  const continueRun = React.useCallback(async () => {
""",
    review_hook + """  const continueRun = React.useCallback(async () => {
""",
)
replace_once(
    "apps/client/src/hooks/useEngineeringRun.ts",
    """    cancel: () => mutate('cancel'),
    runAutonomously,
""",
    """    cancel: () => mutate('cancel'),
    requestReviewRework,
    runAutonomously,
""",
)

# Shared accessible correction surface for desktop and compact mobile.
Path("apps/client/src/components/ReviewReworkPanel.tsx").write_text(
    '''import React from 'react';
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
''',
    encoding="utf-8",
)

# Desktop review status uses shared panel.
replace_once(
    "apps/client/src/components/EngineeringRunStatus.tsx",
    """import { palette } from '../theme';
""",
    """import { palette } from '../theme';
import { ReviewReworkPanel } from './ReviewReworkPanel';
""",
)
replace_once(
    "apps/client/src/components/EngineeringRunStatus.tsx",
    """export function EngineeringRunStatus({ run, busy, error, onPause, onResume, onCancel }: {
  run: EngineeringRunDto;
  busy: boolean;
  error?: string | null;
  onPause(): void;
  onResume(): void;
  onCancel(): void;
  reducedGraphics?: boolean;
}) {
""",
    """export function EngineeringRunStatus({ run, busy, error, onPause, onResume, onCancel, onRequestChanges }: {
  run: EngineeringRunDto;
  busy: boolean;
  error?: string | null;
  onPause(): void;
  onResume(): void;
  onCancel(): void;
  onRequestChanges(acceptanceIds: string[], finding: string): void;
  reducedGraphics?: boolean;
}) {
""",
)
replace_once(
    "apps/client/src/components/EngineeringRunStatus.tsx",
    """      <View style={styles.actions}>
""",
    """      {run.state === 'REVIEW' ? (
        <ReviewReworkPanel run={run} busy={busy} onRequestChanges={onRequestChanges} />
      ) : null}

      <View style={styles.actions}>
""",
)

# Compact mobile Progress screen uses the same interaction.
replace_once(
    "apps/client/src/components/mobile/MobileExperience.tsx",
    """import { ParallaxLogo } from '../ParallaxLogo';
""",
    """import { ParallaxLogo } from '../ParallaxLogo';
import { ReviewReworkPanel } from '../ReviewReworkPanel';
""",
)
replace_once(
    "apps/client/src/components/mobile/MobileExperience.tsx",
    """  onCaptureSpecification(): void;
  onReviewSpecification(): void;
  onOpenDetails(): void;
};

export function MobileBuildWorkspace({ specification, run, canDraft, busy, error, onCaptureSpecification, onReviewSpecification, onOpenDetails }: BuildWorkspaceProps) {
""",
    """  onCaptureSpecification(): void;
  onReviewSpecification(): void;
  onOpenDetails(): void;
  onRequestChanges(acceptanceIds: string[], finding: string): void;
};

export function MobileBuildWorkspace({ specification, run, canDraft, busy, error, onCaptureSpecification, onReviewSpecification, onOpenDetails, onRequestChanges }: BuildWorkspaceProps) {
""",
)
replace_once(
    "apps/client/src/components/mobile/MobileExperience.tsx",
    """      <View style={styles.lifecycleCard}>
""",
    """      {run?.state === 'REVIEW' ? (
        <ReviewReworkPanel run={run} busy={busy} onRequestChanges={onRequestChanges} />
      ) : null}

      <View style={styles.lifecycleCard}>
""",
)

# Main app wires both desktop and mobile through the same hook action.
replace_once(
    "apps/client/src/App.tsx",
    """                  busy={workSpecification.busy}
                  error={workSpecification.error}
                  onCaptureSpecification={() => void workSpecification.draft()}
                  onReviewSpecification={() => mobileSpecification && setMobileDetail('specification')}
                  onOpenDetails={() => mobileRun && setMobileDetail('live-build')}
                />
""",
    """                  busy={workSpecification.busy || engineering.busy}
                  error={workSpecification.error || engineering.error}
                  onCaptureSpecification={() => void workSpecification.draft()}
                  onReviewSpecification={() => mobileSpecification && setMobileDetail('specification')}
                  onOpenDetails={() => mobileRun && setMobileDetail('live-build')}
                  onRequestChanges={(acceptanceIds, finding) => void engineering.requestReviewRework(acceptanceIds, finding)}
                />
""",
)
replace_once(
    "apps/client/src/App.tsx",
    """                      onPause={() => void engineering.pause()}
                      onResume={() => void engineering.resume()}
                      onCancel={() => void engineering.cancel()}
                    />
""",
    """                      onPause={() => void engineering.pause()}
                      onResume={() => void engineering.resume()}
                      onCancel={() => void engineering.cancel()}
                      onRequestChanges={(acceptanceIds, finding) => void engineering.requestReviewRework(acceptanceIds, finding)}
                    />
""",
)

# Reduced-graphics fallback remains fully functional rather than hiding the action.
replace_once(
    "apps/client/src/FallbackApp.tsx",
    """              onPause={() => void engineering.pause()}
              onResume={() => void engineering.resume()}
              onCancel={() => void engineering.cancel()}
            />
""",
    """              onPause={() => void engineering.pause()}
              onResume={() => void engineering.resume()}
              onCancel={() => void engineering.cancel()}
              onRequestChanges={(acceptanceIds, finding) => void engineering.requestReviewRework(acceptanceIds, finding)}
            />
""",
)

# Fast source contract catches accidental API-only or one-surface regressions.
Path("apps/client/scripts/review-rework-contract.mjs").write_text(
    '''import { readFileSync } from 'node:fs';

function source(path) { return readFileSync(new URL(`../${path}`, import.meta.url), 'utf8'); }
function assert(condition, message) { if (!condition) throw new Error(message); }

const api = source('src/lib/api.ts');
const hook = source('src/hooks/useEngineeringRun.ts');
const panel = source('src/components/ReviewReworkPanel.tsx');
const desktop = source('src/components/EngineeringRunStatus.tsx');
const mobile = source('src/components/mobile/MobileExperience.tsx');
const app = source('src/App.tsx');
const fallback = source('src/FallbackApp.tsx');

assert(api.includes('/review-rework'), 'review rework API endpoint is not wired');
assert(api.includes('expected_revision: run.revision'), 'review rework API must remain revision-bound');
assert(hook.includes('requestReviewRework'), 'engineering hook lacks explicit REVIEW rework action');
assert(hook.includes('reviewed.revision') && hook.includes('latestEngineeringRun'), 'split-boundary reconciliation is missing');
assert(panel.includes('accessibilityRole="checkbox"'), 'acceptance selection is not accessibility-observable');
assert(panel.includes('accessibilityLabel="What should Parallax change"'), 'correction input lacks accessible identity');
assert(panel.includes('Request changes'), 'explicit human correction action is missing');
assert(panel.includes('maxLength={1200}'), 'client finding bound drifted from API contract');
assert(desktop.includes('<ReviewReworkPanel'), 'desktop REVIEW does not expose correction UI');
assert(mobile.includes('<ReviewReworkPanel'), 'compact mobile REVIEW does not expose correction UI');
assert(app.match(/onRequestChanges=/g)?.length === 2, 'main app must wire desktop and mobile rework actions');
assert(fallback.includes('onRequestChanges='), 'reduced-graphics client must preserve REVIEW rework');
console.log(JSON.stringify({ reviewRework: true, desktop: true, mobile: true, reducedGraphics: true, revisionBound: true }));
''',
    encoding="utf-8",
)
replace_once(
    "apps/client/package.json",
    """node scripts/test-workflow-guidance.cjs\"",
""",
    """node scripts/test-workflow-guidance.cjs && node scripts/review-rework-contract.mjs\"",
""",
)
