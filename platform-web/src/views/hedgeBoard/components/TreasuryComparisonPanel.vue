<template>
  <div class="treasury-comparison">
    <div class="controls" role="group" aria-label="美债收益率与期限利差范围">
      <button
        v-for="n in [1, 3, 5, 10, 0]"
        :key="n"
        :aria-pressed="years === n"
        @click="years = n"
        >{{ n ? `${n}年` : '全部' }}</button
      >
    </div>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-else-if="!series.length">正在读取美债历史…</p>
    <div v-show="series.length && !error">
      <div
        ref="element"
        class="plot"
        role="img"
        aria-label="上图DFF及3个月、2年、10年、30年美债收益率，下图2Y减3M、10Y减2Y、30Y减10Y期限利差，共用时间轴和缩放"
      ></div>
      <div class="sources"
        ><a
          v-for="s in series"
          :key="s.seriesId"
          :href="s.sourceUrl || undefined"
          target="_blank"
          rel="noreferrer"
          >{{ label(s.seriesId) }} · {{ s.observationDate || '暂无日期'
          }}{{ s.isStale ? ' · 待更新' : '' }}</a
        ></div
      >
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, shallowRef, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { getMacroDashboardV1, type MacroDashboardSeries } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { useResearchViewState } from '../composables/researchWorkspace';
  import {
    buildTreasuryComparisonOptions,
    TREASURY_LINES,
  } from '../charts/treasuryComparisonOptions';

  const years = useResearchViewState('treasury-comparison:years', 5);
  const series = shallowRef<MacroDashboardSeries[]>([]),
    error = ref('');
  const element = ref<HTMLDivElement | null>(null);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const label = (id: string) => TREASURY_LINES.find((l) => l[0] === id)?.[1] || id;
  useDashboardRefresh(async () => {
    try {
      const dashboard = await getMacroDashboardV1();
      series.value = dashboard.groups.treasuryComparison || [];
      error.value = series.value.length ? '' : '美债历史暂不可用';
    } catch {
      error.value = '美债历史读取失败';
    }
  });
  const plotted = computed(() => {
    const cutoff = years.value
      ? new Date(Date.now() - years.value * 366 * 86400000).toISOString().slice(0, 10)
      : '';
    return series.value.map((s) => ({
      ...s,
      observations: s.observations.filter((o) => o.date >= cutoff),
    }));
  });
  watch(
    plotted,
    async () => {
      await nextTick();
      if (element.value)
        chart.setOptions(buildTreasuryComparisonOptions(plotted.value) as EChartsOption, true);
    },
    { immediate: true },
  );
</script>
<style scoped>
  .controls {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  button {
    padding: 5px 10px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: #fff;
    color: #3e5b76;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    background: #edf4ff;
    color: #165dff;
  }

  .plot {
    width: 100%;
    min-width: 0;
    height: 680px;
  }

  .chart-expand__surface[aria-modal='true'] .plot {
    height: calc(100vh - 200px);
    min-height: 400px;
  }

  .sources {
    display: flex;
    flex-wrap: wrap;
    margin-top: 12px;
    font-size: 11px;
    gap: 8px 18px;
  }

  .sources a {
    color: #65809b;
  }

  @media (max-width: 600px) {
    .plot {
      height: 570px;
    }
  }
</style>
