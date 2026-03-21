import { PageContainer } from '@ant-design/pro-components';
import { useAccess } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createContentTask,
  getContentTaskDetail,
  type ContentTaskCreatePayload,
  type ContentTaskItem,
  type ContentTaskListParams,
  type ContentTaskStatus,
  type ContentTaskType,
  listContentTasks,
} from '@/services/voltiq/content';

type ContentTaskFilters = {
  task_type?: ContentTaskType;
  status?: ContentTaskStatus;
  created_by?: string;
  created_range?: [Dayjs, Dayjs];
};

type ContentTaskCreateFormValues = {
  task_type: ContentTaskType;
  prompt: string;
};

type PaginationState = {
  current: number;
  pageSize: number;
  total: number;
};

const TASK_TYPE_TEXT: Record<ContentTaskType, string> = {
  copywriting: '文案',
  image: '图片',
  video_script: '短视频脚本',
};

const TASK_TYPE_OPTIONS: Array<{ label: string; value: ContentTaskType }> = [
  { label: '文案', value: 'copywriting' },
  { label: '图片', value: 'image' },
  { label: '短视频脚本', value: 'video_script' },
];

const STATUS_TEXT: Record<ContentTaskStatus, string> = {
  pending: '待处理',
  running: '执行中',
  succeeded: '已成功',
  failed: '已失败',
};

const STATUS_COLOR: Record<ContentTaskStatus, string> = {
  pending: 'default',
  running: 'processing',
  succeeded: 'success',
  failed: 'error',
};

const STATUS_OPTIONS: Array<{ label: string; value: ContentTaskStatus }> = [
  { label: '待处理', value: 'pending' },
  { label: '执行中', value: 'running' },
  { label: '已成功', value: 'succeeded' },
  { label: '已失败', value: 'failed' },
];

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return '-';
  }
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
};

