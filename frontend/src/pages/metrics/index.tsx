import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../_components/StepPlaceholder';

const MetricsPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="数据看板"
      description="线索/成单/转化率看板页面将在 Step 21 实现。"
      nextStepHint="当前页面用于验证 sales/manager 菜单可见性。"
      actions={[
        { label: '查看指标看板', enabled: access.canMetricsRead },
      ]}
    />
  );
};

export default MetricsPage;
