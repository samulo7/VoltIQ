import { PageContainer } from '@ant-design/pro-components';
import { useAccess } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
  Modal,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createDeal,
  createOpportunity,
  type OpportunityCreatePayload,
  type OpportunityItem,
  type OpportunityListParams,
  type OpportunityStage,
  type OpportunityStats,
  getOpportunityStats,
  listOpportunities,
  updateOpportunityStage,
} from '@/services/voltiq/crm';
import { type LeadItem, listLeads } from '@/services/voltiq/leads';

type OpportunityFilters = {
  lead_id?: string;
  customer_id?: string;
  stage?: OpportunityStage;
  updated_range?: [Dayjs, Dayjs];
};

type OpportunityCreateFormValues = {
  lead_id: string;
  customer_id?: string;
  amount_estimate?: number;
};

type LostFormValues = {
  lost_reason: string;
};

type DealCreateFormValues = {
  deal_amount: number;
  deal_date: Dayjs;
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

const STAGE_OPTIONS: Array<{ label: string; value: OpportunityStage }> = [
  { label: '初步接触', value: 'initial' },
  { label: '方案沟通', value: 'proposal' },
  { label: '商务谈判', value: 'negotiation' },
  { label: '已赢单', value: 'won' },
  { label: '已丢单', value: 'lost' },
];

const STAGE_TEXT: Record<OpportunityStage, string> = {
  initial: '初步接触',
  proposal: '方案沟通',
  negotiation: '商务谈判',
  won: '已赢单',
  lost: '已丢单',
};

const STAGE_COLOR: Record<OpportunityStage, string> = {
  initial: 'blue',
  proposal: 'gold',
  negotiation: 'orange',
  won: 'green',
  lost: 'default',
};

const STAGE_ORDER: OpportunityStage[] = [
  'initial',
  'proposal',
  'negotiation',
  'won',
  'lost',
];

const DEFAULT_STATS: OpportunityStats = {
  opportunity_total: 0,
  stage_counts: {
    initial: 0,
    proposal: 0,
    negotiation: 0,
    won: 0,
    lost: 0,
  },
  deal_count: 0,
  deal_amount_sum: 0,
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return '-';
  }
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
};

const getNextStage = (stage: OpportunityStage): OpportunityStage | null => {
  if (stage === 'initial') return 'proposal';
  if (stage === 'proposal') return 'negotiation';
  if (stage === 'negotiation') return 'lost';
  return null;
};

