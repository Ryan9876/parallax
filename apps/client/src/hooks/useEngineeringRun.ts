import React from 'react';
import { api, type EngineeringRunDto } from '../lib/api';
import { runEngineeringAutonomy } from '../lib/autonomyApi';
import {
  clearEngineeringRunFailure,
  publishEngineeringRunFailure,
  subscribeEngineeringRunRetry,
} from '../lib/engineeringRunEvents';
import {
  automaticAutonomyOperationKey,
  canContinueEngineeringRunAutonomously,
} from '../state/engineeringRunContinuation';
import { subscribeApprovedWorkSpecification } from '../lib/workSpecEvents';

type EngineeringRunView = EngineeringRunDto & { autonomy_stop_reason?: string | null };

export function useEngineeringRun(conversationId: string | null, enabled: boolean) {
  const [run, setRun] = React.useState<EngineeringRunView | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const manualAutonomyAttemptRef = React.useRef(0);

  const clearFailure = React.useCallback(() => {
    setError(null);
    clearEngineeringRunFailure(conversationId);
  }, [conversationId]);

  const recordFailure = React.useCallback((message: string, runId?: string | null) => {
    setError(message);
    if (conversationId && runId) {
      publishEngineeringRunFailure({
        conversationId,
        runId,
        message,
      });
    }
  }, [conversationId]);

  const applyAutonomyResult = React.useCallback(async (candidate: EngineeringRunDto, operationKey: string) => {
    const result = await runEngineeringAutonomy(candidate, operationKey);
    const next: EngineeringRunView = { ...result.run, autonomy_stop_reason: result.stop_reason };
    setRun(next);
    clearFailure();
    return next;
  }, [clearFailure]);

  const continueAutomatically = React.useCallback(async (candidate: EngineeringRunDto) => {
    if (!canContinueEngineeringRunAutonomously(candidate)) return candidate;
    return applyAutonomyResult(candidate, automaticAutonomyOperationKey(candidate));
  }, [applyAutonomyResult]);

  const activateApproved = React.useCallback(async (specificationId?: string | null) => {
    if (!enabled || !conversationId) return null;
    const activated = await api.activateEngineeringRun(conversationId, specificationId);
    setRun(activated);
    clearFailure();
    if (!canContinueEngineeringRunAutonomously(activated)) return activated;
    try {
      return await continueAutomatically(activated);
    } catch (caught) {
      // Activation is durable server truth even when the bounded autonomous
      // handoff fails. Keep the PLAN/active run visible so the operator can
      // retry without fabricating or discarding canonical state.
      recordFailure(
        caught instanceof Error ? caught.message : 'Autonomous Code run failed after activation.',
        activated.id,
      );
      return activated;
    }
  }, [clearFailure, continueAutomatically, conversationId, enabled, recordFailure]);

  const refresh = React.useCallback(async () => {
    if (!enabled || !conversationId) {
      setRun(null);
      clearFailure();
      return;
    }
    try {
      const latest = await api.latestEngineeringRun(conversationId);
      if (latest) {
        setRun(latest);
        clearFailure();
        if (!canContinueEngineeringRunAutonomously(latest)) return;
        setBusy(true);
        try {
          // One bounded continuation attempt per refresh. The deterministic
          // key makes StrictMode/reconnect replay safe and prevents duplicate
          // protected execution for the same server revision.
          await continueAutomatically(latest);
        } catch (caught) {
          recordFailure(
            caught instanceof Error ? caught.message : 'Autonomous Code run continuation failed.',
            latest.id,
          );
        } finally {
          setBusy(false);
        }
        return;
      }
      const approved = await api.latestApprovedWorkSpecification(conversationId);
      if (approved) {
        setBusy(true);
        try {
          await activateApproved(approved.id);
        } finally {
          setBusy(false);
        }
      } else {
        setRun(null);
        clearFailure();
      }
    } catch (caught) {
      setRun(null);
      setError(caught instanceof Error ? caught.message : 'Code run status unavailable.');
      setBusy(false);
    }
  }, [activateApproved, clearFailure, continueAutomatically, conversationId, enabled, recordFailure]);

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
    clearFailure();
    try {
      const key = `${action}-${run.id}-${run.revision}-${Date.now()}`;
      const result = action === 'pause'
        ? await api.pauseEngineeringRun(run, key)
        : action === 'resume'
          ? await api.resumeEngineeringRun(run, key)
          : await api.cancelEngineeringRun(run, key);
      setRun(result.run);
      clearFailure();
    } catch (caught) {
      recordFailure(
        caught instanceof Error ? caught.message : `Code run ${action} failed.`,
        run.id,
      );
    } finally { setBusy(false); }
  }, [busy, clearFailure, recordFailure, run]);

  const runAutonomously = React.useCallback(async () => {
    if (!run || busy || !canContinueEngineeringRunAutonomously(run)) return;
    setBusy(true);
    clearFailure();
    manualAutonomyAttemptRef.current += 1;
    try {
      await applyAutonomyResult(
        run,
        `autonomous-manual-${run.id}-${run.revision}-${manualAutonomyAttemptRef.current}`,
      );
    } catch (caught) {
      recordFailure(
        caught instanceof Error ? caught.message : 'Autonomous Code run failed.',
        run.id,
      );
    } finally { setBusy(false); }
  }, [applyAutonomyResult, busy, clearFailure, recordFailure, run]);

  const continueRun = React.useCallback(async () => {
    if (!run) return;
    if (canContinueEngineeringRunAutonomously(run)) {
      await runAutonomously();
      return;
    }
    await mutate('resume');
  }, [mutate, run, runAutonomously]);

  React.useEffect(() => subscribeEngineeringRunRetry((targetConversationId) => {
    if (!enabled || !conversationId || targetConversationId !== conversationId) return;
    void continueRun();
  }), [continueRun, conversationId, enabled]);

  React.useEffect(() => () => {
    clearEngineeringRunFailure(conversationId);
  }, [conversationId]);

  return {
    run,
    busy,
    error,
    refresh,
    pause: () => mutate('pause'),
    // Existing App wiring uses the resume callback. In active protected stages,
    // continuation means the bounded autonomous cycle; PAUSED/FAILED retains
    // the original explicit resume behavior.
    resume: continueRun,
    cancel: () => mutate('cancel'),
    runAutonomously,
  };
}
