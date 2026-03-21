import { request } from '@umijs/max';

export type ContentTaskType = 'copywriting' | 'image' | 'video_script';

export type ContentTaskStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'failed';

export type ContentTaskItem = {
  id: string;
  task_type: ContentTaskType;
  prompt: string;
  status: ContentTaskStatus;
  result_text: string | null;
  result_meta: Record<string, unknown> | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type ContentTaskListResult = {
  total: number;
  items: ContentTaskItem[];
};

export type ContentTaskListParams = {
  task_type?: ContentTaskType;
  status?: ContentTaskStatus;
  created_by?: string;
  created_at_start?: string;
  created_at_end?: string;
  limit?: number;
  offset?: number;
};

export type ContentTaskCreatePayload = {
  task_type: ContentTaskType;
  prompt: string;
};

export async function createContentTask(payload: ContentTaskCreatePayload) {
  return request<ContentTaskItem>('/content/tasks', {
    method: 'POST',
    data: payload,
  });
}

export async function listContentTasks(params: ContentTaskListParams) {
  return request<ContentTaskListResult>('/content/tasks', {
    method: 'GET',
    params,
  });
}

export async function getContentTaskDetail(taskId: string) {
  return request<ContentTaskItem>(`/content/tasks/${taskId}`, {
    method: 'GET',
  });
}
