<template>
  <TerminalDetailPanel
    class="terminal-detail-panel--embedded"
    title="市场明细"
    market-id="macro"
    :columns="config.detailColumns"
    :groups="groups"
  />
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue';

  import { getMarketDetail } from '@/api/hedgeResearch';

  import { marketTerminalConfigs, type TerminalTableGroup } from '../nativeData/marketTerminal';
  import {
    mergeMacroMarketDetail,
    prepareMacroMarketDetail,
  } from '../nativeData/marketDetailAdapter';
  import TerminalDetailPanel from './TerminalDetailPanel.vue';

  const config = marketTerminalConfigs.macro;
  const groups = ref<TerminalTableGroup[]>(prepareMacroMarketDetail(config.detailGroups));

  onMounted(async () => {
    try {
      const response = await getMarketDetail('macro');
      groups.value = mergeMacroMarketDetail(config.detailGroups, response.rows);
    } catch (error) {
      console.warn('[hedgeBoard] macro market detail unavailable', error);
    }
  });
</script>
