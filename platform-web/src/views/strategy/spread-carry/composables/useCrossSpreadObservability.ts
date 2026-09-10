import { computed } from 'vue';
import { useQuery } from '@tanstack/vue-query';
import {
  strategyQueryClient,
  strategyQueryKey,
  strategySession,
} from '@/api/platform/strategyQueries';
import { getCrossSpreadObservability } from '@/api/platform/crossSpreadObservability';

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
          .join('; ') || fallback
      );
    }
    return detail || candidate.message || fallback;
  }
  return fallback;
}

export function useCrossSpreadObservability() {
  const query = useQuery(
    {
      queryKey: computed(() => strategyQueryKey('cross-spread', 'observability', 1, 1, 'fast')),
      queryFn: ({ signal }) => getCrossSpreadObservability(1, 1, 'fast', signal),
      enabled: computed(() => !!strategySession.value.userId),
    },
    strategyQueryClient,
  );
  return {
    observability: computed(() => query.data.value ?? null),
    observabilityError: computed(() =>
      query.error.value ? resolveError(query.error.value, '实盘只读数据读取失败') : '',
    ),
    refreshObservability: async () => {
      await query.refetch({ cancelRefetch: false });
    },
  };
}
