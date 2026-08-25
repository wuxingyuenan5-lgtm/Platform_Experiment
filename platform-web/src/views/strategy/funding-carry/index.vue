<template>
  <div class="funding-page" data-testid="funding-original-structure">
    <template v-if="localSection === 'analysis'">
      <FundingMarketBoard
        :context="context"
        :loading="loading"
        :error="error"
        @refresh="refreshAll"
        @select-symbol="handleSelectSymbol"
      />

      <FundingChartPanel :context="context" :position-groups="positionGroups" />

      <FundingDetailPanel :context="context" :workspace="activeWorkspace" />
    </template>

    <template v-else>
      <FundingOrderPanel
        :context="context"
        :position-groups="positionGroups"
        :pending-draft="pendingDraft"
        :workspace-state="workspaceState"
        :submitting="submitting"
        :error="error"
        :quantity-input="quantityInput"
        :notional-input="notionalInput"
        :selected-close-instruction-id="selectedCloseInstructionId"
        :selected-close-group="selectedCloseGroup"
        :can-submit="canSubmit"
        @update:notional-input="notionalInput = $event"
        @update:quantity-input="quantityInput = $event"
        @refresh="refreshAll"
        @submit-open="submit('open')"
        @submit-close="submit('close')"
        @select-symbol="handleSelectSymbol"
        @select-close-instruction="selectCloseInstruction"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue';

  import FundingChartPanel from './components/FundingChartPanel.vue';
  import FundingDetailPanel from './components/FundingDetailPanel.vue';
  import FundingMarketBoard from './components/FundingMarketBoard.vue';
  import FundingOrderPanel from './components/FundingOrderPanel.vue';
  import { useFundingWorkspace } from './composables/useFundingWorkspace';

  const props = withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedSymbol?: string;
    }>(),
    {
      activeSection: 'analysis',
      selectedSymbol: '',
    },
  );

  const localSection = ref(props.activeSection);
  const {
    loading,
    submitting,
    error,
    context,
    positionGroups,
    pendingDraft,
    activeWorkspace,
    workspaceState,
    notionalInput,
    quantityInput,
    selectedCloseInstructionId,
    selectedCloseGroup,
    canSubmit,
    refreshAll,
    submit,
    selectSymbol,
    selectCloseInstruction,
  } = useFundingWorkspace();

  function handleSelectSymbol(perpetualSymbol: string, spotSymbol: string) {
    selectSymbol(perpetualSymbol, spotSymbol);
    refreshAll();
  }

  watch(
    () => props.activeSection,
    (value) => {
      localSection.value = value;
    },
    { immediate: true },
  );

  watch(
    () => props.selectedSymbol,
    (value) => {
      if (typeof value === 'string' && value.trim() && context.value) {
        const match = context.value.symbolOptions.find(
          (item) =>
            item.baseAsset === value.trim().toUpperCase() ||
            item.perpetualSymbol === value.trim().toUpperCase() ||
            item.spotSymbol === value.trim().toUpperCase(),
        );
        if (match) {
          selectSymbol(match.perpetualSymbol, match.spotSymbol);
        }
      }
    },
    { immediate: true },
  );

  refreshAll();
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
