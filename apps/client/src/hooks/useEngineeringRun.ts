import React from 'react';
import { api, type EngineeringRunDto } from '../lib/api';

export function useEngineeringRun(conversationId: string | null, enabled: boolean) {
  const [run, setRun] = React.useState<EngineeringRunDto | null>(null);
  const [busy, setBusy] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!enabled || !conversationId) { setRun(null); return; }
    setRun(await api.latestEngineeringRun(conversationId));
  }, [conversationId, enabled]);

  React.useEffect(() => { void refresh().catch(() => setRun(null)); }, [refresh]);

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
    } finally { setBusy(false); }
  }, [busy, run]);

  return { run, busy, refresh, pause: () => mutate('pause'), resume: () => mutate('resume'), cancel: () => mutate('cancel') };
}
