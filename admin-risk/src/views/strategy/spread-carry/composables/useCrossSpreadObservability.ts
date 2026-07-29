import { ref } from 'vue';
import {
  getCrossSpreadObservability,
  type CrossSpreadObservabilityResult,
} from '@/api/platform/crossSpreadObservability';

function resolveError(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null) {
    const candidate = error as {
      message?: string;
      response?: { data?: { detail?: string | Array<{ msg?: string }> } };
    };
    const detail = candidate.response?.data?.detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg).filter(Boolean).join('; ') || fallback;
    }
    return detail || candidate.message || fallback;
  }
  return fallback;
}

export function useCrossSpreadObservability() {
  const observability = ref<CrossSpreadObservabilityResult | null>(null);
  const observabilityError = ref('');

  async function refreshObservability() {
    try {
      observability.value = await getCrossSpreadObservability(1, 1, 'fast');
      observabilityError.value = '';
    } catch (error: unknown) {
      observabilityError.value = resolveError(error, '实盘只读数据读取失败');
    }
  }

  return {
    observability,
    observabilityError,
    refreshObservability,
  };
}
