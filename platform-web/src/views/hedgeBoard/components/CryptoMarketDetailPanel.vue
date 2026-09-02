<template>
  <TerminalDetailPanel
    class="terminal-detail-panel--embedded"
    title="市场明细 · Binance Venue · not Aggregate"
    market-id="crypto"
    :columns="config.detailColumns"
    :groups="groups"
    :rotation-button-label="config.rotationButtonLabel"
    :rotation-heatmap="[]"
  />
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue';

  import { getCryptoDashboardV1 } from '@/api/hedgeResearch';

  import {
    mergeCryptoMarketDetail,
    prepareCryptoMarketDetail,
  } from '../nativeData/marketDetailAdapter';
  import { marketTerminalConfigs, type TerminalTableGroup } from '../nativeData/marketTerminal';
  import TerminalDetailPanel from './TerminalDetailPanel.vue';

  const config = marketTerminalConfigs.crypto;
  const groups = ref<TerminalTableGroup[]>(prepareCryptoMarketDetail(config.detailGroups));

  onMounted(async () => {
    try {
      const response = await getCryptoDashboardV1();
      groups.value = mergeCryptoMarketDetail(
        config.detailGroups,
        response.groups.binanceSpot ?? [],
      );
    } catch (error) {
      console.warn('[hedgeBoard] crypto market detail unavailable', error);
    }
  });
</script>
