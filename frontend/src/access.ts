import type { AuthUser } from '@/services/voltiq/auth';

const isOperator = (user?: AuthUser) => user?.role === 'operator';
const isSales = (user?: AuthUser) => user?.role === 'sales';
const isManager = (user?: AuthUser) => user?.role === 'manager';

export default function access(
  initialState: { currentUser?: AuthUser } | undefined,
) {
  const currentUser = initialState?.currentUser;
  const operator = isOperator(currentUser);
  const sales = isSales(currentUser);
  const manager = isManager(currentUser);

  return {
    canLeadRead: operator || sales || manager,
    canLeadWrite: operator || sales,
    canFollowUpRead: sales || manager,
    canFollowUpWrite: sales,
    canOpportunityRead: sales || manager,
    canOpportunityWrite: sales,
    canDealRead: sales || manager,
    canDealCreate: sales,
    canContentRead: operator || manager,
    canContentWrite: operator,
    canKbRead: operator || manager,
    canMetricsRead: sales || manager,
    canAuditRead: manager,
  };
}
