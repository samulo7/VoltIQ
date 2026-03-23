import { request } from '@umijs/max';

export type MetricsSummary = {
  lead_count: number;
  deal_count: number;
  effective_lead_count: number;
  conversion_rate: number;
};

export type MetricsDailyItem = {
  date: string;
  lead_count: number;
  deal_count: number;
  effective_lead_count: number;
  conversion_rate: number;
};

export type MetricsOverviewResponse = {
  timezone: string;
  start_date: string;
  end_date: string;
  summary: MetricsSummary;
  daily: MetricsDailyItem[];
};

export type MetricsOverviewParams = {
  start_date?: string;
  end_date?: string;
};

export async function getMetricsOverview(params: MetricsOverviewParams) {
  return request<MetricsOverviewResponse>('/metrics/overview', {
    method: 'GET',
    params,
  });
}
