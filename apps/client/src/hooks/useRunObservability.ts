import React from 'react';
import type { EngineeringRunDto } from '../lib/api';
import { authenticatedRequest } from '../lib/api';
import {
  RunObservabilityClient,
  type AttemptEvidenceDto,
  type RunEventDto,
  type RunTransportState,
  type SourceDiffDto,
  type SourceFileDto,
  type SourceTreeDto,
} from '../lib/runObservability';
import { latestCandidateLineage, observedAttempts, observedLineages } from '../lib/observabilityProjection';

export type LiveBuildTab = 'Code' | 'Diff' | 'Terminal' | 'Tests' | 'Events' | 'Evidence';

export type RunObservabilityView = {
  events: RunEventDto[];
  transport: RunTransportState;
  unavailable: boolean;
  error: string | null;
  followLive: boolean;
  viewPaused: boolean;
  selectedTab: LiveBuildTab;
  lineages: string[];
  attempts: string[];
  candidateLineage: string | null;
  parentLineage: string | null;
  sourceTree: SourceTreeDto | null;
  sourceFile: SourceFileDto | null;
  sourceDiff: SourceDiffDto | null;
  evidence: AttemptEvidenceDto | null;
  readBusy: boolean;
  readError: string | null;
  selectedLineage: string | null;
  selectedPath: string | null;
  selectedAttempt: string | null;
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : 'Live observation unavailable';
}

function isUnavailable(error: unknown): boolean {
  const message = messageOf(error);
  return /\((404|503)\)|disabled|unavailable|not found/i.test(message);
}

