import { PageContainer } from '@ant-design/pro-components';
import { useAccess } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Form,
  Row,
  Space,
  Statistic,
  Table,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getMetricsOverview,
  type MetricsDailyItem,
  type MetricsOverviewResponse,
} from '@/services/voltiq/metrics';

type MetricsFilters = {
  date_range?: [Dayjs, Dayjs];
};

const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;

const extractErrorMessage = (error: unknown): string => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }
  return '数据看板加载失败，请稍后重试。';
};

const todayRange = (): [Dayjs, Dayjs] => {
  const today = dayjs();
  return [today, today];
};

const MetricsPage: React.FC = () => {
  const access = useAccess();
  const [searchForm] = Form.useForm<MetricsFilters>();

  const [filters, setFilters] = useState<MetricsFilters>({
    date_range: todayRange(),
  });
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [overview, setOverview] = useState<MetricsOverviewResponse | null>(null);

  const fetchOverview = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const dateRange = filters.date_range;
      const params =
        dateRange && dateRange.length === 2
          ? {
              start_date: dateRange[0].format('YYYY-MM-DD'),
              end_date: dateRange[1].format('YYYY-MM-DD'),
            }
          : {};
      const response = await getMetricsOverview(params);
      setOverview(response);
    } catch (error) {
      setOverview(null);
      setErrorMessage(extractErrorMessage(error));
    } finally {
      setLoading(false);
    }
  }, [filters.date_range]);

  useEffect(() => {
    void fetchOverview();
  }, [fetchOverview]);

  const handleSearch = (values: MetricsFilters) => {
    setFilters({
      date_range:
        values.date_range && values.date_range.length === 2
          ? values.date_range
          : undefined,
    });
  };

  const handleReset = () => {
    const nextRange = todayRange();
    searchForm.setFieldsValue({ date_range: nextRange });
    setFilters({ date_range: nextRange });
  };

  const columns = useMemo<ColumnsType<MetricsDailyItem>>(
    () => [
      {
        title: '日期',
        dataIndex: 'date',
        width: 120,
      },
      {
        title: '新增线索数',
        dataIndex: 'lead_count',
        width: 140,
      },
      {
        title: '有效线索数',
        dataIndex: 'effective_lead_count',
        width: 140,
      },
      {
        title: '成单数',
        dataIndex: 'deal_count',
        width: 120,
      },
      {
        title: '转化率',
        dataIndex: 'conversion_rate',
        width: 120,
        render: (value: number) => formatPercent(value),
      },
    ],
    [],
  );

  if (!access.canMetricsRead) {
    return (
      <PageContainer title="数据看板">
        <Alert type="error" showIcon message="当前角色无权限访问数据看板页面。" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="数据看板">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Step 21：基础数据看板"
          description="展示线索、有效线索、成单与转化率，数据口径与后端 /metrics/overview 保持一致。"
        />

        <Card>
          <Form
            form={searchForm}
            layout="vertical"
            initialValues={{ date_range: todayRange() }}
            onFinish={handleSearch}
          >
            <Space align="end" size={12} wrap>
              <Form.Item label="统计日期范围" name="date_range" style={{ marginBottom: 0 }}>
                <DatePicker.RangePicker allowClear={false} />
              </Form.Item>
              <Form.Item style={{ marginBottom: 0 }}>
                <Space>
                  <Button htmlType="submit" type="primary">
                    查询
                  </Button>
                  <Button onClick={handleReset}>重置为今日</Button>
                  <Button
                    onClick={() => {
                      void fetchOverview();
                    }}
                  >
                    刷新
                  </Button>
                </Space>
              </Form.Item>
            </Space>
          </Form>
        </Card>

        {errorMessage && (
          <Alert
            type="error"
            showIcon
            message="看板加载失败"
            description={errorMessage}
            action={
              <Button
                size="small"
                onClick={() => {
                  void fetchOverview();
                }}
              >
                重试
              </Button>
            }
          />
        )}

        <Row gutter={16}>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic
                title="新增线索"
                value={overview?.summary.lead_count ?? 0}
                valueStyle={{ color: '#1677ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic
                title="有效线索"
                value={overview?.summary.effective_lead_count ?? 0}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic
                title="成单数"
                value={overview?.summary.deal_count ?? 0}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} xl={6}>
            <Card loading={loading}>
              <Statistic
                title="转化率"
                value={overview ? formatPercent(overview.summary.conversion_rate) : '0.00%'}
              />
            </Card>
          </Col>
        </Row>

        <Card
          title="按日明细"
          extra={
            <Typography.Text type="secondary">
              时区：{overview?.timezone ?? 'Asia/Shanghai'}
            </Typography.Text>
          }
        >
          {!loading && !errorMessage && (overview?.daily.length ?? 0) === 0 ? (
            <Empty description="当前条件下暂无看板数据" />
          ) : (
            <Table<MetricsDailyItem>
              rowKey="date"
              columns={columns}
              dataSource={overview?.daily ?? []}
              loading={loading}
              pagination={{
                defaultPageSize: 14,
                showSizeChanger: true,
                pageSizeOptions: [14, 30, 60],
                showTotal: (total) => `共 ${total} 条`,
              }}
              scroll={{ x: 700 }}
            />
          )}
        </Card>
      </Space>
    </PageContainer>
  );
};

export default MetricsPage;
