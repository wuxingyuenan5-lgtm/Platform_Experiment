<template>
  <section class="spread-carry-page">
    <CrossVenueExecutionWorkspace
      v-if="variant === 'crossVenue' && activeSection === 'execution'"
      :selected-venue="selectedVenue"
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
      :selected-resolution="selectedResolution"
    />
    <ProductNotConfiguredPanel
      v-else
      title="跨所价差研究数据链尚未配置"
      description="当前正式Owner仅覆盖Cross Venue Runtime执行Workspace。价差历史、境内外研究图表及Replica没有正式Provider，因此不展示静态曲线、静态仓位数值或未经Runtime事实证明的结论。"
      source="not-configured: spread-research-provider"
    />
  </section>
</template>

<script setup lang="ts">
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';
  import CrossVenueExecutionWorkspace from './components/CrossVenueExecutionWorkspace.vue';
  import type { SpreadWorkspaceVariant } from './types';

  withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
      variant?: SpreadWorkspaceVariant;
    }>(),
    {
      activeSection: 'analysis',
      selectedVenue: 'Bybit',
      leftLegSymbol: 'XAUTUSDT.P',
      rightLegSymbol: 'XAUUSD.s',
      selectedResolution: '30分钟',
      variant: 'crossVenue',
    },
  );
</script>

<style scoped lang="less">
  .spread-carry-page {
    display: flex;
    flex-direction: column;
    min-width: 0;
    padding: 0 4px 18px;
  }
</style>
