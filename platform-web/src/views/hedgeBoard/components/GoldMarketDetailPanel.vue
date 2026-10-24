<template>
  <p role="status">{{ statusText }}</p>
  <TerminalDetailPanel
    class="terminal-detail-panel--embedded"
    title="市场明细 · 90日曲线仅使用真实历史"
    market-id="gold"
    :columns="config.detailColumns"
    :groups="groups"
    :rotation-button-label="config.rotationButtonLabel"
    :rotation-heatmap="rotationRows"
  />
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { getMarketDetail, type MarketDetailResponse } from '@/api/hedgeResearch';
  import {
    mergeLiveMarketDetail,
    mergeTerminalMarket,
    prepareCommodityMarketDetail,
  } from '../nativeData/marketDetailAdapter';
  import { marketTerminalConfigs, type TerminalTableGroup } from '../nativeData/marketTerminal';
  import TerminalDetailPanel from './TerminalDetailPanel.vue';

  const config = marketTerminalConfigs.gold;
  const groups = ref<TerminalTableGroup[]>(prepareCommodityMarketDetail(config.detailGroups));

  const snapshot = ref<MarketDetailResponse | null>(null);
  const failed = ref(false);
  const loading = ref(true);
  const statusText = computed(() =>
    loading.value
      ? '正在读取数据…'
      : failed.value || snapshot.value?.status === 'error'
      ? '数据暂不可用'
      : snapshot.value?.status === 'stale'
      ? '当前显示最近保留的数据'
      : snapshot.value?.status === 'partial'
      ? '部分数据暂不可用'
      : !snapshot.value?.rows.length
      ? '暂无数据'
      : `数据日期：${snapshot.value.asOf ?? '—'}`,
  );
  const rotationRows = computed(
    () => mergeTerminalMarket(config, snapshot.value?.rows ?? []).rotationHeatmap ?? [],
  );

  onMounted(async () => {
    try {
      const response = await getMarketDetail('gold');
      snapshot.value = response;
      groups.value = mergeLiveMarketDetail(config.detailGroups, response.rows);
    } catch (error) {
      failed.value = true;
      console.warn('[hedgeBoard] gold market detail unavailable', error);
    } finally {
      loading.value = false;
    }
  });
</script>
