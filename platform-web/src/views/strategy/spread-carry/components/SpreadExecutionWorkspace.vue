<template>
  <template v-if="variant === 'crossVenue'">
    <div class="spread-workspace__formal-design">
      <CrossVenueExecutionWorkspace
        :selected-venue="selectedVenue"
        :left-leg-symbol="leftLegSymbol"
        :right-leg-symbol="rightLegSymbol"
        :selected-resolution="selectedResolution"
      />
    </div>
  </template>
  <ProductNotConfiguredPanel
    v-else
    title="境内外价差执行链尚未配置"
    description="当前正式Owner仅覆盖Cross Venue Workspace。境内外执行Replica已退役，不展示静态成交、随机日志或未经Runtime ACK/Fill证明的成功状态。"
    source="not-configured: domestic-overseas-runtime-owner"
  />
</template>

<script setup lang="ts">
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';
  import CrossVenueExecutionWorkspace from './CrossVenueExecutionWorkspace.vue';
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
      rightLegSymbol: 'XAUUSD.s',
      selectedResolution: '30分钟',
    },
  );
</script>

<style scoped lang="less">
  .spread-workspace__formal-design {
    position: relative;
  }
</style>
