import { fetch } from 'expo/fetch';
import { Platform } from 'react-native';

export type MessageDto = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  status: string;
  created_at: string;
};

export type ConversationDto = {
  id: string;
  title: string;
  mode: 'reason' | 'code';
  status: string;
  spec_id: string;
  created_at: string;
  updated_at: string;
  messages: MessageDto[];
};

export type WorkSpecificationDto = {
  id: string;
  conversation_id: string;
  revision: number;
  status: 'DRAFT' | 'APPROVED' | 'SUPERSEDED';
  title: string;
  objective: string;
  constraints: string[];
  acceptance_criteria: string[];
  risks: string[];
  open_questions: string[];
  confidence: number;
  program_version: string;
  model_id: string | null;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
};

export type ResponsePhase =
  | 'THINKING'
  | 'RESPONDING'
  | 'VERIFYING'
  | 'COMPLETE'
  | 'ERROR'
  | 'SPEC_AMENDMENT';

export type ResponseStreamEvent = {
  event: 'state' | 'chunk' | 'complete' | 'amendment' | 'error';
  data: Record<string, unknown>;
};

export type ResponseResult = {
  text: string;
  messageId: string | null;
  confidence: number | null;
  trace: Record<string, unknown> | null;
  phase: 'COMPLETE' | 'SPEC_AMENDMENT';
  scopeDecision: string | null;
};

export type EngineeringAttemptDto = {
  id: string;
  stage: string;
  attempt_number: number;
  status: string;
  failure_code: string | null;
  evidence: Record<string, unknown>;
  started_at: string;
  completed_at: string;
};

export type EngineeringAcceptanceCriterionDto = {
  id: string;
  text: string;
};

export type EngineeringRunDto = {
  id: string;
  conversation_id: string;
  spec_id: string;
  work_specification_id: string | null;
  work_specification_revision: number | null;
  work_specification_digest: string | null;
  binding_status: 'APPROVED_SPEC_BOUND' | 'HISTORICAL_UNBOUND';
  acceptance_criteria: EngineeringAcceptanceCriterionDto[];
  state: string;
  resume_stage: string | null;
  revision: number;
  workspace_ref: string | null;
  last_failure_code: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  attempts: EngineeringAttemptDto[];
};

export type SessionDto = {
  authenticated: boolean;
  expires_at?: string;
};

const configuredApiBase = process.env.EXPO_PUBLIC_PARALLAX_API_URL ?? 'http://localhost:8010';
const hostedHttpsWeb = Platform.OS === 'web'
  && typeof globalThis.location !== 'undefined'
  && globalThis.location.protocol === 'https:';
const secureSessionTransport = hostedHttpsWeb || configuredApiBase.startsWith('https://');
const apiBase = hostedHttpsWeb
  ? '/p2-api'
  : Platform.OS === 'web' && configuredApiBase.startsWith('https://')
    ? '/p2-api'
    : configuredApiBase;
const sessionHeaders = { 'X-Parallax-Session': '1' } as const;
let transientAccessToken = '';

export class AuthenticationRequiredError extends Error {}

function requestCredentials(): RequestCredentials {
  return secureSessionTransport ? 'include' : 'same-origin';
}