const ContentTasksPage: React.FC = () => {
  const access = useAccess();
  const canWrite = access.canContentWrite;

  const [searchForm] = Form.useForm<ContentTaskFilters>();
  const [createForm] = Form.useForm<ContentTaskCreateFormValues>();

  const [filters, setFilters] = useState<ContentTaskFilters>({});
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [items, setItems] = useState<ContentTaskItem[]>([]);
  const [loading, setLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createPhase, setCreatePhase] = useState<'idle' | 'submitting' | 'done'>('idle');
  const [lastSubmittedTask, setLastSubmittedTask] = useState<ContentTaskItem | null>(
    null,
  );

  const [activeTask, setActiveTask] = useState<ContentTaskItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchContentTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params: ContentTaskListParams = {
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      };

      if (filters.task_type) params.task_type = filters.task_type;
      if (filters.status) params.status = filters.status;
      if (filters.created_by) params.created_by = filters.created_by;
      if (filters.created_range?.length === 2) {
        params.created_at_start = filters.created_range[0].startOf('day').toISOString();
        params.created_at_end = filters.created_range[1].endOf('day').toISOString();
      }

      const result = await listContentTasks(params);
      setItems(result.items);
      setPagination((prev) => ({ ...prev, total: result.total }));
      setActiveTask((current) => {
        if (!current) {
          return current;
        }
        const updatedTask = result.items.find((item) => item.id === current.id);
        return updatedTask ?? current;
      });
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.current, pagination.pageSize]);

  useEffect(() => {
    void fetchContentTasks();
  }, [fetchContentTasks]);

  const handleSearch = (values: ContentTaskFilters) => {
    setFilters({
      task_type: values.task_type,
      status: values.status,
      created_by: values.created_by?.trim() || undefined,
      created_range:
        values.created_range && values.created_range.length === 2
          ? values.created_range
          : undefined,
    });
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const handleResetSearch = () => {
    searchForm.resetFields();
    setFilters({});
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const openCreateModal = () => {
    createForm.setFieldsValue({
      task_type: 'copywriting',
      prompt: '',
    });
    setCreateOpen(true);
  };

  const handleCreateTask = async () => {
    if (!canWrite) {
      return;
    }

    const values = await createForm.validateFields();
    const payload: ContentTaskCreatePayload = {
      task_type: values.task_type,
      prompt: values.prompt.trim(),
    };

    setCreating(true);
    setCreatePhase('submitting');
    try {
      const createdTask = await createContentTask(payload);
      setLastSubmittedTask(createdTask);
      setActiveTask(createdTask);
      setCreatePhase('done');
      message.success(`任务创建成功，当前状态：${STATUS_TEXT[createdTask.status]}`);
      setCreateOpen(false);
      createForm.resetFields();
      await fetchContentTasks();
    } finally {
      setCreating(false);
    }
  };

  const handleViewDetail = async (taskId: string) => {
    setDetailLoading(true);
    try {
      const detail = await getContentTaskDetail(taskId);
      setActiveTask(detail);
    } finally {
      setDetailLoading(false);
    }
  };

  const columns = useMemo<ColumnsType<ContentTaskItem>>(
    () => [
      {
        title: '任务 ID',
        dataIndex: 'id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '任务类型',
        dataIndex: 'task_type',
        width: 130,
        render: (value: ContentTaskType) => <Tag>{TASK_TYPE_TEXT[value]}</Tag>,
      },
      {
        title: '状态',
        dataIndex: 'status',
        width: 120,
        render: (value: ContentTaskStatus) => (
          <Tag color={STATUS_COLOR[value]}>{STATUS_TEXT[value]}</Tag>
        ),
      },
      {
        title: 'Prompt',
        dataIndex: 'prompt',
        ellipsis: true,
      },
      {
        title: '创建人',
        dataIndex: 'created_by',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        width: 180,
        render: (value: string) => formatDateTime(value),
      },
      {
        title: '更新时间',
        dataIndex: 'updated_at',
        width: 180,
        render: (value: string) => formatDateTime(value),
      },
      {
        title: '操作',
        key: 'actions',
        width: 100,
        fixed: 'right',
        render: (_, record) => (
          <Button
            type="link"
            onClick={() => {
              void handleViewDetail(record.id);
            }}
          >
            查看结果
          </Button>
        ),
      },
    ],
    [],
  );

  return (
    <PageContainer title="内容任务">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Step 19：内容任务页面"
          description="支持三类任务提交、筛选分页、结果查看与前端提交过渡态。"
        />

        {createPhase === 'submitting' && (
          <Alert
            type="warning"
            showIcon
            message="任务提交中"
            description="正在等待接口返回任务状态，请稍候。"
          />
        )}

        {createPhase === 'done' && lastSubmittedTask && (
          <Alert
            type="success"
            showIcon
            message="最近一次提交完成"
            description={`任务类型：${TASK_TYPE_TEXT[lastSubmittedTask.task_type]}；当前状态：${STATUS_TEXT[lastSubmittedTask.status]}。`}
          />
        )}

        <Card>
          <Form form={searchForm} layout="vertical" onFinish={handleSearch}>
            <Space size={12} wrap align="start">
              <Form.Item label="任务类型" name="task_type" style={{ marginBottom: 0 }}>
                <Select
                  allowClear
                  placeholder="全部类型"
                  options={TASK_TYPE_OPTIONS}
                  style={{ width: 180 }}
                />
              </Form.Item>
              <Form.Item label="状态" name="status" style={{ marginBottom: 0 }}>
                <Select
                  allowClear
                  placeholder="全部状态"
                  options={STATUS_OPTIONS}
                  style={{ width: 180 }}
                />
              </Form.Item>
              <Form.Item label="创建人 ID" name="created_by" style={{ marginBottom: 0 }}>
                <Input allowClear placeholder="created_by" style={{ width: 280 }} />
              </Form.Item>
              <Form.Item label="创建时间" name="created_range" style={{ marginBottom: 0 }}>
                <DatePicker.RangePicker showTime />
              </Form.Item>
            </Space>

            <Space style={{ marginTop: 12 }}>
              <Button type="primary" htmlType="submit">
                查询
              </Button>
              <Button onClick={handleResetSearch}>重置</Button>
              {canWrite && <Button onClick={openCreateModal}>新建任务</Button>}
            </Space>
          </Form>
        </Card>

        <Card>
          <Table<ContentTaskItem>
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={items}
            scroll={{ x: 1620 }}
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              total: pagination.total,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条`,
            }}
            onChange={(nextPagination) => {
              setPagination((prev) => ({
                ...prev,
                current: nextPagination.current ?? prev.current,
                pageSize: nextPagination.pageSize ?? prev.pageSize,
              }));
            }}
          />
        </Card>

        <Card loading={detailLoading} title="任务结果详情">
          {!activeTask ? (
            <Typography.Text type="secondary">请从列表中点击“查看结果”。</Typography.Text>
          ) : (
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Space wrap>
                <Tag>{TASK_TYPE_TEXT[activeTask.task_type]}</Tag>
                <Tag color={STATUS_COLOR[activeTask.status]}>{STATUS_TEXT[activeTask.status]}</Tag>
                <Typography.Text type="secondary">
                  更新时间：{formatDateTime(activeTask.updated_at)}
                </Typography.Text>
              </Space>
              <Typography.Paragraph>
                <Typography.Text strong>Prompt：</Typography.Text>
                {activeTask.prompt}
              </Typography.Paragraph>
              <Typography.Paragraph>
                <Typography.Text strong>结果文本：</Typography.Text>
              </Typography.Paragraph>
              <Typography.Paragraph
                style={{
                  whiteSpace: 'pre-wrap',
                  background: '#fafafa',
                  padding: 12,
                  borderRadius: 8,
                }}
              >
                {activeTask.result_text || '（无）'}
              </Typography.Paragraph>
              <Typography.Paragraph>
                <Typography.Text strong>结果元数据：</Typography.Text>
              </Typography.Paragraph>
              <Typography.Paragraph
                style={{
                  whiteSpace: 'pre-wrap',
                  background: '#fafafa',
                  padding: 12,
                  borderRadius: 8,
                  marginBottom: 0,
                }}
              >
                {activeTask.result_meta
                  ? JSON.stringify(activeTask.result_meta, null, 2)
                  : '（无）'}
              </Typography.Paragraph>
            </Space>
          )}
        </Card>
      </Space>

      <Modal
        title="新建内容任务"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => {
          void handleCreateTask();
        }}
        okButtonProps={{ loading: creating }}
        confirmLoading={creating}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item
            label="任务类型"
            name="task_type"
            rules={[{ required: true, message: '请选择任务类型' }]}
          >
            <Select options={TASK_TYPE_OPTIONS} />
          </Form.Item>
          <Form.Item
            label="Prompt"
            name="prompt"
            rules={[
              { required: true, message: '请输入任务描述' },
              { min: 1, message: '请输入任务描述' },
            ]}
          >
            <Input.TextArea rows={6} maxLength={5000} showCount />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default ContentTasksPage;
