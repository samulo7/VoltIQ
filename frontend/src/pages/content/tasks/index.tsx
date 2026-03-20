import { useAccess } from '@umijs/max';
import React from 'react';
import StepPlaceholder from '../../_components/StepPlaceholder';

const ContentTasksPage: React.FC = () => {
  const access = useAccess();
  return (
    <StepPlaceholder
      title="内容任务"
      description="内容生成任务页面将在 Step 19 实现三类任务提交与结果展示。"
      nextStepHint="当前仅提供权限可见性校验入口。"
      actions={[
        { label: '查看任务', enabled: access.canContentRead },
        { label: '创建任务', enabled: access.canContentWrite },
      ]}
    />
  );
};

export default ContentTasksPage;
