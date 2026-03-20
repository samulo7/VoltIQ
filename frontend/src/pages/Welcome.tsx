import { PageContainer } from '@ant-design/pro-components';
import { useAccess, useModel } from '@umijs/max';
import { Alert, Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd';
import React from 'react';

const roleNameMap: Record<string, string> = {
  operator: '运营',
  sales: '销售',
  manager: '管理层',
};

const WelcomePage: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const access = useAccess();
  const role = initialState?.currentUser?.role || 'unknown';
  const roleName = roleNameMap[role] || role;

  const menuPermissions = [
    { label: '线索管理', enabled: access.canLeadRead },
    { label: '跟进记录', enabled: access.canFollowUpRead },
    { label: '商机管理', enabled: access.canOpportunityRead },
    { label: '成单记录', enabled: access.canDealRead },
    { label: '内容任务', enabled: access.canContentRead },
    { label: '智能客服', enabled: access.canKbRead },
    { label: '数据看板', enabled: access.canMetricsRead },
    { label: '审计日志', enabled: access.canAuditRead },
  ];

  const operationPermissions = [
    { label: '线索写入', enabled: access.canLeadWrite },
    { label: '跟进写入', enabled: access.canFollowUpWrite },
    { label: '商机流转', enabled: access.canOpportunityWrite },
    { label: '成单创建', enabled: access.canDealCreate },
    { label: '内容任务创建', enabled: access.canContentWrite },
  ];

  return (
    <PageContainer>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="success"
          showIcon
          message="Step 16 已接入登录与角色权限渲染"
          description="当前阶段仅提供权限骨架与菜单可见性，业务页面将按实施计划后续步骤逐步完成。"
        />
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="当前账号" value={initialState?.currentUser?.username || '-'} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="当前角色" value={roleName} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic
                title="可见菜单数量"
                value={menuPermissions.filter((item) => item.enabled).length}
              />
            </Card>
          </Col>
        </Row>
        <Card title="菜单可见性">
          <Space wrap size={[8, 12]}>
            {menuPermissions.map((item) => (
              <Tag key={item.label} color={item.enabled ? 'green' : 'default'}>
                {item.label}：{item.enabled ? '可见' : '隐藏'}
              </Tag>
            ))}
          </Space>
        </Card>
        <Card title="操作权限">
          <Space wrap size={[8, 12]}>
            {operationPermissions.map((item) => (
              <Tag key={item.label} color={item.enabled ? 'blue' : 'default'}>
                {item.label}：{item.enabled ? '可操作' : '不可操作'}
              </Tag>
            ))}
          </Space>
          <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
            Step 17 开始后，线索页面会基于这些权限接入真实接口操作。
          </Typography.Paragraph>
        </Card>
      </Space>
    </PageContainer>
  );
};

export default WelcomePage;
