import React from 'react';
import { api, type WorkSpecificationDto } from '../lib/api';

export function useWorkSpecification(conversationId: string | null) {
  const [specification, setSpecification] = React.useState<WorkSpecificationDto | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    if (!conversationId) {
      setSpecification(null);
      setError(null);
      return;
    }
    try {
      const latest = await api.latestWorkSpecification(conversationId);
      setSpecification(latest);
      setError(null);
    } catch {
      // v0.7 keeps specification status additive. A temporary unavailable
      // specification endpoint must not block the durable conversation itself.
      setSpecification(null);
    }
  }, [conversationId]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const draft = React.useCallback(async () => {
    if (!conversationId || busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await api.draftWorkSpecification(conversationId);
      setSpecification(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Specification drafting failed.');
    } finally {
      setBusy(false);
    }
  }, [busy, conversationId]);

  const approve = React.useCallback(async () => {
    if (!specification || busy || specification.status !== 'DRAFT') return;
    setBusy(true);
    setError(null);
    try {
      const approved = await api.approveWorkSpecification(specification.id);
      setSpecification(approved);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Specification approval failed.');
    } finally {
      setBusy(false);
    }
  }, [busy, specification]);

  return { specification, busy, error, refresh, draft, approve };
}
