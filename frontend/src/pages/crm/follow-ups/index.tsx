import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../../_components/StepPlaceholder';

const FollowUpsPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="跟进记录"
      description="CRM 跟进记录页面将在 Step 18 实现增删改查与实时刷新。"
      nextStepHint="当前仅验证角色权限渲染，业务页面尚未开始实现。"
      actions={[
        { label: '查看跟进记录', enabled: access.canFollowUpRead },
        { label: '新增/编辑跟进', enabled: access.canFollowUpWrite },
      ]}
    />
  );
};

export default FollowUpsPage;