export function useRunObservability(run: EngineeringRunDto | null, enabled: boolean) {
  const clientRef = React.useRef<RunObservabilityClient | null>(null);
  if (!clientRef.current) clientRef.current = new RunObservabilityClient(authenticatedRequest);
  const client = clientRef.current;
  const abortRef = React.useRef<AbortController | null>(null);
  const reconnectTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = React.useRef(0);
  const mountedRef = React.useRef(true);

  const [events, setEvents] = React.useState<RunEventDto[]>([]);
  const [transport, setTransport] = React.useState<RunTransportState>('CLOSED');
  const [error, setError] = React.useState<string | null>(null);
  const [unavailable, setUnavailable] = React.useState(false);
  const [followLive, setFollowLive] = React.useState(true);
  const [viewPaused, setViewPaused] = React.useState(false);
  const [selectedTab, setSelectedTab] = React.useState<LiveBuildTab>('Events');
  const [sourceTree, setSourceTree] = React.useState<SourceTreeDto | null>(null);
  const [sourceFile, setSourceFile] = React.useState<SourceFileDto | null>(null);
  const [sourceDiff, setSourceDiff] = React.useState<SourceDiffDto | null>(null);
  const [evidence, setEvidence] = React.useState<AttemptEvidenceDto | null>(null);
  const [readBusy, setReadBusy] = React.useState(false);
  const [readError, setReadError] = React.useState<string | null>(null);
  const [selectedLineage, setSelectedLineage] = React.useState<string | null>(null);
  const [selectedPath, setSelectedPath] = React.useState<string | null>(null);
  const [selectedAttempt, setSelectedAttempt] = React.useState<string | null>(null);

  const runId = run?.id ?? null;

  React.useEffect(() => () => {
    mountedRef.current = false;
    abortRef.current?.abort();
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
  }, []);

  const appendEvents = React.useCallback((incoming: RunEventDto[]) => {
    if (!incoming.length) return;
    setEvents((current) => {
      const existing = new Set(current.map((event) => event.sequence));
      const next = [...current];
      for (const event of incoming) if (!existing.has(event.sequence)) next.push(event);
      next.sort((left, right) => left.sequence - right.sequence);
      return next;
    });
  }, []);

  const connect = React.useCallback(async (selectedRunId: string) => {
    if (!enabled || runId !== selectedRunId || !mountedRef.current) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const replay = await client.replay(selectedRunId, 200);
      if (controller.signal.aborted || runId !== selectedRunId) return;
      appendEvents(replay);
      setUnavailable(false);
      setError(null);
      await client.stream(selectedRunId, (event) => appendEvents([event]), setTransport, controller.signal);
      if (!controller.signal.aborted && mountedRef.current && runId === selectedRunId) {
        reconnectAttemptRef.current += 1;
        const delay = Math.min(5000, 750 * reconnectAttemptRef.current);
        reconnectTimerRef.current = setTimeout(() => { void connect(selectedRunId); }, delay);
      }
    } catch (caught) {
      if (controller.signal.aborted || !mountedRef.current || runId !== selectedRunId) return;
      setError(messageOf(caught));
      setUnavailable(isUnavailable(caught));
      setTransport('ERROR');
      reconnectAttemptRef.current += 1;
      const delay = Math.min(8000, 1000 * reconnectAttemptRef.current);
      reconnectTimerRef.current = setTimeout(() => { void connect(selectedRunId); }, delay);
    }
  }, [appendEvents, client, enabled, runId]);

  React.useEffect(() => {
    abortRef.current?.abort();
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    reconnectAttemptRef.current = 0;
    setEvents([]);
    setTransport('CLOSED');
    setError(null);
    setUnavailable(false);
    setFollowLive(true);
    setViewPaused(false);
    setSelectedTab('Events');
    setSourceTree(null);
    setSourceFile(null);
    setSourceDiff(null);
    setEvidence(null);
    setReadError(null);
    setSelectedLineage(null);
    setSelectedPath(null);
    setSelectedAttempt(null);
    if (!enabled || !runId) return;
    client.cursor.reset(runId);
    void connect(runId);
    return () => abortRef.current?.abort();
  }, [client, connect, enabled, runId]);

  const retry = React.useCallback(() => {
    if (!runId || !enabled) return;
    reconnectAttemptRef.current = 0;
    setError(null);
    setUnavailable(false);
    void connect(runId);
  }, [connect, enabled, runId]);

  const lineages = React.useMemo(() => observedLineages(events), [events]);
  const attempts = React.useMemo(() => observedAttempts(events), [events]);
  const candidate = React.useMemo(() => latestCandidateLineage(events), [events]);

  const loadTree = React.useCallback(async (lineageId: string) => {
    if (!runId || !lineages.includes(lineageId)) return;
    setReadBusy(true);
    setReadError(null);
    setSourceFile(null);
    setSelectedPath(null);
    try {
      const result = await client.sourceTree(runId, lineageId, 0, 200);
      if (runId !== result.run_id) throw new Error('Protected source tree returned a mismatched run');
      setSelectedLineage(lineageId);
      setSourceTree(result);
    } catch (caught) { setReadError(messageOf(caught)); }
    finally { setReadBusy(false); }
  }, [client, lineages, runId]);

  const loadFile = React.useCallback(async (path: string) => {
    if (!runId || !selectedLineage || !sourceTree?.files.some((file) => file.path === path)) return;
    setReadBusy(true);
    setReadError(null);
    try {
      const result = await client.sourceFile(runId, selectedLineage, path);
      setSelectedPath(path);
      setSourceFile(result);
    } catch (caught) { setReadError(messageOf(caught)); }
    finally { setReadBusy(false); }
  }, [client, runId, selectedLineage, sourceTree]);

  const loadDiff = React.useCallback(async (fromLineage = candidate.parent, toLineage = candidate.candidate) => {
    if (!runId || !fromLineage || !toLineage || !lineages.includes(fromLineage) || !lineages.includes(toLineage)) return;
    setReadBusy(true);
    setReadError(null);
    try { setSourceDiff(await client.sourceDiff(runId, fromLineage, toLineage)); }
    catch (caught) { setReadError(messageOf(caught)); }
    finally { setReadBusy(false); }
  }, [candidate.candidate, candidate.parent, client, lineages, runId]);

  const loadEvidence = React.useCallback(async (attemptId: string) => {
    if (!runId || !attempts.includes(attemptId)) return;
    setReadBusy(true);
    setReadError(null);
    try {
      const result = await client.attemptEvidence(runId, attemptId);
      setSelectedAttempt(attemptId);
      setEvidence(result);
    } catch (caught) { setReadError(messageOf(caught)); }
    finally { setReadBusy(false); }
  }, [attempts, client, runId]);

  const pauseView = React.useCallback(() => setViewPaused(true), []);
  const jumpToLatest = React.useCallback(() => {
    setViewPaused(false);
    setFollowLive(true);
  }, []);

  const view: RunObservabilityView = {
    events,
    transport,
    unavailable,
    error,
    followLive,
    viewPaused,
    selectedTab,
    lineages,
    attempts,
    candidateLineage: candidate.candidate,
    parentLineage: candidate.parent,
    sourceTree,
    sourceFile,
    sourceDiff,
    evidence,
    readBusy,
    readError,
    selectedLineage,
    selectedPath,
    selectedAttempt,
  };

  return {
    view,
    setSelectedTab,
    setFollowLive,
    pauseView,
    jumpToLatest,
    retry,
    loadTree,
    loadFile,
    loadDiff,
    loadEvidence,
  };
}
