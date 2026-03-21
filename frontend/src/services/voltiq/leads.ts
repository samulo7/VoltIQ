import { request } from '@umijs/max';

export type LeadStatus = 'new' | 'contacted' | 'converted' | 'invalid';

export type LeadItem = {
  id: string;
  name: string;
  phone: string;
  company_name: string;
  source_channel: string;
  status: LeadStatus;
  owner_user_id: string;
  latest_follow_up_at: string | null;
  created_at: string;
  updated_at: string;
};

export type LeadListResult = {
  total: number;
  items: LeadItem[];
};

export type LeadListParams = {
  status?: LeadStatus;
  owner_user_id?: string;
  source_channel?: string;
  keyword?: string;
  created_at_start?: string;
  created_at_end?: string;
  limit?: number;
  offset?: number;
};

export type LeadCreatePayload = {
  name: string;
  phone: string;
  company_name: string;
  source_channel: string;
  owner_user_id?: string;
  status?: LeadStatus;
};

export type LeadUpdatePayload = {
  name?: string;
  phone?: string;
  company_name?: string;
  source_channel?: string;
  status?: LeadStatus;
};

export type LeadAssignPayload = {
  owner_user_id: string;
};

export type LeadMergePayload = {
  merged_payload: Record<string, unknown>;
  merge_reason: string;
};

export type LeadCreateResult = {
  action: 'created' | 'merged' | string;
  lead: LeadItem;
  merge_reason?: string | null;
};

export async function listLeads(params: LeadListParams) {
  return request<LeadListResult>('/leads', {
    method: 'GET',
    params,
  });
}

export async function getLeadDetail(leadId: string) {
  return request<LeadItem>(`/leads/${leadId}`, {
    method: 'GET',
  });
}

export async function createLead(payload: LeadCreatePayload) {
  return request<LeadCreateResult>('/leads', {
    method: 'POST',
    data: payload,
  });
}

export async function updateLead(leadId: string, payload: LeadUpdatePayload) {
  return request<LeadItem>(`/leads/${leadId}`, {
    method: 'PATCH',
    data: payload,
  });
}

export async function assignLeadOwner(leadId: string, payload: LeadAssignPayload) {
  return request<LeadItem>(`/leads/${leadId}/assign`, {
    method: 'POST',
    data: payload,
  });
}

export async function mergeLead(leadId: string, payload: LeadMergePayload) {
  return request<LeadCreateResult>(`/leads/${leadId}/merge`, {
    method: 'POST',
    data: payload,
  });
}
