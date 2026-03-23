import { PageContainer } from '@ant-design/pro-components';
import { useAccess } from '@umijs/max';
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  List,
  Row,
  Col,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import dayjs from 'dayjs';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  chatWithKb,
  listKbSessions,
  type KbChatResponse,
  type KbSessionItem,
  type KbSourceRef,
} from '@/services/voltiq/kb';

type QueryFormValues = {
  query: string;
};

type PaginationState = {
  current: number;
  pageSize: number;
  total: number;
};

type ChatMessageItem = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  sources?: KbSourceRef[];
  conversation_id?: string;
};

const DRAFT_SESSION_KEY = '__draft__';

const formatDateTime = (value?: string | null) => {
  if (!value) {
    return '-';
  }
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss');
};

const buildUserMessage = (query: string): ChatMessageItem => ({
  id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
  role: 'user',
  content: query,
  created_at: new Date().toISOString(),
});

const buildAssistantMessage = (response: KbChatResponse): ChatMessageItem => ({
  id: response.message_id,
  role: 'assistant',
  content: response.answer,
  created_at: new Date().toISOString(),
  sources: response.sources,
  conversation_id: response.conversation_id,
});

const KbSessionsPage: React.FC = () => {
  const access = useAccess();
  const [queryForm] = Form.useForm<QueryFormValues>();

  const [sessions, setSessions] = useState<KbSessionItem[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [pagination, setPagination] = useState<PaginationState>({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  const [activeSessionKey, setActiveSessionKey] = useState<string | undefined>();
  const [messagesBySession, setMessagesBySession] = useState<
    Record<string, ChatMessageItem[]>
  >({});
  const [sending, setSending] = useState(false);

  const activeStoreKey = activeSessionKey ?? DRAFT_SESSION_KEY;
  const activeMessages = useMemo(
    () => messagesBySession[activeStoreKey] ?? [],
    [messagesBySession, activeStoreKey],
  );

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const result = await listKbSessions({
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      });
      setSessions(result.items);
      setPagination((prev) => ({ ...prev, total: result.total }));
      setActiveSessionKey((prev) => prev ?? result.items[0]?.session_key);
    } finally {
      setSessionsLoading(false);
    }
  }, [pagination.current, pagination.pageSize]);

  useEffect(() => {
    void fetchSessions();
  }, [fetchSessions]);

  const appendMessage = useCallback((sessionKey: string, next: ChatMessageItem) => {
    setMessagesBySession((prev) => ({
      ...prev,
      [sessionKey]: [...(prev[sessionKey] ?? []), next],
    }));
  }, []);

  const handleSendQuery = useCallback(async () => {
    const query = queryForm.getFieldValue('query')?.trim();
    if (!query) {
      return;
    }

    const requestSessionKey = activeSessionKey;
    const requestStoreKey = requestSessionKey ?? DRAFT_SESSION_KEY;
    const userMessage = buildUserMessage(query);

    queryForm.setFieldsValue({ query: '' });
    appendMessage(requestStoreKey, userMessage);
    setSending(true);

    try {
      const response = await chatWithKb({
        query,
        session_key: requestSessionKey,
      });
      const responseSessionKey = response.session_key;
      const assistantMessage = buildAssistantMessage(response);

      setMessagesBySession((prev) => {
        const draftMessages = prev[requestStoreKey] ?? [];
        const targetHistory = prev[responseSessionKey] ?? [];
        const existingIds = new Set(targetHistory.map((item) => item.id));
        const mergedHistory = [...targetHistory];

        if (requestStoreKey !== responseSessionKey) {
          for (const item of draftMessages) {
            if (!existingIds.has(item.id)) {
              mergedHistory.push(item);
              existingIds.add(item.id);
            }
          }
        }

        return {
          ...prev,
          [responseSessionKey]: [...mergedHistory, assistantMessage],
          ...(requestStoreKey !== responseSessionKey
            ? { [requestStoreKey]: [] }
            : {}),
        };
      });

      setActiveSessionKey(responseSessionKey);
      await fetchSessions();
      message.success('已收到智能客服回答。');
    } finally {
      setSending(false);
    }
  }, [activeSessionKey, appendMessage, fetchSessions, queryForm]);

  if (!access.canKbRead) {
    return (
      <PageContainer title="智能客服">
        <Alert type="error" showIcon message="当前角色无权限访问智能客服页面。" />
      </PageContainer>
    );
  }

  return (
    <PageContainer title="智能客服">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Step 20：智能客服页面"
          description="支持会话列表、连续提问与回答依据展示。提示：当前后端未提供历史消息查询，切换历史会话后将从本次页面会话继续。"
        />

        <Row gutter={16}>
          <Col xs={24} lg={8}>
            <Card
              title="会话列表"
              extra={
                <Space>
                  <Button
                    onClick={() => {
                      setActiveSessionKey(undefined);
                    }}
                  >
                    新会话
                  </Button>
                  <Button
                    onClick={() => {
                      void fetchSessions();
                    }}
                  >
                    刷新
                  </Button>
                </Space>
              }
            >
              <List<KbSessionItem>
                loading={sessionsLoading}
                locale={{ emptyText: <Empty description="暂无会话" /> }}
                dataSource={sessions}
                pagination={{
                  current: pagination.current,
                  pageSize: pagination.pageSize,
                  total: pagination.total,
                  showSizeChanger: true,
                  pageSizeOptions: [10, 20, 50],
                  showTotal: (total) => `共 ${total} 条`,
                  onChange: (page, pageSize) => {
                    setPagination((prev) => ({
                      ...prev,
                      current: page,
                      pageSize,
                    }));
                  },
                }}
                renderItem={(item) => {
                  const selected = item.session_key === activeSessionKey;
                  return (
                    <List.Item
                      style={{
                        cursor: 'pointer',
                        borderRadius: 8,
                        background: selected ? '#f6ffed' : undefined,
                        paddingLeft: 8,
                        paddingRight: 8,
                      }}
                      onClick={() => {
                        setActiveSessionKey(item.session_key);
                      }}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            <Typography.Text copyable>{item.session_key}</Typography.Text>
                            {selected && <Tag color="success">当前会话</Tag>}
                          </Space>
                        }
                        description={`更新时间：${formatDateTime(item.updated_at)}`}
                      />
                    </List.Item>
                  );
                }}
              />
            </Card>
          </Col>

          <Col xs={24} lg={16}>
            <Card
              title="问答对话"
              extra={
                <Typography.Text type="secondary">
                  {activeSessionKey
                    ? `会话：${activeSessionKey}`
                    : '会话：新建中（首次提问后自动生成）'}
                </Typography.Text>
              }
            >
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Card
                  size="small"
                  bodyStyle={{
                    maxHeight: 520,
                    overflowY: 'auto',
                    background: '#fafafa',
                  }}
                >
                  {activeMessages.length === 0 ? (
                    <Empty description="暂无消息，请输入问题开始对话" />
                  ) : (
                    <Space direction="vertical" size={12} style={{ width: '100%' }}>
                      {activeMessages.map((item) => (
                        <Card
                          key={item.id}
                          size="small"
                          style={{
                            borderColor: item.role === 'assistant' ? '#b7eb8f' : '#91caff',
                          }}
                        >
                          <Space direction="vertical" size={8} style={{ width: '100%' }}>
                            <Space>
                              <Tag color={item.role === 'assistant' ? 'success' : 'processing'}>
                                {item.role === 'assistant' ? '智能客服' : '提问'}
                              </Tag>
                              <Typography.Text type="secondary">
                                {formatDateTime(item.created_at)}
                              </Typography.Text>
                            </Space>

                            <Typography.Paragraph
                              style={{
                                marginBottom: 0,
                                whiteSpace: 'pre-wrap',
                              }}
                            >
                              {item.content}
                            </Typography.Paragraph>

                            {item.role === 'assistant' && item.sources && item.sources.length > 0 && (
                              <Card size="small" type="inner" title="回答依据">
                                <List<KbSourceRef>
                                  size="small"
                                  dataSource={item.sources}
                                  renderItem={(source) => (
                                    <List.Item>
                                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                        <Space wrap>
                                          <Tag>
                                            {`#${source.position ?? '-'} ${source.dataset_name ?? '未知知识库'}`}
                                          </Tag>
                                          <Tag>{source.document_name ?? '未知文档'}</Tag>
                                          {typeof source.score === 'number' && (
                                            <Tag color="blue">score: {source.score.toFixed(4)}</Tag>
                                          )}
                                        </Space>
                                        <Typography.Paragraph
                                          style={{
                                            marginBottom: 0,
                                            whiteSpace: 'pre-wrap',
                                          }}
                                        >
                                          {source.content || '（无片段内容）'}
                                        </Typography.Paragraph>
                                      </Space>
                                    </List.Item>
                                  )}
                                />
                              </Card>
                            )}
                          </Space>
                        </Card>
                      ))}
                    </Space>
                  )}
                </Card>

                <Form
                  form={queryForm}
                  layout="vertical"
                  onFinish={() => {
                    void handleSendQuery();
                  }}
                >
                  <Form.Item
                    label="输入问题"
                    name="query"
                    rules={[
                      { required: true, message: '请输入问题' },
                      {
                        validator: async (_, value: string | undefined) => {
                          if (value && value.trim().length > 0) {
                            return;
                          }
                          throw new Error('请输入问题');
                        },
                      },
                    ]}
                    style={{ marginBottom: 12 }}
                  >
                    <Input.TextArea
                      rows={4}
                      maxLength={2000}
                      showCount
                      disabled={sending}
                      placeholder="例如：请解释售电合同中的直接交易定义，并给出依据。按 Enter 发送，Shift+Enter 换行。"
                      onPressEnter={(event) => {
                        if (!event.shiftKey) {
                          event.preventDefault();
                          void queryForm.submit();
                        }
                      }}
                    />
                  </Form.Item>

                  <Space>
                    <Button type="primary" htmlType="submit" loading={sending}>
                      发送问题
                    </Button>
                    <Button
                      onClick={() => {
                        queryForm.resetFields();
                      }}
                      disabled={sending}
                    >
                      清空输入
                    </Button>
                  </Space>
                </Form>
              </Space>
            </Card>
          </Col>
        </Row>
      </Space>
    </PageContainer>
  );
};

export default KbSessionsPage;
