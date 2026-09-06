<template>
  <MarketTerminalPage
    :config="aShareTerminalConfig"
    :market-tabs="aShareTerminalTabs"
    detail-section-id="a-share-market-detail"
  />
</template>

<script setup lang="ts">
  import MarketTerminalPage from '../../components/MarketTerminalPage.vue';
  import { marketTerminalConfigs, type TerminalMarketId } from '../../nativeData/marketTerminal';

  const aShareTerminalConfig = marketTerminalConfigs.aShare;
  const aShareTerminalTabs: Array<{ id: TerminalMarketId; label: string; path: string }> = [
    { id: 'aShare', label: 'A股', path: '/hedge-board/a-share' },
  ];
</script>
