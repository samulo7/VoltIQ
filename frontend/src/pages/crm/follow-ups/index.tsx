import { PageContainer } from '@ant-design/pro-components';
import { useAccess } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createFollowUp,
  deleteFollowUp,
  type FollowUpCreatePayload,
  type FollowUpItem,
  type FollowUpListParams,
  listFollowUps,
  updateFollowUp,
} from '@/services/voltiq/crm';
import { type LeadItem, listLeads } from '@/services/voltiq/leads';

type FollowUpFilters = {
  lead_id?: string;
  customer_id?: string;
  created_by?: string;
  created_range?: [Dayjs, Dayjs];
};

type FollowUpCreateFormValues = {
  lead_id: string;
  customer_id?: string;
  content: string;
  next_action_at?: Dayjs;
};

type FollowUpUpdateFormValues = {
  content: string;
  next_action_at?: Dayjs;
};

type PaginationState = {
  current: number;
  pageSize: number;
  total: number;
};

type SelectOption = {
  label: string;
  value: string;
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return '-';
  }
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
};

const FollowUpsPage: React.FC = () => {
  const access = useAccess();
  const canWrite = access.canFollowUpWrite;

  const [searchForm] = Form.useForm<FollowUpFilters>();
  const [createForm] = Form.useForm<FollowUpCreateFormValues>();
  const [updateForm] = Form.useForm<FollowUpUpdateFormValues>();

  const [filters, setFilters] = useState<FollowUpFilters>({});
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [items, setItems] = useState<FollowUpItem[]>([]);
  const [loading, setLoading] = useState(false);

  const [leadOptions, setLeadOptions] = useState<SelectOption[]>([]);
  const [leadOptionsLoading, setLeadOptionsLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [activeItem, setActiveItem] = useState<FollowUpItem | null>(null);

  const loadLeadOptions = useCallback(async (keyword?: string) => {
    setLeadOptionsLoading(true);
    try {
      const leadResult = await listLeads({
        keyword: keyword?.trim() || undefined,
        limit: 100,
        offset: 0,
      });
      setLeadOptions(
        leadResult.items.map((lead: LeadItem) => ({
          label: `${lead.name} | ${lead.company_name} | ${lead.id.slice(0, 8)}`,
          value: lead.id,
        })),
      );
    } finally {
      setLeadOptionsLoading(false);
    }
  }, []);

  const fetchFollowUps = useCallback(async () => {
    setLoading(true);
    try {
      const params: FollowUpListParams = {
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      };

      if (filters.lead_id) params.lead_id = filters.lead_id;
      if (filters.customer_id) params.customer_id = filters.customer_id;
      if (filters.created_by) params.created_by = filters.created_by;
      if (filters.created_range?.length === 2) {
        params.created_at_start = filters.created_range[0].startOf('day').toISOString();
        params.created_at_end = filters.created_range[1].endOf('day').toISOString();
      }

      const result = await listFollowUps(params);
      setItems(result.items);
      setPagination((prev) => ({ ...prev, total: result.total }));
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.current, pagination.pageSize]);

  useEffect(() => {
    void loadLeadOptions();
  }, [loadLeadOptions]);

  useEffect(() => {
    void fetchFollowUps();
  }, [fetchFollowUps]);

  const handleSearch = (values: FollowUpFilters) => {
    setFilters({
      lead_id: values.lead_id || undefined,
      customer_id: values.customer_id?.trim() || undefined,
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
    createForm.resetFields();
    if (leadOptions.length > 0) {
      createForm.setFieldValue('lead_id', leadOptions[0].value);
    }
    setCreateOpen(true);
  };

  const openUpdateModal = (item: FollowUpItem) => {
    setActiveItem(item);
    updateForm.setFieldsValue({
      content: item.content,
      next_action_at: item.next_action_at ? dayjs(item.next_action_at) : undefined,
    });
    setUpdateOpen(true);
  };

  const handleCreateFollowUp = async () => {
    const values = await createForm.validateFields();
    const payload: FollowUpCreatePayload = {
      lead_id: values.lead_id,
      content: values.content.trim(),
      customer_id: values.customer_id?.trim() || undefined,
      next_action_at: values.next_action_at
        ? values.next_action_at.toISOString()
        : undefined,
    };

    await createFollowUp(payload);
    message.success('跟进记录创建成功');
    setCreateOpen(false);
    createForm.resetFields();
    await fetchFollowUps();
  };

  const handleUpdateFollowUp = async () => {
    if (!activeItem) return;
    const values = await updateForm.validateFields();

    await updateFollowUp(activeItem.id, {
      content: values.content.trim(),
      next_action_at: values.next_action_at
        ? values.next_action_at.toISOString()
        : null,
    });

    message.success('跟进记录更新成功');
    setUpdateOpen(false);
    setActiveItem(null);
    await fetchFollowUps();
  };

  const handleDeleteFollowUp = (item: FollowUpItem) => {
    Modal.confirm({
      title: '确认删除该跟进记录？',
      content: '删除后将重算线索最近跟进时间。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteFollowUp(item.id);
        message.success('跟进记录已删除');
        await fetchFollowUps();
      },
    });
  };

  const columns = useMemo<ColumnsType<FollowUpItem>>(
    () => [
      {
        title: '内容',
        dataIndex: 'content',
        ellipsis: true,
      },
      {
        title: '线索 ID',
        dataIndex: 'lead_id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '客户 ID',
        dataIndex: 'customer_id',
        width: 240,
        render: (value: string | null) =>
          value ? <Typography.Text copyable>{value}</Typography.Text> : '-',
      },
      {
        title: '下次行动',
        dataIndex: 'next_action_at',
        width: 180,
        render: (value: string | null) => formatDateTime(value),
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
        title: '操作',
        key: 'actions',
        width: 140,
        fixed: 'right',
        render: (_, record) => (
          <Space size={4}>
            {canWrite && (
              <Button type="link" onClick={() => openUpdateModal(record)}>
                编辑
              </Button>
            )}
            {canWrite && (
              <Button type="link" danger onClick={() => handleDeleteFollowUp(record)}>
                删除
              </Button>
            )}
            {!canWrite && <Tag>只读</Tag>}
          </Space>
        ),
      },
    ],
    [canWrite],
  );

  return (
    <PageContainer title="跟进记录">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Step 18：跟进记录页面"
          description="支持新增、查询、编辑、删除；新增和删除后自动刷新列表。"
        />

        <Card>
          <Form form={searchForm} layout="vertical" onFinish={handleSearch}>
            <Space size={12} wrap align="start">
              <Form.Item label="线索" name="lead_id" style={{ marginBottom: 0 }}>
                <Select
                  allowClear
                  showSearch
                  placeholder="选择线索"
                  loading={leadOptionsLoading}
                  options={leadOptions}
                  optionFilterProp="label"
                  onSearch={(value) => {
                    void loadLeadOptions(value);
                  }}
                  style={{ width: 360 }}
                />
              </Form.Item>
              <Form.Item label="客户 ID" name="customer_id" style={{ marginBottom: 0 }}>
                <Input allowClear placeholder="customer_id" style={{ width: 260 }} />
              </Form.Item>
              <Form.Item label="创建人 ID" name="created_by" style={{ marginBottom: 0 }}>
                <Input allowClear placeholder="created_by" style={{ width: 260 }} />
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
              {canWrite && <Button onClick={openCreateModal}>新增跟进</Button>}
            </Space>
          </Form>
        </Card>

        <Card>
          <Table<FollowUpItem>
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={items}
            scroll={{ x: 1480 }}
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
      </Space>

      <Modal
        title="新增跟进"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => {
          void handleCreateFollowUp();
        }}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item
            label="线索"
            name="lead_id"
            rules={[{ required: true, message: '请选择线索' }]}
          >
            <Select
              showSearch
              placeholder="选择线索"
              loading={leadOptionsLoading}
              options={leadOptions}
              optionFilterProp="label"
              onSearch={(value) => {
                void loadLeadOptions(value);
              }}
            />
          </Form.Item>
          <Form.Item label="客户 ID（可选）" name="customer_id">
            <Input placeholder="若填写需与线索归属一致" />
          </Form.Item>
          <Form.Item
            label="跟进内容"
            name="content"
            rules={[{ required: true, message: '请输入跟进内容' }]}
          >
            <Input.TextArea rows={4} maxLength={2000} />
          </Form.Item>
          <Form.Item label="下次行动时间" name="next_action_at">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑跟进"
        open={updateOpen}
        onCancel={() => {
          setUpdateOpen(false);
          setActiveItem(null);
        }}
        onOk={() => {
          void handleUpdateFollowUp();
        }}
        destroyOnClose
      >
        <Form form={updateForm} layout="vertical" preserve={false}>
          <Form.Item
            label="跟进内容"
            name="content"
            rules={[{ required: true, message: '请输入跟进内容' }]}
          >
            <Input.TextArea rows={4} maxLength={2000} />
          </Form.Item>
          <Form.Item label="下次行动时间" name="next_action_at">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default FollowUpsPage;
