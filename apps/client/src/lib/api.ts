import { fetch } from 'expo/fetch';

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

const apiBase = process.env.EXPO_PUBLIC_PARALLAX_API_URL ?? 'http://localhost:8010';

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    throw new Error(`Parallax API ${response.status}`);
  }
  return (await response.json()) as T;
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
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ content, material_scope_change: materialScopeChange }),
  });

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
      throw new Error(typeof event.data.error === 'string' ? event.data.error : 'Parallax response failed');
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
  streamResponse,
};
