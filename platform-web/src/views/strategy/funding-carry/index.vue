<template>
  <div class="funding-page" data-testid="funding-original-structure">
    <StrategyResearchWorkspace v-if="localSection === 'analysis'" pair-id="funding-btc" />

    <template v-else>
      <ResearchDraftImport
        pair-id="funding-btc"
        :disabled="submitting || !!pendingDraft"
        @apply="applyResearchDraft"
      />
      <FundingOrderPanel
        :context="context"
        :position-groups="positionGroups"
        :pending-draft="pendingDraft"
        :workspace-state="workspaceState"
        :failure-reason="activeInstruction?.failureReason"
        :submitting="submitting"
        :error="error"
        :quantity-input="quantityInput"
        :close-quantity-input="closeQuantityInput"
        :execution-policy="executionPolicy"
        :perpetual-limit-price-input="perpetualLimitPriceInput"
        :can-close="canClose"
        :notional-input="notionalInput"
        :selected-close-instruction-id="selectedCloseInstructionId"
        :selected-close-group="selectedCloseGroup"
        :can-submit="canSubmit"
        @update:notional-input="notionalInput = $event"
        @update:quantity-input="quantityInput = $event"
        @update:close-quantity-input="closeQuantityInput = $event"
        @update:execution-policy="executionPolicy = $event as FundingExecutionPolicy"
        @update:perpetual-limit-price-input="perpetualLimitPriceInput = $event"
        @refresh="refreshAll"
        @submit-open="submit('open')"
        @submit-close="submit('close')"
        @select-symbol="handleExecutionSymbolUpdate"
        @select-close-instruction="selectCloseInstruction"
        @select-close-fraction="selectCloseFraction"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue';
  import ResearchDraftImport from '../shared/ResearchDraftImport.vue';
  import type { components } from '@/api/platform/generated/strategy';
  import StrategyResearchWorkspace from '../shared/StrategyResearchWorkspace.vue';
  import FundingOrderPanel from './components/FundingOrderPanel.vue';
  import { useFundingWorkspace } from './composables/useFundingWorkspace';
  import type { FundingExecutionPolicy } from './composables/fundingExecutionRecovery';
  import type { FundingExchange, FundingSymbol } from './types';

  const props = withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedExchange?: FundingExchange;
      selectedSymbol?: FundingSymbol;
      selectedResolution?: string;
    }>(),
    {
      activeSection: 'analysis',
      selectedExchange: 'Bybit',
      selectedSymbol: 'BTC',
      selectedResolution: '30分钟',
    },
  );

  const localSection = ref(props.activeSection);
  const {
    submitting,
    error,
    context,
    positionGroups,
    pendingDraft,
    activeInstruction,
    workspaceState,
    notionalInput,
    quantityInput,
    closeQuantityInput,
    executionPolicy,
    perpetualLimitPriceInput,
    selectedCloseInstructionId,
    selectedCloseGroup,
    canSubmit,
    canClose,
    refreshAll,
    submit,
    selectSymbol,
    selectCloseInstruction,
    selectCloseFraction,
  } = useFundingWorkspace();

  function applyResearchDraft(draft: components['schemas']['DraftRequest']) {
    if (submitting.value || pendingDraft.value || draft.direction !== 'sell_spread') return;
    selectSymbol('BTCUSDT', 'BTCUSDT');
    quantityInput.value = draft.quantity;
    void refreshAll();
  }

  function handleExecutionSymbolUpdate(perpetualSymbol: string, spotSymbol: string) {
    selectSymbol(perpetualSymbol, spotSymbol);
  }

  watch(
    () => props.activeSection,
    (value) => {
      localSection.value = value;
      if (value === 'execution') refreshAll();
    },
    { immediate: true },
  );
</script>

<style lang="less">
  @import '../shared/strategy-theme.less';
</style>

<style scoped lang="less">
  .funding-page {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 0 4px 18px;
    background: var(--strategy-bg);
    color: var(--strategy-text-1);
  }
</style>
