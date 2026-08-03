import { ref } from 'vue';

import { getTradingSnapshot } from '/@/api/platform/trading';
import type { TradingSnapshot } from '/@/api/platform/trading.types';

function normalizeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'Trading request failed';
}

export function usePlatformTrading() {
  const refreshing = ref(false);
  const errorMessage = ref<string | null>(null);
  const snapshot = ref<TradingSnapshot>({ position: null, pnl: null });

  async function refresh(accountId: string, instrumentId: string): Promise<void> {
    refreshing.value = true;
    errorMessage.value = null;
    try {
      snapshot.value = await getTradingSnapshot(accountId, instrumentId);
    } catch (error) {
      errorMessage.value = normalizeError(error);
      throw error;
    } finally {
      refreshing.value = false;
    }
  }

  return {
    errorMessage,
    refreshing,
    snapshot,
    refresh,
  };
}
