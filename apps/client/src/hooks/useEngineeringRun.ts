import React from 'react';
import { api, type EngineeringRunDto } from '../lib/api';
import { runEngineeringAutonomy } from '../lib/autonomyApi';
import { subscribeApprovedWorkSpecification } from '../lib/workSpecEvents';

const AUTONOMOUS_STAGES = new Set(['PLAN', 'BUILD', 'TEST', 'VERIFY']);
type EngineeringRunView = EngineeringRunDto & { autonomy_stop_reason?: string | null };

export function useEngineeringRun(conversationId: string | null, enabled: boolean) {
  const [run, setRun] = React.useState<EngineeringRunView | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const activateApproved = React.useCallback(async (specificationId?: string | null) => {
    if (!enabled || !conversationId) return null;
    const activated = await api.activateEngineeringRun(conversationId, specificationId);
    setRun(activated);
    setError(null);
    return activated;
  }, [conversationId, enabled]);

  const refresh = React.useCallback(async () => {
    if (!enabled || !conversationId) {
      setRun(null);
      setError(null);
      return;
    }
    try {
      const latest = await api.latestEngineeringRun(conversationId);
      if (latest) {
        setRun(latest);
        setError(null);
        return;
      }
      const approved = await api.latestApprovedWorkSpecification(conversationId);
      if (approved) {
        await activateApproved(approved.id);
      } else {
        setRun(null);
        setError(null);
      }
    } catch (caught) {
      setRun(null);
      setError(caught instanceof Error ? caught.message : 'Code run status unavailable.');
    }
  }, [activateApproved, conversationId, enabled]);

  React.useEffect(() => { void refresh(); }, [refresh]);

  React.useEffect(() => subscribeApprovedWorkSpecification((event) => {
    if (!enabled || !conversationId || event.conversationId !== conversationId) return;
    setBusy(true);
    void activateApproved(event.specificationId)
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Code run activation failed.'))
      .finally(() => setBusy(false));
  }), [activateApproved, conversationId, enabled]);

  const mutate = React.useCallback(async (action: 'pause' | 'resume' | 'cancel') => {
    if (!run || busy) return;
    setBusy(true);
    setError(null);
    try {
      const key = `${action}-${run.id}-${run.revision}-${Date.now()}`;
      const result = action === 'pause'
        ? await api.pauseEngineeringRun(run, key)
        : action === 'resume'
          ? await api.resumeEngineeringRun(run, key)
          : await api.cancelEngineeringRun(run, key);
      setRun(result.run);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Code run ${action} failed.`);
    } finally { setBusy(false); }
  }, [busy, run]);

  const runAutonomously = React.useCallback(async () => {
    if (!run || busy) return;
    setBusy(true);
    setError(null);
    try {
      const result = await runEngineeringAutonomy(
        run,
        `autonomous-${run.id}-${run.revision}-${Date.now()}`,
      );
      setRun({ ...result.run, autonomy_stop_reason: result.stop_reason });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Autonomous Code run failed.');
    } finally { setBusy(false); }
  }, [busy, run]);

  const continueRun = React.useCallback(async () => {
    if (!run) return;
    if (AUTONOMOUS_STAGES.has(run.state)) {
      await runAutonomously();
      return;
    }
    await mutate('resume');
  }, [mutate, run, runAutonomously]);

  return {
    run,
    busy,
    error,
    refresh,
    pause: () => mutate('pause'),
    // Existing App wiring uses the resume callback. In active protected stages,
    // continuation now means the bounded autonomous cycle; PAUSED/FAILED retains
    // the original explicit resume behavior.
    resume: continueRun,
    cancel: () => mutate('cancel'),
    runAutonomously,
  };
}
