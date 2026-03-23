import { request } from '@umijs/max';

export type KbSessionItem = {
  id: string;
  user_id: string;
  session_key: string;
  created_at: string;
  updated_at: string;
};

export type KbSessionListResult = {
  total: number;
  items: KbSessionItem[];
};

export type KbSessionListParams = {
  limit?: number;
  offset?: number;
};

export type KbSourceRef = {
  position: number | null;
  dataset_id: string | null;
  dataset_name: string | null;
  document_id: string | null;
  document_name: string | null;
  segment_id: string | null;
  score: number | null;
  content: string | null;
};

export type KbChatPayload = {
  query: string;
  session_key?: string;
};

export type KbChatResponse = {
  session_key: string;
  conversation_id: string;
  message_id: string;
  answer: string;
  sources: KbSourceRef[];
};

export async function listKbSessions(params: KbSessionListParams) {
  return request<KbSessionListResult>('/kb/sessions', {
    method: 'GET',
    params,
  });
}

export async function chatWithKb(payload: KbChatPayload) {
  return request<KbChatResponse>('/kb/sessions/chat', {
    method: 'POST',
    data: payload,
  });
}