const OpportunitiesPage: React.FC = () => {
  const access = useAccess();
  const canWrite = access.canOpportunityWrite;
  const canDealCreate = access.canDealCreate;

  const [searchForm] = Form.useForm<OpportunityFilters>();
  const [createForm] = Form.useForm<OpportunityCreateFormValues>();
  const [lostForm] = Form.useForm<LostFormValues>();
  const [dealCreateForm] = Form.useForm<DealCreateFormValues>();

  const [filters, setFilters] = useState<OpportunityFilters>({});
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [items, setItems] = useState<OpportunityItem[]>([]);
  const [stats, setStats] = useState<OpportunityStats>(DEFAULT_STATS);
  const [loading, setLoading] = useState(false);

  const [leadOptions, setLeadOptions] = useState<SelectOption[]>([]);
  const [leadOptionsLoading, setLeadOptionsLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [lostOpen, setLostOpen] = useState(false);
  const [dealCreateOpen, setDealCreateOpen] = useState(false);
  const [activeOpportunity, setActiveOpportunity] = useState<OpportunityItem | null>(null);

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

  const buildFilterParams = useCallback(() => {
    const params: Omit<OpportunityListParams, 'limit' | 'offset'> = {};
    if (filters.lead_id) params.lead_id = filters.lead_id;
    if (filters.customer_id) params.customer_id = filters.customer_id;
    if (filters.stage) params.stage = filters.stage;
    if (filters.updated_range?.length === 2) {
      params.updated_at_start = filters.updated_range[0].startOf('day').toISOString();
      params.updated_at_end = filters.updated_range[1].endOf('day').toISOString();
    }
    return params;
  }, [filters]);

  const fetchOpportunities = useCallback(async () => {
    setLoading(true);
    try {
      const filterParams = buildFilterParams();
      const [listResult, statsResult] = await Promise.all([
        listOpportunities({
          ...filterParams,
          limit: pagination.pageSize,
          offset: (pagination.current - 1) * pagination.pageSize,
        }),
        getOpportunityStats(filterParams),
      ]);

      setItems(listResult.items);
      setPagination((prev) => ({ ...prev, total: listResult.total }));
      setStats({
        ...DEFAULT_STATS,
        ...statsResult,
        stage_counts: {
          ...DEFAULT_STATS.stage_counts,
          ...statsResult.stage_counts,
        },
      });
    } finally {
      setLoading(false);
    }
  }, [buildFilterParams, pagination.current, pagination.pageSize]);

  useEffect(() => {
    void loadLeadOptions();
  }, [loadLeadOptions]);

  useEffect(() => {
    void fetchOpportunities();
  }, [fetchOpportunities]);

  const handleSearch = (values: OpportunityFilters) => {
    setFilters({
      lead_id: values.lead_id || undefined,
      customer_id: values.customer_id?.trim() || undefined,
      stage: values.stage,
      updated_range:
        values.updated_range && values.updated_range.length === 2
          ? values.updated_range
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

  const handleCreateOpportunity = async () => {
    const values = await createForm.validateFields();
    const payload: OpportunityCreatePayload = {
      lead_id: values.lead_id,
      customer_id: values.customer_id?.trim() || undefined,
      amount_estimate: values.amount_estimate,
    };

    await createOpportunity(payload);
    message.success('商机创建成功');
    setCreateOpen(false);
    createForm.resetFields();
    await fetchOpportunities();
  };

  const handleAdvanceStage = async (
    opportunity: OpportunityItem,
    nextStage: OpportunityStage,
  ) => {
    await updateOpportunityStage(opportunity.id, { stage: nextStage });
    message.success(`阶段已更新为：${STAGE_TEXT[nextStage]}`);
    await fetchOpportunities();
  };

  const openLostModal = (opportunity: OpportunityItem) => {
    setActiveOpportunity(opportunity);
    lostForm.resetFields();
    setLostOpen(true);
  };

  const handleSetLost = async () => {
    if (!activeOpportunity) return;
    const values = await lostForm.validateFields();
    await updateOpportunityStage(activeOpportunity.id, {
      stage: 'lost',
      lost_reason: values.lost_reason.trim(),
    });
    message.success('商机已标记为丢单');
    setLostOpen(false);
    setActiveOpportunity(null);
    await fetchOpportunities();
  };

  const openDealCreateModal = (opportunity: OpportunityItem) => {
    setActiveOpportunity(opportunity);
    dealCreateForm.resetFields();
    dealCreateForm.setFieldsValue({
      deal_date: dayjs(),
    });
    setDealCreateOpen(true);
  };

  const handleCreateDeal = async () => {
    if (!activeOpportunity) return;
    const values = await dealCreateForm.validateFields();
    await createDeal({
      opportunity_id: activeOpportunity.id,
      deal_amount: values.deal_amount,
      deal_date: values.deal_date.format('YYYY-MM-DD'),
    });

    message.success('成单创建成功，商机已自动置为赢单');
    setDealCreateOpen(false);
    setActiveOpportunity(null);
    await fetchOpportunities();
  };

  const columns = useMemo<ColumnsType<OpportunityItem>>(
    () => [
      {
        title: '商机 ID',
        dataIndex: 'id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '线索 ID',
        dataIndex: 'lead_id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '阶段',
        dataIndex: 'stage',
        width: 120,
        render: (value: OpportunityStage) => (
          <Tag color={STAGE_COLOR[value]}>{STAGE_TEXT[value]}</Tag>
        ),
      },
      {
        title: '预计金额',
        dataIndex: 'amount_estimate',
        width: 140,
        render: (value: number | null) =>
          value === null ? '-' : value.toLocaleString('zh-CN', { maximumFractionDigits: 2 }),
      },
      {
        title: '负责人',
        dataIndex: 'owner_user_id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
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
        width: 280,
        render: (_, record) => {
          const nextStage = getNextStage(record.stage);

          return (
            <Space size={4} wrap>
              {canWrite && nextStage && nextStage !== 'lost' && (
                <Button
                  type="link"
                  onClick={() => {
                    void handleAdvanceStage(record, nextStage);
                  }}
                >
                  推进到{STAGE_TEXT[nextStage]}
                </Button>
              )}
              {canWrite && nextStage === 'lost' && (
                <Button type="link" onClick={() => openLostModal(record)}>
                  标记丢单
                </Button>
              )}
              {canDealCreate && record.stage === 'negotiation' && (
                <Button type="link" onClick={() => openDealCreateModal(record)}>
                  创建成单
                </Button>
              )}
              {!canWrite && <Tag>只读</Tag>}
            </Space>
          );
        },
      },
    ],
    [canDealCreate, canWrite],
  );

  return (
    <PageContainer title="商机管理">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Step 18：商机阶段流转"
          description="支持筛选、创建商机、阶段推进、丢单原因记录与商机内联创建成单。"
        />

        <Row gutter={16}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="商机总数" value={stats.opportunity_total} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="成单数" value={stats.deal_count} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic title="成单金额汇总" value={stats.deal_amount_sum} precision={2} />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="当前阶段分布"
                valueRender={() => (
                  <Space wrap>
                    {STAGE_ORDER.map((stage) => (
                      <Tag key={stage} color={STAGE_COLOR[stage]}>
                        {STAGE_TEXT[stage]} {stats.stage_counts[stage] ?? 0}
                      </Tag>
                    ))}
                  </Space>
                )}
              />
            </Card>
          </Col>
        </Row>

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
              <Form.Item label="阶段" name="stage" style={{ marginBottom: 0 }}>
                <Select
                  allowClear
                  options={STAGE_OPTIONS}
                  placeholder="全部阶段"
                  style={{ width: 160 }}
                />
              </Form.Item>
              <Form.Item label="更新时间" name="updated_range" style={{ marginBottom: 0 }}>
                <DatePicker.RangePicker showTime />
              </Form.Item>
            </Space>

            <Space style={{ marginTop: 12 }}>
              <Button type="primary" htmlType="submit">
                查询
              </Button>
              <Button onClick={handleResetSearch}>重置</Button>
              {canWrite && <Button onClick={openCreateModal}>新增商机</Button>}
            </Space>
          </Form>
        </Card>

        <Card>
          <Table<OpportunityItem>
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={items}
            scroll={{ x: 1600 }}
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
        title="新增商机"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => {
          void handleCreateOpportunity();
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
          <Form.Item label="预计金额（可选）" name="amount_estimate">
            <InputNumber
              min={0}
              precision={2}
              placeholder="如 50000"
              style={{ width: '100%' }}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="标记丢单"
        open={lostOpen}
        onCancel={() => {
          setLostOpen(false);
          setActiveOpportunity(null);
        }}
        onOk={() => {
          void handleSetLost();
        }}
        destroyOnClose
      >
        <Form form={lostForm} layout="vertical" preserve={false}>
          <Form.Item
            label="丢单原因"
            name="lost_reason"
            rules={[{ required: true, message: '请输入丢单原因' }]}
          >
            <Input.TextArea rows={4} maxLength={300} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="创建成单"
        open={dealCreateOpen}
        onCancel={() => {
          setDealCreateOpen(false);
          setActiveOpportunity(null);
        }}
        onOk={() => {
          void handleCreateDeal();
        }}
        destroyOnClose
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="仅谈判中商机可创建成单，创建后商机自动变更为赢单。"
        />
        <Form form={dealCreateForm} layout="vertical" preserve={false}>
          <Form.Item label="商机 ID">
            <Input value={activeOpportunity?.id} disabled />
          </Form.Item>
          <Form.Item
            label="成单金额"
            name="deal_amount"
            rules={[{ required: true, message: '请输入成单金额' }]}
          >
            <InputNumber min={0.01} precision={2} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            label="成单日期"
            name="deal_date"
            rules={[{ required: true, message: '请选择成单日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default OpportunitiesPage;
