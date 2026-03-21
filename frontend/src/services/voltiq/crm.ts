import { request } from '@umijs/max';

export type OpportunityStage =
  | 'initial'
  | 'proposal'
  | 'negotiation'
  | 'won'
  | 'lost';

export type FollowUpItem = {
  id: string;
  lead_id: string;
  customer_id: string | null;
  content: string;
  next_action_at: string | null;
  created_by: string;
  created_at: string;
};

export type FollowUpListResult = {
  total: number;
  items: FollowUpItem[];
};

export type FollowUpListParams = {
  lead_id?: string;
  customer_id?: string;
  created_by?: string;
  created_at_start?: string;
  created_at_end?: string;
  limit?: number;
  offset?: number;
};

export type FollowUpCreatePayload = {
  lead_id: string;
  customer_id?: string;
  content: string;
  next_action_at?: string | null;
};

export type FollowUpUpdatePayload = {
  content?: string;
  next_action_at?: string | null;
};

export type OpportunityItem = {
  id: string;
  lead_id: string;
  customer_id: string | null;
  stage: OpportunityStage;
  amount_estimate: number | null;
  owner_user_id: string;
  created_at: string;
  updated_at: string;
};

export type OpportunityListResult = {
  total: number;
  items: OpportunityItem[];
};

export type OpportunityListParams = {
  lead_id?: string;
  customer_id?: string;
  stage?: OpportunityStage;
  updated_at_start?: string;
  updated_at_end?: string;
  limit?: number;
  offset?: number;
};

export type OpportunityCreatePayload = {
  lead_id: string;
  customer_id?: string;
  amount_estimate?: number;
};

export type OpportunityStageUpdatePayload = {
  stage: OpportunityStage;
  lost_reason?: string;
};

export type OpportunityStats = {
  opportunity_total: number;
  stage_counts: Record<OpportunityStage, number>;
  deal_count: number;
  deal_amount_sum: number;
};

export type DealItem = {
  id: string;
  opportunity_id: string;
  deal_amount: number;
  deal_date: string;
  created_by: string;
  created_at: string;
};

export type DealListResult = {
  total: number;
  items: DealItem[];
};

export type DealListParams = {
  opportunity_id?: string;
  deal_date_start?: string;
  deal_date_end?: string;
  limit?: number;
  offset?: number;
};

export type DealCreatePayload = {
  opportunity_id: string;
  deal_amount: number;
  deal_date: string;
};

export async function listFollowUps(params: FollowUpListParams) {
  return request<FollowUpListResult>('/crm/follow-ups', {
    method: 'GET',
    params,
  });
}

export async function createFollowUp(payload: FollowUpCreatePayload) {
  return request<FollowUpItem>('/crm/follow-ups', {
    method: 'POST',
    data: payload,
  });
}

export async function updateFollowUp(
  followUpId: string,
  payload: FollowUpUpdatePayload,
) {
  return request<FollowUpItem>(`/crm/follow-ups/${followUpId}`, {
    method: 'PATCH',
    data: payload,
  });
}

export async function deleteFollowUp(followUpId: string) {
  return request<void>(`/crm/follow-ups/${followUpId}`, {
    method: 'DELETE',
  });
}

export async function listOpportunities(params: OpportunityListParams) {
  return request<OpportunityListResult>('/crm/opportunities', {
    method: 'GET',
    params,
  });
}

export async function getOpportunityStats(
  params: Omit<OpportunityListParams, 'limit' | 'offset'>,
) {
  return request<OpportunityStats>('/crm/opportunities/stats', {
    method: 'GET',
    params,
  });
}

export async function createOpportunity(payload: OpportunityCreatePayload) {
  return request<OpportunityItem>('/crm/opportunities', {
    method: 'POST',
    data: payload,
  });
}

export async function updateOpportunityStage(
  opportunityId: string,
  payload: OpportunityStageUpdatePayload,
) {
  return request<OpportunityItem>(`/crm/opportunities/${opportunityId}/stage`, {
    method: 'PATCH',
    data: payload,
  });
}

export async function listDeals(params: DealListParams) {
  return request<DealListResult>('/crm/deals', {
    method: 'GET',
    params,
  });
}

export async function createDeal(payload: DealCreatePayload) {
  return request<DealItem>('/crm/deals', {
    method: 'POST',
    data: payload,
  });
}
