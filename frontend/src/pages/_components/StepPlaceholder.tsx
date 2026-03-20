import { PageContainer } from '@ant-design/pro-components';
import { Alert, Card, Space, Tag, Typography } from 'antd';
import React from 'react';

type ActionState = {
  label: string;
  enabled: boolean;
};

type StepPlaceholderProps = {
  title: string;
  description: string;
  nextStepHint: string;
  actions: ActionState[];
};

const StepPlaceholder: React.FC<StepPlaceholderProps> = ({
  title,
  description,
  nextStepHint,
  actions,
}) => {
  return (
    <PageContainer title={title}>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert
          type="info"
          showIcon
          message="Step 16 已完成登录与角色权限渲染"
          description={nextStepHint}
        />
        <Card>
          <Typography.Paragraph>{description}</Typography.Paragraph>
          <Space wrap>
            {actions.map((action) => (
              <Tag key={action.label} color={action.enabled ? 'green' : 'default'}>
                {action.label}：{action.enabled ? '可操作' : '不可操作'}
              </Tag>
            ))}
          </Space>
        </Card>
      </Space>
    </PageContainer>
  );
};

export default StepPlaceholder;
