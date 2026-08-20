export type MessageDto = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
};

export type ConversationDto = {
  id: string;
  title: string;
  mode: 'reason' | 'code';
  status: string;
  messages: MessageDto[];
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
};
