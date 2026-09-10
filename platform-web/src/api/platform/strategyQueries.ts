import { QueryClient } from '@tanstack/vue-query';
import { ref } from 'vue';

export const strategyQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 0,
      gcTime: 60_000,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      networkMode: 'always',
    },
    mutations: { retry: false, networkMode: 'always' },
  },
});

export const strategySession = ref({ generation: 0, userId: '' });
let sessionIdentity = '';

export function setStrategyQuerySession(userId = '', identity = '') {
  if (identity === sessionIdentity && userId === strategySession.value.userId) return;
  sessionIdentity = identity;
  strategyQueryClient.clear();
  strategySession.value = { generation: strategySession.value.generation + 1, userId };
}

export function strategyQueryKey(...parts: unknown[]) {
  const { generation, userId } = strategySession.value;
  return ['strategy', generation, userId, ...parts];
}

export async function fetchStrategyQuery<T>(
  parts: unknown[],
  queryFn: (signal: AbortSignal) => Promise<T>,
): Promise<T> {
  const generation = strategySession.value.generation;
  const value = await strategyQueryClient.fetchQuery({
    queryKey: strategyQueryKey(...parts),
    queryFn: ({ signal }) => queryFn(signal),
  });
  if (generation !== strategySession.value.generation) throw new Error('登录状态已变更');
  return value;
}
