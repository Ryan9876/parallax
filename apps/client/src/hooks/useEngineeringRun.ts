import React from 'react';
import { api, type EngineeringRunDto } from '../lib/api';

export function useEngineeringRun(conversationId: string | null, enabled: boolean) {
  const [run, setRun] = React.useState<EngineeringRunDto | null>(null);
  const [busy, setBusy] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!enabled || !conversationId) {
      setRun(null);
      return null;
    }

    const existing = await api.latestEngineeringRun(conversationId);
    if (existing) {
      setRun(existing);
      return existing;
    }

    const conversation = await api.getConversation(conversationId);
    if (conversation.mode !== 'code') {
      setRun(null);
      return null;
    }

    const activated = await api.ensureEngineeringRun(conversation.id, conversation.spec_id);
    setRun(activated);
    return activated;
  }, [conversationId, enabled]);

  React.useEffect(() => {
    void refresh().catch(() => setRun(null));
  }, [refresh]);

  const mutate = React.useCallback(async (action: 'pause' | 'resume' | 'cancel') => {
    if (!run || busy) return;
    setBusy(true);
    try {
      const key = `${action}-${run.id}-${run.revision}-${Date.now()}`;
      const result = action === 'pause'
        ? await api.pauseEngineeringRun(run, key)
        : action === 'resume'
          ? await api.resumeEngineeringRun(run, key)
          : await api.cancelEngineeringRun(run, key);
      setRun(result.run);
    } finally {
      setBusy(false);
    }
  }, [busy, run]);

  return {
    run,
    busy,
    refresh,
    pause: () => mutate('pause'),
    resume: () => mutate('resume'),
    cancel: () => mutate('cancel'),
  };
}
