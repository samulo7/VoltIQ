import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../../_components/StepPlaceholder';

const DealsPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="成单记录"
      description="成单录入与查询页面将在 Step 18 实现，与商机流转联动。"
      nextStepHint="当前仅展示角色级可见性与操作权限差异。"
      actions={[
        { label: '查看成单', enabled: access.canDealRead },
        { label: '创建成单', enabled: access.canDealCreate },
      ]}
    />
  );
};

export default DealsPage;
