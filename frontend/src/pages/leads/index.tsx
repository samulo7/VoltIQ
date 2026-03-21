import { PageContainer } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
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
import type { AuthUser } from '@/services/voltiq/auth';
import {
  assignLeadOwner,
  createLead,
  type LeadCreateResult,
  type LeadItem,
  type LeadListParams,
  type LeadStatus,
  listLeads,
  mergeLead,
  updateLead,
} from '@/services/voltiq/leads';

type LeadFilters = {
  status?: LeadStatus;
  source_channel?: string;
  keyword?: string;
  owner_user_id?: string;
  created_range?: [Dayjs, Dayjs];
};

type PaginationState = {
  current: number;
  pageSize: number;
  total: number;
};

type LeadCreateFormValues = {
  name: string;
  phone: string;
  company_name: string;
  source_channel: string;
  status: LeadStatus;
  owner_user_id?: string;
};

type LeadUpdateFormValues = {
  name: string;
  phone: string;
  company_name: string;
  source_channel: string;
  status: LeadStatus;
};

type LeadAssignFormValues = {
  owner_user_id: string;
};

type LeadMergeFormValues = {
  merge_reason: string;
  merged_payload_json: string;
};

const STATUS_OPTIONS: Array<{ label: string; value: LeadStatus }> = [
  { label: '新线索', value: 'new' },
  { label: '已联系', value: 'contacted' },
  { label: '已转化', value: 'converted' },
  { label: '无效', value: 'invalid' },
];

const STATUS_COLOR: Record<LeadStatus, string> = {
  new: 'blue',
  contacted: 'gold',
  converted: 'green',
  invalid: 'default',
};

const STATUS_TEXT: Record<LeadStatus, string> = {
  new: '新线索',
  contacted: '已联系',
  converted: '已转化',
  invalid: '无效',
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return '-';
  }
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
};

