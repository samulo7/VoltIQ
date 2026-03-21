import { PageContainer } from '@ant-design/pro-components';
import { useAccess } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Form,
  InputNumber,
  Select,
  Space,
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
  type DealCreatePayload,
  type DealItem,
  type DealListParams,
  listDeals,
  listOpportunities,
  type OpportunityItem,
  type OpportunityStage,
} from '@/services/voltiq/crm';

type DealFilters = {
  opportunity_id?: string;
  deal_date_range?: [Dayjs, Dayjs];
};

type DealCreateFormValues = {
  opportunity_id: string;
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
  stage: OpportunityStage;
};

const STAGE_TEXT: Record<OpportunityStage, string> = {
  initial: '初步接触',
  proposal: '方案沟通',
  negotiation: '商务谈判',
  won: '已赢单',
  lost: '已丢单',
};

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return '-';
  }
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
};

const DealsPage: React.FC = () => {
  const access = useAccess();
  const canCreate = access.canDealCreate;

  const [searchForm] = Form.useForm<DealFilters>();
  const [createForm] = Form.useForm<DealCreateFormValues>();

  const [filters, setFilters] = useState<DealFilters>({});
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [items, setItems] = useState<DealItem[]>([]);
  const [loading, setLoading] = useState(false);

  const [allOpportunityOptions, setAllOpportunityOptions] = useState<SelectOption[]>([]);
  const [negotiationOpportunityOptions, setNegotiationOpportunityOptions] = useState<
    SelectOption[]
  >([]);
  const [optionsLoading, setOptionsLoading] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);

  const loadOpportunityOptions = useCallback(async () => {
    setOptionsLoading(true);
    try {
      const [allResult, negotiationResult] = await Promise.all([
        listOpportunities({ limit: 100, offset: 0 }),
        listOpportunities({ stage: 'negotiation', limit: 100, offset: 0 }),
      ]);

      const mapToOption = (item: OpportunityItem): SelectOption => ({
        label: `${item.id.slice(0, 8)} | ${STAGE_TEXT[item.stage]} | lead:${item.lead_id.slice(0, 8)}`,
        value: item.id,
        stage: item.stage,
      });

      setAllOpportunityOptions(allResult.items.map(mapToOption));
      setNegotiationOpportunityOptions(negotiationResult.items.map(mapToOption));
    } finally {
      setOptionsLoading(false);
    }
  }, []);

  const fetchDeals = useCallback(async () => {
    setLoading(true);
    try {
      const params: DealListParams = {
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      };

      if (filters.opportunity_id) params.opportunity_id = filters.opportunity_id;
      if (filters.deal_date_range?.length === 2) {
        params.deal_date_start = filters.deal_date_range[0].format('YYYY-MM-DD');
        params.deal_date_end = filters.deal_date_range[1].format('YYYY-MM-DD');
      }

      const result = await listDeals(params);
      setItems(result.items);
      setPagination((prev) => ({ ...prev, total: result.total }));
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.current, pagination.pageSize]);

  useEffect(() => {
    void loadOpportunityOptions();
  }, [loadOpportunityOptions]);

  useEffect(() => {
    void fetchDeals();
  }, [fetchDeals]);

  const handleSearch = (values: DealFilters) => {
    setFilters({
      opportunity_id: values.opportunity_id || undefined,
      deal_date_range:
        values.deal_date_range && values.deal_date_range.length === 2
          ? values.deal_date_range
          : undefined,
    });
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const handleResetSearch = () => {
    searchForm.resetFields();
    setFilters({});
    setPagination((prev) => ({ ...prev, current: 1 }));
  };

  const openCreateModal = async () => {
    await loadOpportunityOptions();
    createForm.resetFields();
    if (negotiationOpportunityOptions.length > 0) {
      createForm.setFieldValue('opportunity_id', negotiationOpportunityOptions[0].value);
    }
    createForm.setFieldValue('deal_date', dayjs());
    setCreateOpen(true);
  };

  const handleCreateDeal = async () => {
    const values = await createForm.validateFields();
    const payload: DealCreatePayload = {
      opportunity_id: values.opportunity_id,
      deal_amount: values.deal_amount,
      deal_date: values.deal_date.format('YYYY-MM-DD'),
    };

    await createDeal(payload);
    message.success('成单创建成功');
    setCreateOpen(false);
    createForm.resetFields();
    await Promise.all([fetchDeals(), loadOpportunityOptions()]);
  };

  const columns = useMemo<ColumnsType<DealItem>>(
    () => [
      {
        title: '成单 ID',
        dataIndex: 'id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '商机 ID',
        dataIndex: 'opportunity_id',
        width: 240,
        render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
      },
      {
        title: '成单金额',
        dataIndex: 'deal_amount',
        width: 140,
        render: (value: number) =>
          value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
      },
      {
        title: '成单日期',
        dataIndex: 'deal_date',
        width: 130,
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
        title: '状态',
        key: 'status',
        width: 100,
        render: () => <Tag color="green">已成单</Tag>,
      },
    ],
    [],
  );

  return (
    <PageContainer title="成单记录">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Step 18：成单记录页面"
          description="支持成单列表与按谈判中商机创建成单，创建后可立即在列表中查询。"
        />

        <Card>
          <Form form={searchForm} layout="vertical" onFinish={handleSearch}>
            <Space size={12} wrap align="start">
              <Form.Item label="商机" name="opportunity_id" style={{ marginBottom: 0 }}>
                <Select
                  allowClear
                  showSearch
                  options={allOpportunityOptions}
                  loading={optionsLoading}
                  optionFilterProp="label"
                  placeholder="选择商机"
                  style={{ width: 420 }}
                />
              </Form.Item>
              <Form.Item label="成单日期" name="deal_date_range" style={{ marginBottom: 0 }}>
                <DatePicker.RangePicker />
              </Form.Item>
            </Space>

            <Space style={{ marginTop: 12 }}>
              <Button type="primary" htmlType="submit">
                查询
              </Button>
              <Button onClick={handleResetSearch}>重置</Button>
              {canCreate && <Button onClick={() => void openCreateModal()}>新增成单</Button>}
            </Space>
          </Form>
        </Card>

        <Card>
          <Table<DealItem>
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={items}
            scroll={{ x: 1340 }}
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
        title="新增成单"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => {
          void handleCreateDeal();
        }}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item
            label="商机"
            name="opportunity_id"
            rules={[{ required: true, message: '请选择商机' }]}
          >
            <Select
              showSearch
              options={negotiationOpportunityOptions}
              loading={optionsLoading}
              optionFilterProp="label"
              placeholder="仅展示 negotiation 商机"
            />
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

export default DealsPage;
