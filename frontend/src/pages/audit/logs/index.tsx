import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../../_components/StepPlaceholder';

const AuditLogsPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="审计日志"
      description="审计检索页面将在 Step 22 实现按操作者/对象/时间查询。"
      nextStepHint="当前仅验证 manager 角色可见性。"
      actions={[
        { label: '查看审计日志', enabled: access.canAuditRead },
      ]}
    />
  );
};

export default AuditLogsPage;
