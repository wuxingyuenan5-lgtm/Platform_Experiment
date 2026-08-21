import { ref } from 'vue';
import {
  getCrossSpreadExitPlans,
  type CrossSpreadExitPlanResult,
} from '@/api/platform/crossSpreadLifecycle';

function resolveError(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null) {
    const candidate = error as {
      message?: string;
      response?: { data?: { detail?: string | Array<{ msg?: string }> } };
    };
    const detail = candidate.response?.data?.detail;
    if (Array.isArray(detail)) {
      return (
        detail
          .map((item) => item.msg)
          .filter(Boolean)
          .join('；') || fallback
      );
    }
    return detail || candidate.message || fallback;
  }
  return fallback;
}

export function useCrossSpreadExitPlans() {
  const exitPlans = ref<CrossSpreadExitPlanResult[]>([]);

  function comparePlans(left: CrossSpreadExitPlanResult, right: CrossSpreadExitPlanResult): number {
    return new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime();
  }

  function upsertExitPlan(plan: CrossSpreadExitPlanResult) {
    const nextPlans = [...exitPlans.value];
    const index = nextPlans.findIndex((item) => item.planId === plan.planId);
    if (index >= 0) {
      nextPlans[index] = plan;
    } else {
      nextPlans.unshift(plan);
    }
    nextPlans.sort(comparePlans);
    exitPlans.value = nextPlans;
  }

  async function refreshExitPlans() {
    try {
      exitPlans.value = await getCrossSpreadExitPlans();
      return '';
    } catch (error: unknown) {
      return resolveError(error, '退出计划读取失败');
    }
  }

  return {
    exitPlans,
    refreshExitPlans,
    upsertExitPlan,
  };
}
