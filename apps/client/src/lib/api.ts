import { fetch } from 'expo/fetch';
import { Platform } from 'react-native';
import { emitAuthenticationRequired } from './authSessionSignal';

export type MessageDto = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  status: string;
  created_at: string;
};

export type ProjectBindingStatus = 'PROJECT_BOUND' | 'HISTORICAL_UNBOUND';

export type ProjectDto = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  repository_ref: string | null;
  workspace_ref: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ProjectCreateRequest = {
  name: string;
  repository_ref?: string | null;
};

export type ConversationDto = {
  id: string;
  title: string;
  mode: 'reason' | 'code';
  status: string;
  spec_id: string;
  project_id: string | null;
  project_binding_status: ProjectBindingStatus;
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
  project_id: string | null;
  project_binding_status: ProjectBindingStatus;
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

export type AccessUserDto = {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  role: 'owner' | 'member';
  status: 'active' | 'revoked';
  auth_method: 'google' | 'bearer' | null;
  bound: boolean;
  created_at: string | null;
  updated_at: string | null;
  last_login_at: string | null;
};

export type ProjectCompatibilityResolver = {
  resolveCodeProject(): Promise<string>;
  invalidateProject(projectId: string, message: string): void;
  observeConversation(conversation: ConversationDto): void;
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
let projectCompatibilityResolver: ProjectCompatibilityResolver | null = null;

export class AuthenticationRequiredError extends Error {
  constructor(message = 'Private access required') {
    super(message);
    this.name = 'AuthenticationRequiredError';
    emitAuthenticationRequired();
  }
}
export class AuthorizationDeniedError extends Error {}
export class ApiRequestError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiRequestError';
  }
}

export function installProjectCompatibilityResolver(resolver: ProjectCompatibilityResolver): () => void {
  projectCompatibilityResolver = resolver;
  return () => {
    if (projectCompatibilityResolver === resolver) projectCompatibilityResolver = null;
  };
}

function observeConversation(conversation: ConversationDto | null | undefined): void {
  if (conversation) projectCompatibilityResolver?.observeConversation(conversation);
}

function requestCredentials(): RequestCredentials {
  return secureSessionTransport ? 'include' : 'same-origin';
}

function authenticatedHeaders(): Record<string, string> {
  return {
    ...(secureSessionTransport ? sessionHeaders : {}),
    ...(transientAccessToken ? { Authorization: `Bearer ${transientAccessToken}` } : {}),
  };
}

async function responseDetail(response: Response): Promise<string> {
  let detail = `Parallax API ${response.status}`;
  try {
    const payload = await response.json() as { detail?: string };
    if (typeof payload.detail === 'string' && payload.detail.trim()) detail = payload.detail;
  } catch {
    // Preserve the status fallback when the API did not return JSON.
  }
  return detail;
}

export async function authenticatedRequest(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: requestCredentials(),
    headers: { ...authenticatedHeaders(), ...(init?.headers ?? {}) },
  });
  if (response.status === 401) throw new AuthenticationRequiredError();
  if (response.status === 403) throw new AuthorizationDeniedError(await responseDetail(response));
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: requestCredentials(),
    headers: { 'Content-Type': 'application/json', ...authenticatedHeaders(), ...(init?.headers ?? {}) },
  });
  if (response.status === 401) throw new AuthenticationRequiredError();
  if (response.status === 403) throw new AuthorizationDeniedError(await responseDetail(response));
  if (!response.ok) throw new ApiRequestError(response.status, await responseDetail(response));
  return (await response.json()) as T;
}

async function establishSession(token: string): Promise<SessionDto> {
  const candidate = token.trim();
  if (!candidate) throw new AuthenticationRequiredError();

  const response = await fetch(`${apiBase}/v1/session`, {
    method: 'POST',
    credentials: requestCredentials(),
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${candidate}`,
    },
  });
  transientAccessToken = '';
  if (response.status === 401) throw new AuthenticationRequiredError();
  if (!response.ok) throw new ApiRequestError(response.status, await responseDetail(response));
  return (await response.json()) as SessionDto;
}

async function establishGoogleSession(accessToken: string): Promise<SessionDto> {
  const candidate = accessToken.trim();
  if (!candidate) throw new AuthenticationRequiredError('Google authentication required');

  const response = await fetch(`${apiBase}/v1/session/google`, {
    method: 'POST',
    credentials: requestCredentials(),
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${candidate}`,
    },
  });
  if (response.status === 401) throw new AuthenticationRequiredError(await responseDetail(response));
  if (response.status === 403) throw new AuthorizationDeniedError(await responseDetail(response));
  if (!response.ok) throw new ApiRequestError(response.status, await responseDetail(response));
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
  if (!response.ok) throw new ApiRequestError(response.status, await responseDetail(response));
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

  if (response.status === 401) throw new AuthenticationRequiredError();
  if (response.status === 403) throw new AuthorizationDeniedError(await responseDetail(response));
  if (!response.ok) throw new ApiRequestError(response.status, await responseDetail(response));
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

async function createConversation(mode: 'reason' | 'code'): Promise<ConversationDto> {
  let projectId: string | null = null;
  if (mode === 'code') {
    if (!projectCompatibilityResolver) {
      throw new Error('Select a Project before starting Code work.');
    }
    projectId = (await projectCompatibilityResolver.resolveCodeProject()).trim();
    if (!projectId) throw new Error('Select a Project before starting Code work.');
  }

  try {
    const conversation = await json<ConversationDto>('/v1/conversations', {
      method: 'POST',
      body: JSON.stringify(mode === 'code' ? { mode, project_id: projectId } : { mode }),
    });
    observeConversation(conversation);
    return conversation;
  } catch (error) {
    if (mode === 'code' && projectId && error instanceof ApiRequestError && [404, 422].includes(error.status)) {
      projectCompatibilityResolver?.invalidateProject(projectId, error.message);
    }
    throw error;
  }
}

async function getConversation(id: string): Promise<ConversationDto> {
  const conversation = await json<ConversationDto>(`/v1/conversations/${id}`);
  observeConversation(conversation);
  return conversation;
}

async function listConversations(): Promise<ConversationDto[]> {
  const conversations = await json<ConversationDto[]>('/v1/conversations');
  observeConversation(conversations[0]);
  return conversations;
}

export const api = {
  setAccessToken: (token: string) => { transientAccessToken = token.trim(); },
  establishSession,
  establishGoogleSession,
  getSession,
  endSession,
  currentAccessUser: () => json<AccessUserDto>('/v1/access/me'),
  listAccessUsers: () => json<AccessUserDto[]>('/v1/access/users'),
  addAccessUser: (email: string) => json<AccessUserDto>('/v1/access/users', {
    method: 'POST',
    body: JSON.stringify({ email }),
  }),
  updateAccessUserStatus: (id: string, status: 'active' | 'revoked') => json<AccessUserDto>(`/v1/access/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  }),
  listProjects: () => json<ProjectDto[]>('/v1/projects'),
  createProject: (request: ProjectCreateRequest) => json<ProjectDto>('/v1/projects', {
    method: 'POST',
    body: JSON.stringify({
      name: request.name,
      ...(request.repository_ref ? { repository_ref: request.repository_ref } : {}),
    }),
  }),
  createConversation,
  getConversation,
  listConversations,
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
  resumeApprovedScope: (conversationId: string) =>
    json<ConversationDto>(`/v1/conversations/${conversationId}/work-specifications/resume-approved-scope`, {
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
