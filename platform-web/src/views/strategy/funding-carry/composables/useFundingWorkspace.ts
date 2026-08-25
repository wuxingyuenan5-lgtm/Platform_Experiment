import { computed, ref } from 'vue';

import {
  getFundingExecutionContext,
  getFundingInstructionWorkspace,
  getFundingPositionGroups,
  submitFundingInstruction,
  type FundingExecutionContext,
} from '@/api/platform/fundingWorkspace';
import {
  clearFundingDraft,
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

export function useFundingWorkspace() {
  const loading = ref(false);
  const submitting = ref(false);
  const error = ref<string | null>(null);
  const context = ref<FundingExecutionContext | null>(null);
  const positionGroups = ref<Array<Record<string, unknown>>>([]);
  const selectedPerpetualSymbol = ref<string>('');
  const selectedSpotSymbol = ref<string>('');
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
  const canSubmit = computed(() => {
    const ready = readiness.value.ready === true;
    return ready && !submitting.value && !!selectedPerpetualSymbol.value && !!quantityInput.value;
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
      if (!quantityInput.value && next.suggestedQuantity) {
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
    positionGroups.value = await getFundingPositionGroups();
  }

  async function refreshInstruction() {
    if (!pendingDraft.value?.instructionId) return;
    const response = await getFundingInstructionWorkspace(pendingDraft.value.instructionId);
    activeInstruction.value = response.instruction;
    activeWorkspace.value = response.workspaceState ?? null;
    const state = normalizeWorkspaceState(response.workspaceState);
    if (isFundingTerminalState(state)) {
      clearFundingDraft();
      pendingDraft.value = null;
    } else if (pendingDraft.value) {
      pendingDraft.value = { ...pendingDraft.value, state: state as FundingPendingDraft['state'] };
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
      state: 'submitting',
    };
    draft.action = action;
    draft.perpetualSymbol = selectedPerpetualSymbol.value;
    draft.spotSymbol = selectedSpotSymbol.value;
    draft.quantity = quantityInput.value;
    writeFundingDraft(draft);
    pendingDraft.value = draft;
    try {
      const response = await submitFundingInstruction({
        action,
        idempotencyKey: draft.idempotencyKey,
        perpetualSymbol: draft.perpetualSymbol,
        spotSymbol: draft.spotSymbol,
        quantity: draft.quantity,
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
        clearFundingDraft();
        pendingDraft.value = null;
      }
      await refreshPositionGroups();
      return response;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : 'Funding instruction submit failed';
      throw caught;
    } finally {
      submitting.value = false;
    }
  }

  function selectSymbol(perpetualSymbol: string, spotSymbol: string) {
    selectedPerpetualSymbol.value = perpetualSymbol;
    selectedSpotSymbol.value = spotSymbol;
  }

  return {
    loading,
    submitting,
    error,
    context,
    positionGroups,
    selectedPerpetualSymbol,
    selectedSpotSymbol,
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
    submit,
    selectSymbol,
  };
}
