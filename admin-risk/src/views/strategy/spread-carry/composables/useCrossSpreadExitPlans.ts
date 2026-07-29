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
      return detail.map((item) => item.msg).filter(Boolean).join('；') || fallback;
    }
    return detail || candidate.message || fallback;
  }
  return fallback;
}

export function useCrossSpreadExitPlans() {
  const exitPlans = ref<CrossSpreadExitPlanResult[]>([]);

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
  };
}