function authenticatedHeaders(): Record<string, string> {
  return {
    ...(secureSessionTransport ? sessionHeaders : {}),
    ...(transientAccessToken ? { Authorization: `Bearer ${transientAccessToken}` } : {}),
  };
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: requestCredentials(),
    headers: { 'Content-Type': 'application/json', ...authenticatedHeaders(), ...(init?.headers ?? {}) },
  });
  if (response.status === 401) throw new AuthenticationRequiredError('Private access required');
  if (!response.ok) {
    let detail = `Parallax API ${response.status}`;
    try {
      const payload = await response.json() as { detail?: string };
      if (typeof payload.detail === 'string' && payload.detail.trim()) detail = payload.detail;
    } catch {
      // Preserve the status fallback when the API did not return JSON.
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

async function establishSession(token: string): Promise<SessionDto> {
  const candidate = token.trim();
  if (!candidate) throw new AuthenticationRequiredError('Private access required');

  const response = await fetch(`${apiBase}/v1/session`, {
    method: 'POST',
    credentials: requestCredentials(),
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${candidate}`,
    },
  });
  transientAccessToken = '';
  if (response.status === 401) throw new AuthenticationRequiredError('Private access required');
  if (!response.ok) throw new Error(`Parallax API ${response.status}`);
  return (await response.json()) as SessionDto;
}

async function getSession(): Promise<SessionDto> {
  if (!secureSessionTransport) return { authenticated: true };
  return json<SessionDto>('/v1/session');
}

async function endSession(): Promise<SessionDto> {
  transientAccessToken = '';
  if (!secureSessionTransport) return { authenticated: false };
  const response = await fetch(`${apiBase}/v1/session`, {
    method: 'DELETE',
    credentials: requestCredentials(),
    headers: { ...sessionHeaders },
  });
  if (!response.ok) throw new Error(`Parallax API ${response.status}`);
  return (await response.json()) as SessionDto;
}

function decodeEvent(block: string): ResponseStreamEvent | null {
  let eventName = 'message';
  const dataLines: string[] = [];

  for (const rawLine of block.split(/\r?\n/)) {
    if (rawLine.startsWith('event:')) eventName = rawLine.slice(6).trim();
    if (rawLine.startsWith('data:')) dataLines.push(rawLine.slice(5).trimStart());
  }

  if (!dataLines.length) return null;
  if (!['state', 'chunk', 'complete', 'amendment', 'error'].includes(eventName)) return null;

  const parsed = JSON.parse(dataLines.join('\n')) as Record<string, unknown>;
  return { event: eventName as ResponseStreamEvent['event'], data: parsed };
}

async function streamResponse(
  id: string,
  content: string,
  onEvent?: (event: ResponseStreamEvent) => void,
  materialScopeChange = false,
): Promise<ResponseResult> {
  const response = await fetch(`${apiBase}/v1/conversations/${id}/responses`, {
    method: 'POST',
    credentials: requestCredentials(),
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...authenticatedHeaders(),
    },
    body: JSON.stringify({ content, material_scope_change: materialScopeChange }),
  });

  if (response.status === 401) throw new AuthenticationRequiredError('Private access required');
  if (!response.ok) throw new Error(`Parallax API ${response.status}`);
  if (!response.body) throw new Error('Parallax response stream unavailable');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let text = '';
  let messageId: string | null = null;
  let confidence: number | null = null;
  let trace: Record<string, unknown> | null = null;
  let phase: ResponseResult['phase'] = 'COMPLETE';
  let scopeDecision: string | null = null;

  const handle = (event: ResponseStreamEvent) => {
    onEvent?.(event);
    if (event.event === 'chunk' && typeof event.data.text === 'string') {
      text += event.data.text;
    }
    if (event.event === 'complete' || event.event === 'amendment') {
      if (typeof event.data.message_id === 'string') messageId = event.data.message_id;
      if (typeof event.data.confidence === 'number') confidence = event.data.confidence;
      if (typeof event.data.scope_decision === 'string') scopeDecision = event.data.scope_decision;
      if (event.data.trace && typeof event.data.trace === 'object') {
        trace = event.data.trace as Record<string, unknown>;
      }
      if (event.event === 'amendment') {
        phase = 'SPEC_AMENDMENT';
        if (typeof event.data.text === 'string') text = event.data.text;
      }
    }
    if (event.event === 'error') {
      const message = typeof event.data.message === 'string'
        ? event.data.message
        : typeof event.data.error === 'string'
          ? event.data.error
          : 'Parallax response failed';
      throw new Error(message);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? '';
    for (const block of blocks) {
      const event = decodeEvent(block.trim());
      if (event) handle(event);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    const event = decodeEvent(buffer.trim());
    if (event) handle(event);
  }

  return { text, messageId, confidence, trace, phase, scopeDecision };
}

export const api = {
  setAccessToken: (token: string) => { transientAccessToken = token.trim(); },
  establishSession,
  getSession,
  endSession,
  createConversation: (mode: 'reason' | 'code') =>
    json<ConversationDto>('/v1/conversations', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),
  getConversation: (id: string) => json<ConversationDto>(`/v1/conversations/${id}`),
  listConversations: () => json<ConversationDto[]>('/v1/conversations'),
  appendMessage: (id: string, role: 'user' | 'assistant', content: string) =>
    json<MessageDto>(`/v1/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ role, content }),
    }),
  latestWorkSpecification: (conversationId: string) =>
    json<WorkSpecificationDto | null>(`/v1/conversations/${conversationId}/work-specifications/latest`),
  latestApprovedWorkSpecification: (conversationId: string) =>
    json<WorkSpecificationDto | null>(`/v1/conversations/${conversationId}/work-specifications/approved`),
  draftWorkSpecification: (conversationId: string) =>
    json<WorkSpecificationDto>(`/v1/conversations/${conversationId}/work-specifications/draft`, {
      method: 'POST',
    }),
  approveWorkSpecification: (specificationId: string) =>
    json<WorkSpecificationDto>(`/v1/work-specifications/${specificationId}/approve`, {
      method: 'POST',
    }),
  streamResponse,
  latestEngineeringRun: (conversationId: string) =>
    json<EngineeringRunDto | null>(`/v1/engineering-runs/conversation/${conversationId}/latest`),
  activateEngineeringRun: (conversationId: string, workSpecificationId?: string | null) =>
    json<EngineeringRunDto>('/v1/engineering-runs/activate', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        ...(workSpecificationId ? { work_specification_id: workSpecificationId } : {}),
      }),
    }),
  pauseEngineeringRun: (run: EngineeringRunDto, operationKey: string) =>
    json<{ run: EngineeringRunDto }>(`/v1/engineering-runs/${run.id}/pause`, {
      method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
  resumeEngineeringRun: (run: EngineeringRunDto, operationKey: string) =>
    json<{ run: EngineeringRunDto }>(`/v1/engineering-runs/${run.id}/resume`, {
      method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
  cancelEngineeringRun: (run: EngineeringRunDto, operationKey: string) =>
    json<{ run: EngineeringRunDto }>(`/v1/engineering-runs/${run.id}/cancel`, {
      method: 'POST', body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
    }),
};
