import React from 'react';
import { api, type EngineeringRunDto } from '../lib/api';
import { subscribeApprovedWorkSpecification } from '../lib/workSpecEvents';

export function useEngineeringRun(conversationId: string | null, enabled: boolean) {
  const [run, setRun] = React.useState<EngineeringRunDto | null>(null);
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

  return {
    run,
    busy,
    error,
    refresh,
    pause: () => mutate('pause'),
    resume: () => mutate('resume'),
    cancel: () => mutate('cancel'),
  };
}