const LeadsPage: React.FC = () => {
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const currentUser = initialState?.currentUser as AuthUser | undefined;
  const isOperator = currentUser?.role === 'operator';
  const canWrite = access.canLeadWrite;

  const [searchForm] = Form.useForm<LeadFilters>();
  const [createForm] = Form.useForm<LeadCreateFormValues>();
  const [updateForm] = Form.useForm<LeadUpdateFormValues>();
  const [assignForm] = Form.useForm<LeadAssignFormValues>();
  const [mergeForm] = Form.useForm<LeadMergeFormValues>();

  const [filters, setFilters] = useState<LeadFilters>({});
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [items, setItems] = useState<LeadItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [activeLead, setActiveLead] = useState<LeadItem | null>(null);
  const [lastCreateResult, setLastCreateResult] = useState<LeadCreateResult | null>(null);
  const [lastManualMergeResult, setLastManualMergeResult] = useState<LeadCreateResult | null>(null);
  const [lastManualMergeAt, setLastManualMergeAt] = useState<string | null>(null);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params: LeadListParams = {
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      };

      if (filters.status) params.status = filters.status;
      if (filters.source_channel) params.source_channel = filters.source_channel;
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.owner_user_id) params.owner_user_id = filters.owner_user_id;
      if (filters.created_range?.length === 2) {
        params.created_at_start = filters.created_range[0].startOf('day').toISOString();
        params.created_at_end = filters.created_range[1].endOf('day').toISOString();
      }

      const result = await listLeads(params);
      setItems(result.items);
      setPagination((prev) => ({ ...prev, total: result.total }));
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.current, pagination.pageSize]);

  useEffect(() => {
    void fetchLeads();
  }, [fetchLeads]);

  const openCreateModal = () => {
    createForm.resetFields();
    createForm.setFieldsValue({ status: 'new' });
    setCreateOpen(true);
  };

  const openUpdateModal = (record: LeadItem) => {
    setActiveLead(record);
    updateForm.setFieldsValue({
      name: record.name,
      phone: record.phone,
      company_name: record.company_name,
      source_channel: record.source_channel,
      status: record.status,
    });
    setUpdateOpen(true);
  };

  const openAssignModal = (record: LeadItem) => {
    setActiveLead(record);
    assignForm.setFieldsValue({ owner_user_id: record.owner_user_id });
    setAssignOpen(true);
  };

  const openMergeModal = (record: LeadItem) => {
    setActiveLead(record);
    mergeForm.setFieldsValue({
      merge_reason: 'manual_merge',
      merged_payload_json: JSON.stringify(
        {
          phone: record.phone,
          source_channel: record.source_channel,
        },
        null,
        2,
      ),
    });
    setMergeOpen(true);
  };

  const handleSearch = (values: LeadFilters) => {
    const nextFilters: LeadFilters = {
      status: values.status,
      source_channel: values.source_channel?.trim() || undefined,
      keyword: values.keyword?.trim() || undefined,
      owner_user_id: values.owner_user_id?.trim() || undefined,
      created_range:
        values.created_range && values.created_range.length === 2
          ? values.created_range
          : undefined,
    };
    setFilters(nextFilters);
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const handleResetSearch = () => {
    searchForm.resetFields();
    setFilters({});
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const handleCreateLead = async () => {
    const values = await createForm.validateFields();
    const payload = {
      name: values.name.trim(),
      phone: values.phone.trim(),
      company_name: values.company_name.trim(),
      source_channel: values.source_channel.trim(),
      status: values.status,
      owner_user_id: values.owner_user_id?.trim() || undefined,
    };

    if (!isOperator) {
      delete payload.owner_user_id;
    }

    const result = await createLead(payload);
    if (result.action === 'merged') {
      setLastCreateResult(result);
      message.warning(`命中去重并合并：${result.merge_reason ?? 'duplicate'}`);
    } else {
      setLastCreateResult(null);
      message.success('线索创建成功');
    }

    setCreateOpen(false);
    createForm.resetFields();
    await fetchLeads();
  };

  const handleUpdateLead = async () => {
    if (!activeLead) return;
    const values = await updateForm.validateFields();
    await updateLead(activeLead.id, {
      name: values.name.trim(),
      phone: values.phone.trim(),
      company_name: values.company_name.trim(),
      source_channel: values.source_channel.trim(),
      status: values.status,
    });
    message.success('线索更新成功');
    setUpdateOpen(false);
    setActiveLead(null);
    await fetchLeads();
  };

  const handleAssignLead = async () => {
    if (!activeLead) return;
    const values = await assignForm.validateFields();
    await assignLeadOwner(activeLead.id, {
      owner_user_id: values.owner_user_id.trim(),
    });
    message.success('负责人分配成功');
    setAssignOpen(false);
    setActiveLead(null);
    await fetchLeads();
  };

  const handleMergeLead = async () => {
    if (!activeLead) return;
    const values = await mergeForm.validateFields();

    let mergedPayload: Record<string, unknown>;
    try {
      mergedPayload = JSON.parse(values.merged_payload_json) as Record<string, unknown>;
    } catch {
      message.error('合并载荷必须是合法 JSON');
      return;
    }

    const result = await mergeLead(activeLead.id, {
      merge_reason: values.merge_reason.trim(),
      merged_payload: mergedPayload,
    });
    setLastManualMergeResult(result);
    setLastManualMergeAt(dayjs().format('YYYY-MM-DD HH:mm:ss'));
    message.success(`手动合并已记录：${result.lead.id}`);
    setMergeOpen(false);
    setActiveLead(null);
    await fetchLeads();
  };

  const columns = useMemo<ColumnsType<LeadItem>>(
    () => [
      {
        title: '姓名',
        dataIndex: 'name',
        width: 120,
      },
      {
        title: '手机号',
        dataIndex: 'phone',
        width: 140,
      },
      {
        title: '企业名称',
        dataIndex: 'company_name',
        ellipsis: true,
      },
      {
        title: '来源渠道',
        dataIndex: 'source_channel',
        width: 120,
      },
      {
        title: '状态',
        dataIndex: 'status',
        width: 110,
        render: (_, record) => (
          <Tag color={STATUS_COLOR[record.status]}>{STATUS_TEXT[record.status]}</Tag>
        ),
      },
      {
        title: '负责人',
        dataIndex: 'owner_user_id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '最近跟进',
        dataIndex: 'latest_follow_up_at',
        width: 180,
        render: (value: string | null) => formatDateTime(value),
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
        fixed: 'right',
        width: 260,
        render: (_, record) => (
          <Space size={4} wrap>
            {canWrite && (
              <Button type="link" onClick={() => openUpdateModal(record)}>
                编辑
              </Button>
            )}
            {isOperator && (
              <Button type="link" onClick={() => openAssignModal(record)}>
                分配
              </Button>
            )}
            {isOperator && (
              <Button type="link" onClick={() => openMergeModal(record)}>
                手动合并
              </Button>
            )}
          </Space>
        ),
      },
    ],
    [canWrite, isOperator],
  );

  return (
    <PageContainer title="线索管理">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        {lastCreateResult?.action === 'merged' && (
          <Alert
            showIcon
            type="warning"
            message="最近一次创建命中去重规则"
            description={`线索已合并到 ${lastCreateResult.lead.id}，原因：${
              lastCreateResult.merge_reason ?? 'duplicate'
            }`}
          />
        )}
        {lastManualMergeResult?.action === 'merged' && (
          <Alert
            showIcon
            type="success"
            message="最近一次手动合并已记录"
            description={`目标线索：${lastManualMergeResult.lead.id}，原因：${
              lastManualMergeResult.merge_reason ?? 'manual_merge'
            }，时间：${lastManualMergeAt ?? '-'}`}
            action={
              <Button
                type="text"
                size="small"
                onClick={() => {
                  setLastManualMergeResult(null);
                  setLastManualMergeAt(null);
                }}
              >
                关闭
              </Button>
            }
          />
        )}

        <Card>
          <Form form={searchForm} layout="vertical" onFinish={handleSearch}>
            <Space size={12} wrap align="start">
              <Form.Item label="关键词" name="keyword" style={{ marginBottom: 0 }}>
                <Input allowClear placeholder="姓名/企业名称" style={{ width: 220 }} />
              </Form.Item>
              <Form.Item label="状态" name="status" style={{ marginBottom: 0 }}>
                <Select
                  allowClear
                  options={STATUS_OPTIONS}
                  placeholder="全部状态"
                  style={{ width: 140 }}
                />
              </Form.Item>
              <Form.Item label="来源渠道" name="source_channel" style={{ marginBottom: 0 }}>
                <Input allowClear placeholder="如 wechat" style={{ width: 160 }} />
              </Form.Item>
              {isOperator && (
                <Form.Item
                  label="负责人 UUID"
                  name="owner_user_id"
                  style={{ marginBottom: 0 }}
                >
                  <Input allowClear placeholder="owner_user_id" style={{ width: 280 }} />
                </Form.Item>
              )}
              <Form.Item label="创建时间" name="created_range" style={{ marginBottom: 0 }}>
                <DatePicker.RangePicker />
              </Form.Item>
            </Space>

            <Space style={{ marginTop: 12 }}>
              <Button htmlType="submit" type="primary">
                查询
              </Button>
              <Button onClick={handleResetSearch}>重置</Button>
              {canWrite && <Button onClick={openCreateModal}>新增线索</Button>}
            </Space>
          </Form>
        </Card>

        <Card>
          <Table<LeadItem>
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={items}
            scroll={{ x: 1500 }}
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
        title="新增线索"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => {
          void handleCreateLead();
        }}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item label="姓名" name="name" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item
            label="手机号"
            name="phone"
            rules={[{ required: true, message: '请输入手机号' }]}
          >
            <Input maxLength={32} />
          </Form.Item>
          <Form.Item
            label="企业名称"
            name="company_name"
            rules={[{ required: true, message: '请输入企业名称' }]}
          >
            <Input maxLength={128} />
          </Form.Item>
          <Form.Item
            label="来源渠道"
            name="source_channel"
            rules={[{ required: true, message: '请输入来源渠道' }]}
          >
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          {isOperator && (
            <Form.Item
              label="负责人 UUID"
              name="owner_user_id"
              tooltip="留空则默认当前用户"
              rules={[
                {
                  pattern:
                    /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/,
                  message: '请输入合法 UUID，或留空',
                },
              ]}
            >
              <Input placeholder="如 d77487b2-faed-411a-871e-0f761b045812" />
            </Form.Item>
          )}
        </Form>
      </Modal>

      <Modal
        title="编辑线索"
        open={updateOpen}
        onCancel={() => {
          setUpdateOpen(false);
          setActiveLead(null);
        }}
        onOk={() => {
          void handleUpdateLead();
        }}
        destroyOnClose
      >
        <Form form={updateForm} layout="vertical" preserve={false}>
          <Form.Item label="姓名" name="name" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item
            label="手机号"
            name="phone"
            rules={[{ required: true, message: '请输入手机号' }]}
          >
            <Input maxLength={32} />
          </Form.Item>
          <Form.Item
            label="企业名称"
            name="company_name"
            rules={[{ required: true, message: '请输入企业名称' }]}
          >
            <Input maxLength={128} />
          </Form.Item>
          <Form.Item
            label="来源渠道"
            name="source_channel"
            rules={[{ required: true, message: '请输入来源渠道' }]}
          >
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="分配负责人"
        open={assignOpen}
        onCancel={() => {
          setAssignOpen(false);
          setActiveLead(null);
        }}
        onOk={() => {
          void handleAssignLead();
        }}
        destroyOnClose
      >
        <Alert
          style={{ marginBottom: 12 }}
          type="info"
          showIcon
          message="当前版本使用 UUID 手动输入分配负责人"
        />
        <Form form={assignForm} layout="vertical" preserve={false}>
          <Form.Item
            label="负责人 UUID"
            name="owner_user_id"
            rules={[
              { required: true, message: '请输入负责人 UUID' },
              {
                pattern:
                  /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$/,
                message: '请输入合法 UUID',
              },
            ]}
          >
            <Input placeholder="如 d77487b2-faed-411a-871e-0f761b045812" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="手动合并"
        open={mergeOpen}
        onCancel={() => {
          setMergeOpen(false);
          setActiveLead(null);
        }}
        onOk={() => {
          void handleMergeLead();
        }}
        destroyOnClose
      >
        <Alert
          style={{ marginBottom: 12 }}
          type="warning"
          showIcon
          message="手动合并会写入 lead_merge_logs 与审计日志"
        />
        <Form form={mergeForm} layout="vertical" preserve={false}>
          <Form.Item
            label="合并原因"
            name="merge_reason"
            rules={[{ required: true, message: '请输入合并原因' }]}
          >
            <Input maxLength={64} />
          </Form.Item>
          <Form.Item
            label="合并载荷 (JSON)"
            name="merged_payload_json"
            rules={[{ required: true, message: '请输入 JSON 载荷' }]}
          >
            <Input.TextArea rows={8} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default LeadsPage;
