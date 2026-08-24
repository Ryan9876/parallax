import { RunEventCursor, type RunEventIdentity } from '../state/runEventCursor';

export type RunTransportState = 'CONNECTING' | 'LIVE' | 'RECONNECTING' | 'CLOSED' | 'ERROR';

export type RunEventDto = RunEventIdentity & {
  project_id: string;
  event_key: string;
  event_type: string;
  stage: string | null;
  outcome: string;
  subsystem: string;
  attempt_id: string | null;
  worker_execution_id: string | null;
  source_lineage_ref: string | null;
  parent_source_lineage_ref: string | null;
  operation_ref: string | null;
  artifact_ref: string | null;
  evidence_ref: string | null;
  failure_code: string | null;
  summary: string | null;
  metadata: Record<string, unknown>;
  occurred_at: string;
  created_at: string;
};

export type RunEventPageDto = {
  events: RunEventDto[];
  next_after_sequence: number;
  has_more: boolean;
};

export type SourceTreeDto = {
  project_id: string;
  run_id: string;
  lineage_id: string;
  parent_lineage_id: string | null;
  content_digest: string;
  source_kind: string;
  file_count: number;
  total_bytes: number;
  files: Array<{ path: string; sha256: string; size: number }>;
  next_offset: number;
  has_more: boolean;
};

export type SourceFileDto = {
  project_id: string;
  run_id: string;
  lineage_id: string;
  path: string;
  sha256: string;
  size: number;
  availability: 'TEXT' | 'BINARY' | 'TOO_LARGE';
  text: string | null;
};

export type SourceDiffDto = {
  project_id: string;
  run_id: string;
  from_lineage: string;
  to_lineage: string;
  unchanged_count: number;
  changed_count: number;
  files: Array<{
    path: string;
    change_type: 'ADDED' | 'REMOVED' | 'MODIFIED';
    from_sha256: string | null;
    from_size: number | null;
    to_sha256: string | null;
    to_size: number | null;
    availability: 'TEXT' | 'BINARY' | 'TOO_LARGE';
    diff_text: string | null;
    truncated: boolean;
  }>;
  truncated: boolean;
};

export type AttemptEvidenceDto = {
  project_id: string;
  run_id: string;
  attempt_id: string;
  stage: 'BUILD' | 'TEST' | 'VERIFY';
  attempt_number: number;
  status: string;
  program_id: string | null;
  model_id: string | null;
  tool_id: string | null;
  failure_code: string | null;
  started_at: string;
  completed_at: string;
  availability: 'AVAILABLE' | 'UNAVAILABLE' | 'REDACTED';
  evidence: Record<string, unknown>;
};

export type AuthenticatedRunRequest = (path: string, init?: RequestInit) => Promise<Response>;

function encode(value: string): string {
  return encodeURIComponent(value);
}

async function requireJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`Parallax observability request failed (${response.status})`);
  return await response.json() as T;
}

function decodeSseBlock(block: string, runId: string): RunEventDto | null {
  if (!block.trim() || block.trimStart().startsWith(':')) return null;
  let id = '';
  let eventName = 'message';
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('id:')) id = line.slice(3).trim();
    else if (line.startsWith('event:')) eventName = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (eventName !== 'run-event' || !/^[1-9][0-9]*$/.test(id) || data.length === 0) return null;
  const parsed = JSON.parse(data.join('\n')) as RunEventDto;
  const sequence = Number(id);
  if (!Number.isSafeInteger(sequence) || parsed.sequence !== sequence || parsed.run_id !== runId) return null;
  return parsed;
}

export class RunObservabilityClient {
  readonly cursor = new RunEventCursor();

  constructor(private readonly request: AuthenticatedRunRequest) {}

  async replay(runId: string, limit = 100): Promise<RunEventDto[]> {
    const after = this.cursor.last(runId);
    const response = await this.request(
      `/v1/engineering-runs/${encode(runId)}/events?after_sequence=${after}&limit=${limit}`,
      { method: 'GET' },
    );
    const page = await requireJson<RunEventPageDto>(response);
    const accepted: RunEventDto[] = [];
    for (const event of page.events) {
      if (this.cursor.accept(runId, event)) accepted.push(event);
    }
    return accepted;
  }

  async stream(
    runId: string,
    onEvent: (event: RunEventDto) => void,
    onState?: (state: RunTransportState) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const previous = this.cursor.last(runId);
    onState?.(previous > 0 ? 'RECONNECTING' : 'CONNECTING');
    try {
      const response = await this.request(`/v1/engineering-runs/${encode(runId)}/events/stream`, {
        method: 'GET',
        signal,
        headers: {
          Accept: 'text/event-stream',
          ...(previous > 0 ? { 'Last-Event-ID': String(previous) } : {}),
        },
      });
      if (!response.ok || !response.body) {
        throw new Error(`Parallax run-event stream unavailable (${response.status})`);
      }
      onState?.('LIVE');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split(/\r?\n\r?\n/);
        buffer = blocks.pop() ?? '';
        for (const block of blocks) {
          const event = decodeSseBlock(block, runId);
          if (event && this.cursor.accept(runId, event)) onEvent(event);
        }
      }
      buffer += decoder.decode();
      if (buffer.trim()) {
        const event = decodeSseBlock(buffer, runId);
        if (event && this.cursor.accept(runId, event)) onEvent(event);
      }
      onState?.('CLOSED');
    } catch (error) {
      if (signal?.aborted) {
        onState?.('CLOSED');
        return;
      }
      onState?.('ERROR');
      throw error;
    }
  }

  async sourceTree(runId: string, lineageId: string, offset = 0, limit = 100): Promise<SourceTreeDto> {
    return requireJson<SourceTreeDto>(await this.request(
      `/v1/engineering-runs/${encode(runId)}/source/${encode(lineageId)}/tree?offset=${offset}&limit=${limit}`,
      { method: 'GET' },
    ));
  }

  async sourceFile(runId: string, lineageId: string, path: string): Promise<SourceFileDto> {
    return requireJson<SourceFileDto>(await this.request(
      `/v1/engineering-runs/${encode(runId)}/source/${encode(lineageId)}/file?path=${encode(path)}`,
      { method: 'GET' },
    ));
  }

  async sourceDiff(runId: string, fromLineage: string, toLineage: string): Promise<SourceDiffDto> {
    return requireJson<SourceDiffDto>(await this.request(
      `/v1/engineering-runs/${encode(runId)}/source-diff?from_lineage=${encode(fromLineage)}&to_lineage=${encode(toLineage)}`,
      { method: 'GET' },
    ));
  }

  async attemptEvidence(runId: string, attemptId: string): Promise<AttemptEvidenceDto> {
    return requireJson<AttemptEvidenceDto>(await this.request(
      `/v1/engineering-runs/${encode(runId)}/attempts/${encode(attemptId)}/evidence`,
      { method: 'GET' },
    ));
  }
}
