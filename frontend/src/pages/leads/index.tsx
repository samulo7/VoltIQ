import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../_components/StepPlaceholder';

const LeadsPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="线索管理"
      description="线索列表、筛选、编辑、分配与去重结果展示将在 Step 17 实现。"
      nextStepHint="等待你验证 Step 16 后再启动 Step 17。"
      actions={[
        { label: '查看线索菜单', enabled: access.canLeadRead },
        { label: '新增/编辑线索', enabled: access.canLeadWrite },
      ]}
    />
  );
};

export default LeadsPage;
