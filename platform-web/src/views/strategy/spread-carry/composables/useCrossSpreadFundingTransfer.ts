import Decimal from 'decimal.js';
import { computed, onMounted, ref, watch } from 'vue';

import {
  cancelFundingTransfer,
  createFundingTransfer,
  getFundingTransfer,
  getFundingTransferQuote,
  type FundingTransferDirection,
  type FundingTransferQuoteResult,
  type InternalCapitalTransferResult,
} from '@/api/platform/crossSpreadFundingTransfer';

interface FundingSuggestion {
  direction: FundingTransferDirection | null;
  amount: string | null;
}

export function calculateFundingSuggestion(
  bybitTransferable: string | null,
  mt5Withdrawable: string | null,
): FundingSuggestion {
  if (bybitTransferable === null || mt5Withdrawable === null) {
    return { direction: null, amount: null };
  }
  const bybit = new Decimal(bybitTransferable);
  const mt5 = new Decimal(mt5Withdrawable);
  if (bybit.eq(mt5)) return { direction: null, amount: '0' };
  const direction: FundingTransferDirection = bybit.gt(mt5) ? 'bybit_to_mt5' : 'mt5_to_bybit';
  const source = direction === 'bybit_to_mt5' ? bybit : mt5;
  const amount = Decimal.min(bybit.minus(mt5).abs().div(2), source);
  return { direction, amount: amount.toFixed() };
}

function requestErrorMessage(error: unknown, fallback: string): string {
  if (typeof error !== 'object' || error === null) return fallback;
  const candidate = error as {
    message?: unknown;
    response?: { data?: { detail?: unknown } };
  };
  const detail = candidate.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  return typeof candidate.message === 'string' && candidate.message ? candidate.message : fallback;
}

export function useCrossSpreadFundingTransfer() {
  const quote = ref<FundingTransferQuoteResult | null>(null);
  const transfer = ref<InternalCapitalTransferResult | null>(null);
  const direction = ref<FundingTransferDirection>('bybit_to_mt5');
  const amountInput = ref('');
  const loading = ref(false);
  const error = ref('');
  const confirmed = ref(false);
  const manuallyEdited = ref(false);
  const draftIdempotencyKey = ref('');
  const assistedExpected = ref<{ bybit: string; mt5: string } | null>(null);
  const balanceVerification = ref<'idle' | 'matched' | 'not_matched'>('idle');

  const bybitAmount = computed(() => quote.value?.bybitTransferable.amount ?? null);
  const mt5Amount = computed(() => quote.value?.mt5Withdrawable.amount ?? null);
  const sourceAvailable = computed(() =>
    direction.value === 'bybit_to_mt5' ? bybitAmount.value : mt5Amount.value,
  );
  const amountError = computed(() => {
    if (!amountInput.value.trim()) return '请输入调拨金额';
    try {
      const amount = new Decimal(amountInput.value);
      if (!amount.isPositive()) return '金额必须大于 0';
      if (sourceAvailable.value === null) return '转出方余额暂不可用';
      if (amount.gt(new Decimal(sourceAvailable.value))) return '金额超过转出方真实可用余额';
      return '';
    } catch {
      return '请输入有效 Decimal 金额';
    }
  });
  const projectedBalances = computed(() => {
    if (bybitAmount.value === null || mt5Amount.value === null || amountError.value) return null;
    const bybit = new Decimal(bybitAmount.value);
    const mt5 = new Decimal(mt5Amount.value);
    const amount = new Decimal(amountInput.value);
    return direction.value === 'bybit_to_mt5'
      ? { bybit: bybit.minus(amount).toFixed(), mt5: mt5.plus(amount).toFixed() }
      : { bybit: bybit.plus(amount).toFixed(), mt5: mt5.minus(amount).toFixed() };
  });
  const canSubmit = computed(
    () => confirmed.value && !loading.value && !amountError.value && quote.value !== null,
  );

  watch([direction, amountInput], () => {
    confirmed.value = false;
    draftIdempotencyKey.value = '';
    assistedExpected.value = null;
    balanceVerification.value = 'idle';
  });

  async function refreshQuote(options: { preserveInput?: boolean } = {}) {
    loading.value = true;
    error.value = '';
    try {
      const next = await getFundingTransferQuote();
      quote.value = next;
      const suggestion = calculateFundingSuggestion(
        next.bybitTransferable.amount,
        next.mt5Withdrawable.amount,
      );
      if (!options.preserveInput && !manuallyEdited.value) {
        if (suggestion.direction) direction.value = suggestion.direction;
        amountInput.value = suggestion.amount ?? '';
      }
      if (assistedExpected.value && next.bybitTransferable.amount && next.mt5Withdrawable.amount) {
        balanceVerification.value =
          new Decimal(next.bybitTransferable.amount).eq(assistedExpected.value.bybit) &&
          new Decimal(next.mt5Withdrawable.amount).eq(assistedExpected.value.mt5)
            ? 'matched'
            : 'not_matched';
      }
    } catch (cause) {
      error.value = requestErrorMessage(cause, '双边资金余额读取失败');
    } finally {
      loading.value = false;
    }
  }

  function updateAmount(value: string) {
    manuallyEdited.value = true;
    amountInput.value = value;
  }

  function swapDirection() {
    direction.value = direction.value === 'bybit_to_mt5' ? 'mt5_to_bybit' : 'bybit_to_mt5';
  }

  async function submitTransfer() {
    if (!canSubmit.value || !projectedBalances.value) return;
    loading.value = true;
    error.value = '';
    draftIdempotencyKey.value ||= crypto.randomUUID();
    assistedExpected.value = projectedBalances.value;
    try {
      transfer.value = await createFundingTransfer({
        idempotencyKey: draftIdempotencyKey.value,
        direction: direction.value,
        amount: new Decimal(amountInput.value).toFixed(),
      });
      if (transfer.value.status === 'completed') {
        await refreshQuote({ preserveInput: true });
      }
    } catch (cause) {
      error.value = requestErrorMessage(cause, '资金调拨提交失败');
    } finally {
      loading.value = false;
    }
  }

  async function refreshTransferAndBalances() {
    loading.value = true;
    error.value = '';
    try {
      if (transfer.value) transfer.value = await getFundingTransfer(transfer.value.transferId);
      await refreshQuote({ preserveInput: true });
    } catch (cause) {
      error.value = requestErrorMessage(cause, '资金状态核对失败');
    } finally {
      loading.value = false;
    }
  }

  async function cancelTransfer() {
    if (!transfer.value || transfer.value.status !== 'pending') return;
    loading.value = true;
    error.value = '';
    try {
      transfer.value = await cancelFundingTransfer(transfer.value.transferId);
      assistedExpected.value = null;
      balanceVerification.value = 'idle';
      await refreshQuote({ preserveInput: true });
    } catch (cause) {
      error.value = requestErrorMessage(cause, '辅助调拨取消失败');
    } finally {
      loading.value = false;
    }
  }

  async function copyAmount() {
    await navigator.clipboard.writeText(amountInput.value);
  }

  function openOfficialFundingPage() {
    const url = quote.value?.officialFundingUrl;
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
  }

  onMounted(() => void refreshQuote());

  return {
    amountError,
    amountInput,
    balanceVerification,
    bybitAmount,
    canSubmit,
    cancelTransfer,
    confirmed,
    copyAmount,
    direction,
    error,
    loading,
    mt5Amount,
    openOfficialFundingPage,
    projectedBalances,
    quote,
    refreshTransferAndBalances,
    submitTransfer,
    swapDirection,
    transfer,
    updateAmount,
  };
}
