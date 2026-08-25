import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import {
  getFundingExecutionContext,
  getFundingInstructionWorkspace,
  getFundingInstructionWorkspaceByIdempotency,
  getFundingPositionGroups,
  type FundingPositionGroup,
  submitFundingInstruction,
  type FundingExecutionContext,
} from '@/api/platform/fundingWorkspace';
import {
  clearFundingDraft,
  isFundingAutoPollingState,
  isFundingTerminalState,
  readFundingDraft,
  writeFundingDraft,
  type FundingPendingDraft,
} from './fundingExecutionRecovery';

function createIdempotencyKey(): string {
  return `funding:${crypto.randomUUID()}`;
}

function normalizeWorkspaceState(workspace: Record<string, unknown> | undefined | null): string {
  return typeof workspace?.executionState === 'string' ? workspace.executionState : 'loading';
}

function isPageVisible(): boolean {
  return typeof document === 'undefined' || document.visibilityState === 'visible';
}

export function useFundingWorkspace() {
  let refreshTimer: ReturnType<typeof setTimeout> | null = null;
  let instructionPollTimer: ReturnType<typeof setTimeout> | null = null;
  let instructionPollAttempt = 0;
  const instructionPollDelays = [1_000, 2_000, 3_000];
  const loading = ref(false);
  const submitting = ref(false);
  const error = ref<string | null>(null);
  const context = ref<FundingExecutionContext | null>(null);
  const positionGroups = ref<FundingPositionGroup[]>([]);
  const selectedPerpetualSymbol = ref<string>('');
  const selectedSpotSymbol = ref<string>('');
  const selectedCloseInstructionId = ref<string>('');
  const notionalInput = ref<string>('100');
  const quantityInput = ref<string>('');
  const activeInstruction = ref<Record<string, unknown> | null>(null);
  const activeWorkspace = ref<Record<string, unknown> | null>(null);
  const pendingDraft = ref<FundingPendingDraft | null>(readFundingDraft());

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
  const canSubmit = computed(() => {
    const ready = readiness.value.ready === true;
    if (!ready || submitting.value || pendingDraft.value || !quantityInput.value) return false;
    if (!selectedPerpetualSymbol.value) return false;
    return (
      !selectedCloseInstructionId.value ||
      (selectedCloseGroup.value?.remainingClosableQuantity ?? '0') !== '0'
    );
  });

  async function refreshContext() {
    loading.value = true;
    error.value = null;
    try {
      const next = await getFundingExecutionContext({
        perpetualSymbol: selectedPerpetualSymbol.value || undefined,
        spotSymbol: selectedSpotSymbol.value || undefined,
        notional: notionalInput.value || undefined,
      });
      context.value = next;
      if (!selectedPerpetualSymbol.value) {
        selectedPerpetualSymbol.value = next.perpetualSymbol;
      }
      if (!selectedSpotSymbol.value) {
        selectedSpotSymbol.value = next.spotSymbol;
      }
      if ((!selectedCloseInstructionId.value || !quantityInput.value) && next.suggestedQuantity) {
        quantityInput.value = next.suggestedQuantity;
      }
    } catch (caught) {
      error.value =
        caught instanceof Error ? caught.message : 'Funding execution context unavailable';
    } finally {
      loading.value = false;
    }
  }

  async function refreshPositionGroups() {
    positionGroups.value = await getFundingPositionGroups('all');
    if (!selectedCloseInstructionId.value && positionGroups.value.length) {
      selectedCloseInstructionId.value =
        positionGroups.value.find((item) => item.lifecycleState === 'active')?.instructionId ??
        positionGroups.value[0].instructionId;
    }
    if (
      selectedCloseInstructionId.value &&
      !positionGroups.value.some((item) => item.instructionId === selectedCloseInstructionId.value)
    ) {
      selectedCloseInstructionId.value =
        positionGroups.value.find((item) => item.lifecycleState === 'active')?.instructionId ??
        positionGroups.value[0]?.instructionId ??
        '';
    }
  }

  function stopInstructionPolling() {
    if (instructionPollTimer) {
      clearTimeout(instructionPollTimer);
      instructionPollTimer = null;
    }
    instructionPollAttempt = 0;
  }

  function scheduleInstructionPoll() {
    if (
      instructionPollTimer ||
      !pendingDraft.value ||
      !isFundingAutoPollingState(pendingDraft.value.state) ||
      !isPageVisible()
    ) {
      return;
    }
    const delay =
      instructionPollDelays[Math.min(instructionPollAttempt, instructionPollDelays.length - 1)];
    instructionPollAttempt += 1;
    instructionPollTimer = setTimeout(async () => {
      instructionPollTimer = null;
      await refreshInstruction({ silent: true });
      scheduleInstructionPoll();
    }, delay);
  }

  function startInstructionPolling() {
    if (!pendingDraft.value || !isFundingAutoPollingState(pendingDraft.value.state)) return;
    scheduleInstructionPoll();
  }

  async function refreshInstruction(options: { silent?: boolean } = {}) {
    const draft = pendingDraft.value;
    if (!draft) return;
    let response;
    try {
      response = draft.instructionId
        ? await getFundingInstructionWorkspace(draft.instructionId)
        : await getFundingInstructionWorkspaceByIdempotency(draft.idempotencyKey);
    } catch (caught) {
      if (!options.silent) {
        error.value =
          caught instanceof Error ? caught.message : 'Funding instruction recovery unavailable';
      }
      return;
    }
    activeInstruction.value = response.instruction;
    activeWorkspace.value = response.workspaceState ?? null;
    const state = normalizeWorkspaceState(response.workspaceState);
    if (isFundingTerminalState(state)) {
      stopInstructionPolling();
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
  }

  async function refreshAll() {
    await refreshContext();
    await refreshPositionGroups();
    await refreshInstruction();
  }

  async function submit(action: 'open' | 'close') {
    if (!context.value) {
      await refreshContext();
    }
    submitting.value = true;
    error.value = null;
    const draft: FundingPendingDraft = pendingDraft.value ?? {
      idempotencyKey: createIdempotencyKey(),
      action,
      perpetualSymbol: selectedPerpetualSymbol.value,
      spotSymbol: selectedSpotSymbol.value,
      quantity: quantityInput.value,
      targetOpenInstructionId: action === 'close' ? selectedCloseInstructionId.value : undefined,
      state: 'submitting',
    };
    draft.action = action;
    draft.perpetualSymbol = selectedPerpetualSymbol.value;
    draft.spotSymbol = selectedSpotSymbol.value;
    draft.quantity = quantityInput.value;
    draft.targetOpenInstructionId =
      action === 'close' ? selectedCloseInstructionId.value : undefined;
    writeFundingDraft(draft);
    pendingDraft.value = draft;
    try {
      const response = await submitFundingInstruction({
        action,
        idempotencyKey: draft.idempotencyKey,
        perpetualSymbol: draft.perpetualSymbol,
        spotSymbol: draft.spotSymbol,
        quantity: draft.quantity,
        targetOpenInstructionId: draft.targetOpenInstructionId,
      });
      activeInstruction.value = response.instruction;
      activeWorkspace.value = response.workspaceState ?? null;
      const instructionId = String(response.instruction.instructionId ?? '');
      const state = normalizeWorkspaceState(response.workspaceState);
      if (instructionId) {
        pendingDraft.value = {
          ...draft,
          instructionId,
          state: state as FundingPendingDraft['state'],
        };
        writeFundingDraft(pendingDraft.value);
      }
      if (isFundingTerminalState(state)) {
        stopInstructionPolling();
        clearFundingDraft();
        pendingDraft.value = null;
      } else {
        startInstructionPolling();
      }
      await refreshPositionGroups();
      return response;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Funding instruction submit failed';
      startInstructionPolling();
      throw caught;
    } finally {
      submitting.value = false;
    }
  }

  function selectSymbol(perpetualSymbol: string, spotSymbol: string) {
    selectedPerpetualSymbol.value = perpetualSymbol;
    selectedSpotSymbol.value = spotSymbol;
  }

  function selectCloseInstruction(instructionId: string) {
    selectedCloseInstructionId.value = instructionId;
    const group = positionGroups.value.find((item) => item.instructionId === instructionId);
    if (group?.remainingClosableQuantity) {
      quantityInput.value = group.remainingClosableQuantity;
    }
  }

  watch(
    [selectedPerpetualSymbol, selectedSpotSymbol, notionalInput],
    () => {
      if (refreshTimer) {
        clearTimeout(refreshTimer);
      }
      refreshTimer = setTimeout(() => {
        void refreshContext();
      }, 250);
    },
    { flush: 'post' },
  );

  function recoverPendingInstruction() {
    if (!pendingDraft.value) return;
    stopInstructionPolling();
    void refreshInstruction({ silent: true }).finally(startInstructionPolling);
  }

  function handleVisibilityChange() {
    if (!isPageVisible()) {
      stopInstructionPolling();
      return;
    }
    recoverPendingInstruction();
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('online', recoverPendingInstruction);
    void refreshAll().finally(startInstructionPolling);
  });

  onBeforeUnmount(() => {
    if (refreshTimer) clearTimeout(refreshTimer);
    stopInstructionPolling();
    document.removeEventListener('visibilitychange', handleVisibilityChange);
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
    activeInstruction,
    activeWorkspace,
    pendingDraft,
    readiness,
    symbolOptions,
    workspaceState,
    canSubmit,
    refreshAll,
    refreshContext,
    refreshPositionGroups,
    refreshInstruction,
    startInstructionPolling,
    submit,
    selectSymbol,
    selectCloseInstruction,
  };
}
