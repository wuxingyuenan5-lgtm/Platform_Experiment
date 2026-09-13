import { useQuery } from '@tanstack/vue-query';
import { useDocumentVisibility, refDebounced } from '@vueuse/core';
import {
  strategyQueryClient,
  strategyQueryKey,
  strategySession,
} from '@/api/platform/strategyQueries';
import { useUserStore } from '@/store/modules/user';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Modal } from 'ant-design-vue';
import Decimal from 'decimal.js';

import {
  getFundingExecutionContext,
  getFundingInstructionWorkspace,
  getFundingInstructionWorkspaceByIdempotency,
  getFundingPositionGroups,
  type FundingPositionGroup,
  submitFundingInstruction,
  type FundingExecutionContext,
  type FundingWorkspaceResponse,
} from '@/api/platform/fundingWorkspace';
import {
  clearFundingDraft,
  isFundingAutoPollingState,
  isFundingTerminalState,
  readFundingDraft,
  writeFundingDraft,
  type FundingPendingDraft,
  type FundingExecutionPolicy,
} from './fundingExecutionRecovery';

function createIdempotencyKey(): string {
  return `funding:${crypto.randomUUID()}`;
}

function normalizeWorkspaceState(workspace: Record<string, unknown> | undefined | null): string {
  return typeof workspace?.executionState === 'string' ? workspace.executionState : 'loading';
}

/**
 * 本次新建的资费草稿。`executionPolicy` 由非可选 ref 写入，必然已选定；
 * `FundingPendingDraft` 的该字段可选只是为了容忍从本地存储恢复的旧草稿，
 * 因此提交路径使用本收窄类型，而不是给提交值补一个默认执行方式。
 */
type FreshFundingDraft = FundingPendingDraft & { executionPolicy: FundingExecutionPolicy };

