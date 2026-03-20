export default [
  {
    path: '/user',
    layout: false,
    routes: [
      {
        name: 'login',
        path: '/user/login',
        component: './user/login',
      },
    ],
  },
  {
    path: '/welcome',
    name: '首页',
    icon: 'home',
    component: './Welcome',
  },
  {
    path: '/leads',
    name: '线索管理',
    icon: 'team',
    access: 'canLeadRead',
    component: './leads',
  },
  {
    path: '/crm/follow-ups',
    name: '跟进记录',
    icon: 'profile',
    access: 'canFollowUpRead',
    component: './crm/follow-ups',
  },
  {
    path: '/crm/opportunities',
    name: '商机管理',
    icon: 'fund',
    access: 'canOpportunityRead',
    component: './crm/opportunities',
  },
  {
    path: '/crm/deals',
    name: '成单记录',
    icon: 'wallet',
    access: 'canDealRead',
    component: './crm/deals',
  },
  {
    path: '/content/tasks',
    name: '内容任务',
    icon: 'fileText',
    access: 'canContentRead',
    component: './content/tasks',
  },
  {
    path: '/kb/sessions',
    name: '智能客服',
    icon: 'message',
    access: 'canKbRead',
    component: './kb/sessions',
  },
  {
    path: '/metrics',
    name: '数据看板',
    icon: 'dashboard',
    access: 'canMetricsRead',
    component: './metrics',
  },
  {
    path: '/audit/logs',
    name: '审计日志',
    icon: 'audit',
    access: 'canAuditRead',
    component: './audit/logs',
  },
  {
    path: '/',
    redirect: '/welcome',
  },
  {
    path: '*',
    layout: false,
    component: './404',
  },
];
