import type { EngineeringRunDto } from './api';
import type { RunEventDto, RunTransportState } from './runObservability';

export const PIPELINE_STAGES = ['SPECIFY', 'PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY', 'REVIEW'] as const;
export type PipelineStage = typeof PIPELINE_STAGES[number];
export type PipelineStatus = 'PENDING' | 'ACTIVE' | 'COMPLETE' | 'FAILED' | 'RECOVERING' | 'HUMAN_REQUIRED';

export type PipelineItem = {
  stage: PipelineStage;
  status: PipelineStatus;
  sequence: number | null;
  summary: string | null;
};

export type ObservabilityAlert = {
  key: string;
  sequence: number;
  tone: 'rust' | 'olive' | 'teal';
  title: string;
  detail: string;
};

export type ProviderIdentity = {
  provider: 'GitHub' | 'Vercel';
  sequence: number;
  status: string;
  identifier: string | null;
};

const TERMINAL_OUTCOMES = new Set(['SUCCEEDED', 'FAILED', 'HUMAN_REQUIRED']);
const SAFE_METADATA_KEYS = new Set([
  'attempt_number',
  'branch_name',
  'command_id',
  'content_digest',
  'control_status',
  'current_state',
  'current_step',
  'evaluation_id',
  'exit_code',
  'file_count',
  'meaningful_progress',
  'next_recovery_action',
  'preview_deployment_id',
  'preview_status',
  'program_id',
  'pull_request_number',
  'retry_count',
  'run_revision',
  'score_class',
  'source_revision',
  'stop_reason',
  'target_state',
  'timed_out',
  'tool_id',
  'worker_state',
] as const);

export function visibleStage(event: RunEventDto): PipelineStage | null {
  if (event.event_type === 'REVIEW_REQUIRED' || event.outcome === 'HUMAN_REQUIRED' || event.subsystem === 'REVIEW') return 'REVIEW';
  if (event.event_type === 'RUN_CREATED') return 'SPECIFY';
  if (event.event_type === 'SOURCE_LINEAGE_ACCEPTED' || event.subsystem === 'IMPLEMENTATION' || event.subsystem === 'SOURCE_LINEAGE') return 'IMPLEMENT';
  if (event.stage === 'PLAN' || event.stage === 'BUILD' || event.stage === 'TEST' || event.stage === 'VERIFY') return event.stage;
  return null;
}

function statusForEvent(event: RunEventDto): PipelineStatus {
  if (event.outcome === 'HUMAN_REQUIRED') return 'HUMAN_REQUIRED';
  if (event.outcome === 'RECOVERING' || event.outcome === 'REPLAYED') return 'RECOVERING';
  if (event.outcome === 'FAILED' || event.outcome === 'DENIED') return 'FAILED';
  if (event.outcome === 'SUCCEEDED') return 'COMPLETE';
  return 'ACTIVE';
}

export function projectPipeline(run: EngineeringRunDto, events: RunEventDto[]): PipelineItem[] {
  const latest = new Map<PipelineStage, RunEventDto>();
  for (const event of events) {
    const stage = visibleStage(event);
    if (stage) latest.set(stage, event);
  }

  return PIPELINE_STAGES.map((stage) => {
    const event = latest.get(stage);
    if (event) {
      return { stage, status: statusForEvent(event), sequence: event.sequence, summary: event.summary };
    }
    // Existing authoritative run state may identify the currently active protected stage,
    // but absence of persisted success never becomes completion.
    if (run.state === stage || (stage === 'REVIEW' && run.state === 'REVIEW')) {
      return { stage, status: stage === 'REVIEW' ? 'HUMAN_REQUIRED' : 'ACTIVE', sequence: null, summary: null };
    }
    return { stage, status: 'PENDING', sequence: null, summary: null };
  });
}

