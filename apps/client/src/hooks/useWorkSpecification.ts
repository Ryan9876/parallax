import React from 'react';
import { api, type ConversationDto, type WorkSpecificationDto } from '../lib/api';
import { publishApprovedWorkSpecification } from '../lib/workSpecEvents';

export function useWorkSpecification(conversationId: string | null) {
  const [specification, setSpecification] = React.useState<WorkSpecificationDto | null>(null);
  const [approvedSpecification, setApprovedSpecification] = React.useState<WorkSpecificationDto | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    if (!conversationId) {
      setSpecification(null);
      setApprovedSpecification(null);
      setError(null);
      return;
    }
    try {
      const latest = await api.latestWorkSpecification(conversationId);
      const approved = !latest
        ? null
        : latest.status === 'APPROVED'
          ? latest
          : await api.latestApprovedWorkSpecification(conversationId).catch(() => null);
      setSpecification(latest);
      setApprovedSpecification(approved);
      setError(null);
    } catch {
      setSpecification(null);
      setApprovedSpecification(null);
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
      setApprovedSpecification(approved);
      publishApprovedWorkSpecification({
        conversationId: approved.conversation_id,
        specificationId: approved.id,
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Specification approval failed.');
    } finally {
      setBusy(false);
    }
  }, [busy, specification]);

  const resumeApprovedScope = React.useCallback(async (): Promise<ConversationDto | null> => {
    if (!conversationId || busy || specification?.status !== 'APPROVED') return null;
    setBusy(true);
    setError(null);
    try {
      return await api.resumeApprovedScope(conversationId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Approved scope could not be resumed.');
      return null;
    } finally {
      setBusy(false);
    }
  }, [busy, conversationId, specification?.status]);

  return {
    specification,
    approvedSpecification,
    busy,
    error,
    refresh,
    draft,
    approve,
    resumeApprovedScope,
  };
}
