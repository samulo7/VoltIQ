import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../../_components/StepPlaceholder';

const OpportunitiesPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="商机管理"
      description="商机阶段流转页面将在 Step 18 实现，包含阶段变更与详情联动。"
      nextStepHint="当前页面用于验证角色菜单与操作可见性。"
      actions={[
        { label: '查看商机', enabled: access.canOpportunityRead },
        { label: '推进阶段', enabled: access.canOpportunityWrite },
      ]}
    />
  );
};

export default OpportunitiesPage;