export function observedLineages(events: RunEventDto[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const event of events) {
    for (const lineage of [event.parent_source_lineage_ref, event.source_lineage_ref]) {
      if (lineage && !seen.has(lineage)) {
        seen.add(lineage);
        result.push(lineage);
      }
    }
  }
  return result;
}

export function observedAttempts(events: RunEventDto[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const event of events) {
    if (event.attempt_id && !seen.has(event.attempt_id)) {
      seen.add(event.attempt_id);
      result.push(event.attempt_id);
    }
  }
  return result;
}

export function latestCandidateLineage(events: RunEventDto[]): { candidate: string | null; parent: string | null } {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (!event) continue;
    if (event.source_lineage_ref) return { candidate: event.source_lineage_ref, parent: event.parent_source_lineage_ref };
  }
  return { candidate: null, parent: null };
}

export function safeEventMetadata(event: RunEventDto): Array<{ key: string; value: string }> {
  return Object.entries(event.metadata)
    .filter(([key]) => SAFE_METADATA_KEYS.has(key as never))
    .slice(0, 12)
    .map(([key, value]) => ({
      key,
      value: Array.isArray(value) ? value.map(String).join(', ') : String(value),
    }));
}

export function recentAlerts(events: RunEventDto[], limit = 5): ObservabilityAlert[] {
  return events
    .filter((event) => ['FAILED', 'DENIED', 'RECOVERING', 'HUMAN_REQUIRED'].includes(event.outcome))
    .slice(-limit)
    .reverse()
    .map((event) => ({
      key: `${event.id}:${event.sequence}`,
      sequence: event.sequence,
      tone: event.outcome === 'RECOVERING' ? 'teal' : event.outcome === 'HUMAN_REQUIRED' ? 'olive' : 'rust',
      title: event.outcome === 'HUMAN_REQUIRED' ? 'Human review required' : event.outcome === 'RECOVERING' ? 'Recovery in progress' : 'Execution attention required',
      detail: event.summary || event.failure_code || `${event.subsystem} · ${event.outcome}`,
    }));
}

export function providerIdentities(events: RunEventDto[]): ProviderIdentity[] {
  const identities: ProviderIdentity[] = [];
  for (const event of events) {
    if (event.subsystem === 'GITHUB') {
      const value = event.metadata.pull_request_number;
      identities.push({ provider: 'GitHub', sequence: event.sequence, status: event.outcome, identifier: typeof value === 'number' || typeof value === 'string' ? `PR #${value}` : null });
    } else if (event.subsystem === 'VERCEL') {
      const deployment = event.metadata.preview_deployment_id;
      const status = event.metadata.preview_status;
      identities.push({ provider: 'Vercel', sequence: event.sequence, status: typeof status === 'string' ? status : event.outcome, identifier: typeof deployment === 'string' ? deployment : null });
    }
  }
  return identities.slice(-4).reverse();
}

export function observerHealth(transport: RunTransportState, run: EngineeringRunDto, events: RunEventDto[]): {
  transport: string;
  run: string;
  tone: 'neutral' | 'teal' | 'olive' | 'rust';
} {
  const latestAttention = [...events].reverse().find((event) => ['FAILED', 'RECOVERING', 'HUMAN_REQUIRED'].includes(event.outcome));
  if (run.state === 'FAILED' || latestAttention?.outcome === 'FAILED') return { transport, run: 'Attention', tone: 'rust' };
  if (latestAttention?.outcome === 'HUMAN_REQUIRED' || run.state === 'REVIEW') return { transport, run: 'Review required', tone: 'olive' };
  if (latestAttention?.outcome === 'RECOVERING') return { transport, run: 'Recovering', tone: 'teal' };
  if (transport === 'ERROR') return { transport, run: run.state, tone: 'rust' };
  if (transport === 'LIVE') return { transport, run: run.state, tone: 'olive' };
  return { transport, run: run.state, tone: 'neutral' };
}

export function eventHasTerminalOutcome(event: RunEventDto): boolean {
  return TERMINAL_OUTCOMES.has(event.outcome);
}
