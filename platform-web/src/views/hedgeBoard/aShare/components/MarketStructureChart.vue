<template>
  <ChartExpand title="市场涨跌结构" @expanded-change="expanded = $event">
    <article class="market-structure-chart">
      <header
        ><h3>市场涨跌结构</h3>
        <div class="ranges" role="group" aria-label="市场涨跌结构历史范围">
          <button
            v-for="item in ranges"
            :key="item.value"
            type="button"
            :class="{ active: range === item.value }"
            :aria-pressed="range === item.value"
            @click="range = item.value"
            >{{ item.label }}</button
          >
        </div>
      </header>
      <div v-if="!rows.length" class="empty">暂无市场涨跌历史数据</div>
      <div
        v-show="rows.length"
        ref="element"
        class="plot"
        :class="{ 'is-expanded': expanded }"
        role="img"
        :aria-label="`市场涨跌结构，${rows[0]?.date || '—'}至${
          rows.at(-1)?.date || '—'
        }，可拖动下方时间范围并悬浮查看数值`"
      ></div>
    </article>
  </ChartExpand>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../../components/ChartExpand.vue';
  import {
    buildMarketStructureOptions,
    structureRows,
    type MarketStructureRow,
    type MarketStructureRange,
  } from './marketStructureChart';

  const props = defineProps<{ rows: MarketStructureRow[] }>();
  const rows = computed(() => structureRows(props.rows));
  const range = ref<MarketStructureRange>(90);
  const expanded = ref(false);
  const ranges = [
    { value: 90, label: '近90日' },
    { value: 365, label: '1年' },
    { value: 1095, label: '3年' },
    { value: 0, label: '全部' },
  ] as const;
  const element = ref<HTMLDivElement | null>(null);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  watch(
    [rows, range],
    async ([data, selected], previous) => {
      await nextTick();
      const current = chart.getInstance()?.getOption();
      const options = buildMarketStructureOptions(data, selected);
      const zoom = (current?.dataZoom as Array<{ start?: number; end?: number }> | undefined)?.[0];
      if (previous?.[1] === selected && zoom && Array.isArray(options.dataZoom))
        options.dataZoom = options.dataZoom.map((item) => ({
          ...item,
          startValue: undefined,
          endValue: undefined,
          start: zoom.start,
          end: zoom.end,
        }));
      const selectedLegends = (
        current?.legend as Array<{ selected?: Record<string, boolean> }> | undefined
      )?.[0]?.selected;
      if (selectedLegends && !Array.isArray(options.legend))
        options.legend = { ...options.legend, selected: selectedLegends };
      chart.setOptions(options, true);
    },
    { immediate: true },
  );
</script>
<style scoped>
  .market-structure-chart {
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    padding-right: 30px;
    gap: 12px;
  }

  h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 14px;
  }

  .ranges {
    display: flex;
    gap: 6px;
  }

  .ranges button {
    padding: 4px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
    color: var(--strategy-text-3);
    font-size: 12px;
    cursor: pointer;
  }

  .ranges button.active {
    border-color: var(--strategy-accent-strong);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .plot {
    width: 100%;
    min-width: 0;
    height: 380px;
  }

  .empty {
    padding: 40px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  .plot.is-expanded {
    height: calc(100vh - 160px);
  }
</style>
