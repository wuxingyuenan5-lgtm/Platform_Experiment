<template>
  <TerminalDetailPanel
    class="terminal-detail-panel--embedded"
    title="市场明细 · 90日曲线仅使用真实历史"
    market-id="gold"
    :columns="config.detailColumns"
    :groups="groups"
    :rotation-button-label="config.rotationButtonLabel"
    :rotation-heatmap="config.rotationHeatmap"
  />
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import { getMarketDetail } from '@/api/hedgeResearch';
  import {
    mergeLiveMarketDetail,
    prepareCommodityMarketDetail,
  } from '../nativeData/marketDetailAdapter';
  import { marketTerminalConfigs, type TerminalTableGroup } from '../nativeData/marketTerminal';
  import TerminalDetailPanel from './TerminalDetailPanel.vue';

  const config = marketTerminalConfigs.gold;
  const groups = ref<TerminalTableGroup[]>(prepareCommodityMarketDetail(config.detailGroups));

  onMounted(async () => {
    try {
      const response = await getMarketDetail('gold');
      groups.value = mergeLiveMarketDetail(config.detailGroups, response.rows);
    } catch (error) {
      console.warn('[hedgeBoard] gold market detail unavailable', error);
    }
  });
</script>
