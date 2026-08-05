import { computed, ref } from 'vue';

import type { CrossSpreadLimitExecutionResult } from '@/api/platform/crossSpreadLifecycle';

export interface LogEntry {
  id: string;
  time: string;
  direction: string;
  type: string;
  qty: string;
  trigger: string;
  fill: string;
  status: string;
  channel: string;
}

type MessageTone = 'is-success' | 'is-error' | 'is-warn';

const UNAVAILABLE_MESSAGE = '跨所价差写入尚未配置；当前页面只允许读取正式行情与Runtime状态。';

export function useCrossSpreadExecution(_options: unknown) {
  const submitLoading = ref(false);
  const confirmVisible = ref(false);
  const executionLogs = ref<LogEntry[]>([]);
  const executionMessage = ref(UNAVAILABLE_MESSAGE);
  const executionMessageTone = ref<MessageTone>('is-warn');
  const limitEvidence = ref<CrossSpreadLimitExecutionResult | null>(null);

  const confirmGuardMessage = computed(() => UNAVAILABLE_MESSAGE);
  const confirmSummary = computed(() => ({
    action: '写入未配置',
    qty: '--',
    legs: '--',
    mode: '只读',
    marketSpread: '--',
    spreadRange: '--',
    takeProfit: '--',
    stopLoss: '--',
  }));

  function setExecutionMessage(nextMessage: string, nextTone: MessageTone) {
    executionMessage.value = nextMessage;
    executionMessageTone.value = nextTone;
  }

  function openConfirm(_action: string) {
    confirmVisible.value = false;
    setExecutionMessage(UNAVAILABLE_MESSAGE, 'is-warn');
  }

  function prepareOpenDraft(_direction: 'long' | 'short') {
    openConfirm('WRITE_UNAVAILABLE');
  }

  async function confirmOrder() {
    confirmVisible.value = false;
    setExecutionMessage(UNAVAILABLE_MESSAGE, 'is-warn');
  }

  return {
    confirmGuardMessage,
    confirmOrder,
    confirmSummary,
    confirmVisible,
    executionLogs,
    executionMessage,
    executionMessageTone,
    limitEvidence,
    openConfirm,
    prepareOpenDraft,
    setExecutionMessage,
    submitLoading,
  };
}
