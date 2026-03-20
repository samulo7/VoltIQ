import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../../_components/StepPlaceholder';

const KbSessionsPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="智能客服"
      description="智能客服对话与来源展示页面将在 Step 20 实现。"
      nextStepHint="当前页面用于验证 operator/manager 可见、sales 不可见。"
      actions={[
        { label: '查看客服模块', enabled: access.canKbRead },
      ]}
    />
  );
};

export default KbSessionsPage;
