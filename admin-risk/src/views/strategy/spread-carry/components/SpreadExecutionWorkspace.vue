<template>
  <template v-if="variant === 'crossVenue'">
    <div class="spread-workspace__legacy-design">
      <CrossVenueExecutionReplica
        :selected-venue="selectedVenue"
        :left-leg-symbol="leftLegSymbol"
        :right-leg-symbol="rightLegSymbol"
        :selected-resolution="selectedResolution"
      />
    </div>
    <CrossSpreadMarketLifecyclePanel
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
    />
  </template>
  <DomesticOverseasExecutionReplica
    v-else
    :selected-venue="selectedVenue"
    :left-leg-symbol="leftLegSymbol"
    :right-leg-symbol="rightLegSymbol"
    :selected-resolution="selectedResolution"
  />
</template>

<script setup lang="ts">
  import CrossSpreadMarketLifecyclePanel from './CrossSpreadMarketLifecyclePanel.vue';
  import CrossVenueExecutionReplica from './CrossVenueExecutionReplica.vue';
  import DomesticOverseasExecutionReplica from './DomesticOverseasExecutionReplica.vue';
  import type { SpreadWorkspaceVariant } from '../types';

  withDefaults(
    defineProps<{
      variant?: SpreadWorkspaceVariant;
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
    }>(),
    {
      variant: 'crossVenue',
      selectedVenue: 'Bybit',
      leftLegSymbol: 'XAUTUSDT.P',
      rightLegSymbol: 'XAUUSD+',
      selectedResolution: '30分钟',
    },
  );
</script>

<style scoped lang="less">
  .spread-workspace__legacy-design {
    position: relative;
  }

  .spread-workspace__legacy-design :deep(.cross-card--execution) {
    position: relative;
    pointer-events: none;
  }

  .spread-workspace__legacy-design :deep(.cross-card--execution::after) {
    position: absolute;
    inset: 0;
    z-index: 4;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 10px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.18);
    color: #526885;
    content: '原市价 / 限价设计保留；真实市价执行请使用下方运行区';
    font-size: 12px;
    font-weight: 700;
  }
</style>
