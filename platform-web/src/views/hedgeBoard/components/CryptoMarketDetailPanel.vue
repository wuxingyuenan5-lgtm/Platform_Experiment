<template>
  <TerminalDetailPanel
    class="terminal-detail-panel--embedded"
    title="市场明细 · 90日曲线仅使用真实历史"
    market-id="crypto"
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
    prepareCryptoMarketDetail,
  } from '../nativeData/marketDetailAdapter';
  import { marketTerminalConfigs, type TerminalTableGroup } from '../nativeData/marketTerminal';
  import TerminalDetailPanel from './TerminalDetailPanel.vue';

  const config = marketTerminalConfigs.crypto;
  const groups = ref<TerminalTableGroup[]>(prepareCryptoMarketDetail(config.detailGroups));

  onMounted(async () => {
    try {
      const response = await getMarketDetail('crypto');
      groups.value = mergeLiveMarketDetail(config.detailGroups, response.rows);
    } catch (error) {
      console.warn('[hedgeBoard] crypto market detail unavailable', error);
    }
  });
</script>
