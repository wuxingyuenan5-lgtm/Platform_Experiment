import { computed, ref } from 'vue';

import { createTradingOrder, getTradingSnapshot } from '/@/api/platform/trading';
import type { CreateOrderInput, OrderResult, TradingSnapshot } from '/@/api/platform/trading.types';

function normalizeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'Trading request failed';
}

export function usePlatformTrading() {
  const submitting = ref(false);
  const refreshing = ref(false);
  const errorMessage = ref<string | null>(null);
  const lastOrder = ref<OrderResult | null>(null);
  const snapshot = ref<TradingSnapshot>({ position: null, pnl: null });

  const busy = computed(() => submitting.value || refreshing.value);

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

  async function submit(input: CreateOrderInput): Promise<OrderResult> {
    submitting.value = true;
    errorMessage.value = null;
    try {
      const order = await createTradingOrder(input);
      lastOrder.value = order;
      await refresh(input.accountId, input.instrumentId);
      return order;
    } catch (error) {
      errorMessage.value = normalizeError(error);
      throw error;
    } finally {
      submitting.value = false;
    }
  }

  return {
    busy,
    errorMessage,
    lastOrder,
    refreshing,
    snapshot,
    submitting,
    refresh,
    submit,
  };
}