export function useFundingWorkspace() {
  const userStore = useUserStore();
  const readCurrentDraft = () =>
    userStore.authentication?.user.role === 'ceo'
      ? readFundingDraft(localStorage, userStore.authentication.user.userId)
      : null;
  let disposed = false;
  const contextReady = ref(false);
  const instructionPollAttempt = ref(0);
  const mounted = ref(false);
  const visibility = useDocumentVisibility();
  const instructionPollDelays = [1_000, 2_000, 3_000];
  const submitting = ref(false);
  const error = ref<string | null>(null);
  const context = ref<FundingExecutionContext | null>(null);
  const positionGroups = ref<FundingPositionGroup[]>([]);
  const selectedPerpetualSymbol = ref<string>('');
  const selectedSpotSymbol = ref<string>('');
  const selectedCloseInstructionId = ref<string>('');
  const notionalInput = ref<string>('100');
  const quantityOverride = ref<string | null>(null);
  const quantityInput = computed({
    get: () => quantityOverride.value ?? context.value?.suggestedQuantity ?? '',
    set: (value: string) => {
      quantityOverride.value = value;
    },
  });
  const closeQuantityInput = ref<string>('');
  const executionPolicy = ref<FundingExecutionPolicy>('market');
  const perpetualLimitPriceInput = ref('');
  const activeInstruction = ref<Record<string, unknown> | null>(null);
  const activeWorkspace = ref<Record<string, unknown> | null>(null);
  const pendingDraft = ref<FundingPendingDraft | null>(readCurrentDraft());

  const readiness = computed(
    () => (context.value?.controlledLiveReadiness ?? {}) as Record<string, unknown>,
  );
  const symbolOptions = computed(() => context.value?.symbolOptions ?? []);
  const workspaceState = computed(() => normalizeWorkspaceState(activeWorkspace.value));
  const selectedCloseGroup = computed(
    () =>
      positionGroups.value.find(
        (item) => item.instructionId === selectedCloseInstructionId.value,
      ) ?? null,
  );
  function positiveQuantity(value: string): boolean {
    try {
      return new Decimal(value).isFinite() && new Decimal(value).gt(0);
    } catch {
      return false;
    }
  }
  function validQuantity(value: string, includeSpot: boolean): boolean {
    if (!positiveQuantity(value)) return false;
    try {
      const quantity = new Decimal(value);
      const legs = includeSpot ? (['perpetual', 'spot'] as const) : (['perpetual'] as const);
      return legs.every((leg) => {
        const step = new Decimal(context.value?.quantityStep[leg] ?? '0');
        const minimum = new Decimal(context.value?.minimumQuantity[leg] ?? '0');
        return step.gt(0) && quantity.mod(step).eq(0) && quantity.gte(minimum);
      });
    } catch {
      return false;
    }
  }
  const validExecutionPrice = computed(() => {
    if (executionPolicy.value !== 'fok') return true;
    if (!positiveQuantity(perpetualLimitPriceInput.value)) return false;
    try {
      const tick = new Decimal(context.value?.tickSize.perpetual ?? '0');
      return tick.gt(0) && new Decimal(perpetualLimitPriceInput.value).mod(tick).eq(0);
    } catch {
      return false;
    }
  });
  const readyToTrade = computed(
    () =>
      userStore.authentication?.user.role === 'ceo' &&
      contextReady.value &&
      !loading.value &&
      readiness.value.ready === true &&
      !submitting.value &&
      !pendingDraft.value,
  );
  const canSubmit = computed(
    () =>
      readyToTrade.value &&
      validExecutionPrice.value &&
      !!selectedPerpetualSymbol.value &&
      context.value?.openSizing?.valid === true &&
      positiveQuantity(quantityInput.value) &&
      new Decimal(quantityInput.value).eq(context.value.openSizing.spotQuantity ?? '0'),
  );
  const canClose = computed(
    () =>
      readyToTrade.value &&
      validExecutionPrice.value &&
      !!selectedCloseGroup.value &&
      (!selectedCloseGroup.value.spotFeeAdjusted ||
        selectedCloseGroup.value.remainingSpotQuantity != null) &&
      validQuantity(closeQuantityInput.value, false) &&
      new Decimal(closeQuantityInput.value).lte(
        selectedCloseGroup.value?.remainingClosableQuantity ?? '0',
      ),
  );

  watch(
    [notionalInput, selectedPerpetualSymbol, selectedSpotSymbol],
    () => {
      quantityOverride.value = null;
      contextReady.value = false;
    },
    { flush: 'sync' },
  );
  const contextInputs = computed(() => ({
    perpetualSymbol: selectedPerpetualSymbol.value || undefined,
    spotSymbol: selectedSpotSymbol.value || undefined,
    notional: notionalInput.value || undefined,
    quantity: quantityOverride.value || undefined,
  }));
  const debouncedInputs = refDebounced(contextInputs, 250);
  const contextQuery = useQuery(
    {
      queryKey: computed(() => strategyQueryKey('funding', 'context', debouncedInputs.value)),
      queryFn: ({ signal }) => getFundingExecutionContext(debouncedInputs.value, signal),
      enabled: computed(
        () =>
          mounted.value &&
          !!strategySession.value.userId &&
          visibility.value === 'visible' &&
          !submitting.value,
      ),
      refetchInterval: 15_000,
    },
    strategyQueryClient,
  );
  const loading = contextQuery.isFetching;
  watch(
    contextQuery.isFetching,
    (fetching) => {
      if (fetching) {
        contextReady.value = false;
      }
    },
    { flush: 'sync' },
  );
  watch(
    [contextQuery.data, contextQuery.isFetching, contextQuery.error],
    ([next, fetching, caught]) => {
      contextReady.value = false;
      if (caught) {
        error.value = caught instanceof Error ? caught.message : '行情暂时不可用';
        return;
      }
      if (
        !next ||
        fetching ||
        JSON.stringify(contextInputs.value) !== JSON.stringify(debouncedInputs.value)
      )
        return;
      context.value = next;
      if (!selectedPerpetualSymbol.value) selectedPerpetualSymbol.value = next.perpetualSymbol;
      if (!selectedSpotSymbol.value) selectedSpotSymbol.value = next.spotSymbol;
      contextReady.value = next.dataQualityState === 'complete';
      error.value = null;
    },
  );
  watch(
    contextInputs,
    () => {
      contextReady.value = false;
    },
    { flush: 'sync' },
  );

  const positionsQuery = useQuery(
    {
      queryKey: computed(() =>
        strategyQueryKey('funding', 'positions', context.value?.accountId, 'all'),
      ),
      queryFn: ({ signal }) => getFundingPositionGroups('all', signal),
      enabled: computed(() => mounted.value && !!strategySession.value.userId),
    },
    strategyQueryClient,
  );
  watch(positionsQuery.data, (next) => {
    if (!next) return;
    positionGroups.value = next;
    if (selectedCloseInstructionId.value && !selectedCloseGroup.value) {
      selectedCloseInstructionId.value = '';
      closeQuantityInput.value = '';
    }
  });

  const instructionQuery = useQuery(
    {
      queryKey: computed(() =>
        strategyQueryKey(
          'funding',
          'instruction',
          pendingDraft.value?.instructionId || pendingDraft.value?.idempotencyKey,
        ),
      ),
      queryFn: async ({ signal }) => {
        const draft = pendingDraft.value;
        if (!draft) throw new Error('没有待恢复指令');
        instructionPollAttempt.value += 1;
        return draft.instructionId
          ? getFundingInstructionWorkspace(draft.instructionId, signal)
          : getFundingInstructionWorkspaceByIdempotency(draft.idempotencyKey, signal);
      },
      enabled: computed(
        () =>
          mounted.value &&
          !!strategySession.value.userId &&
          !submitting.value &&
          visibility.value === 'visible' &&
          !!pendingDraft.value &&
          isFundingAutoPollingState(pendingDraft.value.state),
      ),
      refetchInterval: () =>
        instructionPollDelays[
          Math.min(instructionPollAttempt.value, instructionPollDelays.length - 1)
        ],
    },
    strategyQueryClient,
  );
  function applyInstructionResponse(response: FundingWorkspaceResponse) {
    const draft = pendingDraft.value;
    if (!response || !draft || disposed) return;
    activeInstruction.value = response.instruction;
    activeWorkspace.value = response.workspaceState;
    const state = normalizeWorkspaceState(response.workspaceState);
    if (isFundingTerminalState(state)) {
      clearFundingDraft();
      pendingDraft.value = null;
    } else {
      pendingDraft.value = {
        ...draft,
        instructionId: String(response.instruction.instructionId ?? draft.instructionId ?? ''),
        state: state as FundingPendingDraft['state'],
      };
      writeFundingDraft(pendingDraft.value);
    }
    // A pause can arrive after the table read but before the final fill/status.
    // Refresh facts even when automatic instruction polling is about to stop.
    void refreshPositionGroups().catch((caught) => {
      error.value = caught instanceof Error ? caught.message : '持仓记录暂时不可用';
    });
  }
  watch(instructionQuery.data, (response) => {
    if (response) applyInstructionResponse(response);
  });

  async function refreshContext() {
    await contextQuery.refetch({ cancelRefetch: false });
  }
  async function refreshPositionGroups() {
    await positionsQuery.refetch({ cancelRefetch: true, throwOnError: true });
  }
  async function refreshInstruction(options: { silent?: boolean } = {}) {
    if (!pendingDraft.value) return;
    try {
      await instructionQuery.refetch({ cancelRefetch: false, throwOnError: true });
    } catch (caught) {
      if (!options.silent)
        error.value = caught instanceof Error ? caught.message : '指令状态暂不可用';
    }
  }

  async function refreshAll() {
    const results = await Promise.allSettled([
      refreshContext(),
      refreshPositionGroups(),
      refreshInstruction(),
    ]);
    const failure = results.find((result) => result.status === 'rejected');
    if (failure?.status === 'rejected')
      error.value = failure.reason instanceof Error ? failure.reason.message : '账户记录暂时不可用';
  }

  async function submit(action: 'open' | 'close') {
    if (
      submitting.value ||
      pendingDraft.value ||
      !(action === 'open' ? canSubmit.value : canClose.value)
    )
      return;
    const sessionGeneration = strategySession.value.generation;
    const group = selectedCloseGroup.value;
    const sizing = context.value?.openSizing;
    const draft: FreshFundingDraft = {
      idempotencyKey: createIdempotencyKey(),
      ownerUserId: userStore.authentication!.user.userId,
      action,
      perpetualSymbol: action === 'close' ? group!.perpetualSymbol : selectedPerpetualSymbol.value,
      spotSymbol: action === 'close' ? group!.spotSymbol : selectedSpotSymbol.value,
      quantity: action === 'close' ? closeQuantityInput.value : quantityInput.value,
      expectedPerpetualQuantity:
        action === 'open' ? sizing?.perpetualQuantity ?? undefined : undefined,
      executionPolicy: executionPolicy.value,
      perpetualLimitPrice:
        executionPolicy.value === 'fok' ? perpetualLimitPriceInput.value : undefined,
      targetOpenInstructionId: action === 'close' ? selectedCloseInstructionId.value : undefined,
      state: 'submitting',
    };
    submitting.value = true;
    const confirmed = await new Promise<boolean>((resolve) =>
      Modal.confirm({
        title: action === 'open' ? '确认资费开仓' : '确认资费平仓',
        content: `${draft.perpetualSymbol} / ${draft.spotSymbol}，${
          action === 'open'
            ? `现货买入 ${draft.quantity}，预计净到账 ${sizing?.expectedSpotNetQuantity}；永续卖出 ${draft.expectedPerpetualQuantity}，取整余量 ${sizing?.roundingResidualQuantity}`
            : `永续平仓数量 ${draft.quantity}`
        }。永续${
          draft.executionPolicy === 'market'
            ? '市价'
            : draft.executionPolicy === 'fok'
            ? `限价 ${draft.perpetualLimitPrice} USDT（FOK，未全部成交则取消）`
            : '挂单追价（PostOnly）'
        }，现货按永续实际成交量市价对冲。${
          action === 'open'
            ? '现货买入手续费从币中扣除；永续手续费及现货卖出手续费计入 USDT 成本。'
            : `按所选组合平仓，现货将按扣除手续费后的净到账数量配比执行。${
                group?.spotFeeResidualQuantity ? `现货扣币 ${group.spotFeeResidualQuantity}。` : ''
              }`
        }`,
        okText: '确认提交',
        cancelText: '返回修改',
        onOk: () => {
          resolve(true);
        },
        onCancel: () => {
          resolve(false);
        },
      }),
    );
    if (!confirmed || disposed || sessionGeneration !== strategySession.value.generation) {
      submitting.value = false;
      return;
    }
    error.value = null;
    try {
      writeFundingDraft(draft);
      pendingDraft.value = draft;
      const response = await submitFundingInstruction({
        action,
        idempotencyKey: draft.idempotencyKey,
        perpetualSymbol: draft.perpetualSymbol,
        spotSymbol: draft.spotSymbol,
        quantity: draft.quantity,
        expectedPerpetualQuantity: draft.expectedPerpetualQuantity,
        executionPolicy: draft.executionPolicy,
        perpetualLimitPrice: draft.perpetualLimitPrice,
        targetOpenInstructionId: draft.targetOpenInstructionId,
      });
      if (disposed || sessionGeneration !== strategySession.value.generation) return;
      applyInstructionResponse(response);
      instructionPollAttempt.value = 0;
      await refreshPositionGroups();
      return response;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '提交结果待确认，请恢复原指令';
      instructionPollAttempt.value = 0;
      const status = (caught as { response?: { status?: number } })?.response?.status;
      if (status && [400, 401, 403, 404, 409, 422, 423].includes(status)) {
        try {
          const known = await getFundingInstructionWorkspaceByIdempotency(draft.idempotencyKey);
          if (!disposed && sessionGeneration === strategySession.value.generation)
            applyInstructionResponse(known);
        } catch (lookupError) {
          const lookupStatus = (lookupError as { response?: { status?: number } })?.response
            ?.status;
          if (
            lookupStatus === 404 &&
            !disposed &&
            sessionGeneration === strategySession.value.generation
          ) {
            clearFundingDraft();
            pendingDraft.value = null;
          }
        }
      }
    } finally {
      submitting.value = false;
    }
  }

  function selectSymbol(perpetualSymbol: string, spotSymbol: string) {
    if (perpetualSymbol !== selectedPerpetualSymbol.value) perpetualLimitPriceInput.value = '';
    selectedPerpetualSymbol.value = perpetualSymbol;
    selectedSpotSymbol.value = spotSymbol;
  }

  function selectCloseInstruction(instructionId: string) {
    selectedCloseInstructionId.value = instructionId;
    const group = positionGroups.value.find((item) => item.instructionId === instructionId);
    if (group?.remainingClosableQuantity) {
      selectSymbol(group.perpetualSymbol, group.spotSymbol);
      closeQuantityInput.value = group.remainingClosableQuantity;
    }
  }

  function selectCloseFraction(percent: number) {
    if (![25, 50, 75, 100].includes(percent) || !selectedCloseGroup.value) return;
    try {
      const maximum = new Decimal(selectedCloseGroup.value.remainingClosableQuantity);
      const step = new Decimal(context.value?.quantityStep.perpetual ?? '0');
      if (!step.gt(0)) return;
      closeQuantityInput.value = maximum
        .times(percent)
        .div(100)
        .div(step)
        .floor()
        .times(step)
        .toFixed();
    } catch {
      closeQuantityInput.value = '';
    }
  }

  watch(
    strategySession,
    () => {
      contextReady.value = false;
      context.value = null;
      quantityOverride.value = null;
      positionGroups.value = [];
      activeInstruction.value = null;
      activeWorkspace.value = null;
      pendingDraft.value = readCurrentDraft();
    },
    { flush: 'sync' },
  );
  function recoverPendingInstruction() {
    if (pendingDraft.value && !submitting.value) void refreshInstruction({ silent: true });
  }
  watch(visibility, (state) => {
    if (state === 'visible') recoverPendingInstruction();
  });
  onMounted(() => {
    mounted.value = true;
    recoverPendingInstruction();
    window.addEventListener('online', recoverPendingInstruction);
  });
  onBeforeUnmount(() => {
    disposed = true;
    window.removeEventListener('online', recoverPendingInstruction);
  });

  return {
    loading,
    submitting,
    error,
    context,
    positionGroups,
    selectedPerpetualSymbol,
    selectedSpotSymbol,
    selectedCloseInstructionId,
    selectedCloseGroup,
    notionalInput,
    quantityInput,
    closeQuantityInput,
    executionPolicy,
    perpetualLimitPriceInput,
    activeInstruction,
    activeWorkspace,
    pendingDraft,
    readiness,
    symbolOptions,
    workspaceState,
    canSubmit,
    canClose,
    refreshAll,
    refreshContext,
    refreshPositionGroups,
    refreshInstruction,
    submit,
    selectSymbol,
    selectCloseInstruction,
    selectCloseFraction,
  };
}
