<template>
  <section class="history-panel">
    <header
      ><h3>{{ pairId === 'cross-gold' ? '历史价格' : '标的价格与资费走势' }}</h3
      ><div class="controls"
        ><a
          v-if="pairId === 'funding-btc'"
          class="external-link"
          href="https://www.coinglass.com/zh/FundingRate"
          target="_blank"
          rel="noopener noreferrer"
          >coinglass资费</a
        ><label v-if="pairId === 'funding-btc'"
          >标的<select v-model="selectedSymbol">
            <option v-for="item in symbolOptions" :key="item" :value="item">{{ item }}</option>
          </select></label
        ><div v-if="pairId === 'funding-btc'" class="resolution-tabs" aria-label="资费精度">
          <button
            v-for="item in resolutionOptions"
            :key="item.value"
            type="button"
            :class="{ active: selectedResolution === item.value }"
            @click="selectedResolution = item.value"
            >{{ item.label }}</button
          > </div
        ><button
          v-for="n in [1, 7, 30]"
          :key="n"
          :disabled="loading"
          :class="{ active: days === n }"
          @click="
            days = n;
            load();
          "
          >近 {{ n }} 日</button
        ><label><input v-model="follow" type="checkbox" />自动接续更新</label
        ><button :disabled="loading" @click="load">刷新本地历史</button></div
      ></header
    >
    <p v-if="loading" role="status">读取已归档历史…</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <div ref="chartRef" class="history-chart"></div>
    <details v-if="pairId === 'funding-btc'"
      ><summary>历史结算明细与来源</summary
      ><div class="table-scroll"
        ><table
          ><thead
            ><tr><th>结算时间</th><th>费率（小数）</th><th>价格现金流口径</th></tr></thead
          ><tbody
            ><tr
              v-for="r in data?.data?.settlements || []"
              :key="r.payload?.fundingRateTimestamp ?? r.timeMs"
              ><td>{{
                r.payload?.fundingRateTimestamp
                  ? new Date(Number(r.payload.fundingRateTimestamp)).toLocaleString()
                  : '未知'
              }}</td
              ><td>{{ r.payload?.fundingRate ?? '未知' }}</td
              ><td>结算 mark 未证实时，现金流未知</td></tr
            ></tbody
          ></table
        ></div
      ></details
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, onUnmounted, ref, watch, type Ref } from 'vue';
  import { useKeepAliveActive } from '@/hooks/web/useKeepAliveActive';
  import { researchHistory, type ResearchResponse } from '@/api/platform/strategyResearch';
  import { useECharts } from '@/hooks/web/useECharts';

  const props = withDefaults(
    defineProps<{
      pairId: 'funding-btc' | 'cross-gold';
      symbols?: string[];
      symbol?: string;
      resolution?: '1h' | '8h' | '1d';
    }>(),
    { symbols: () => ['BTC'], symbol: 'BTC', resolution: '1h' },
  );
  const emit = defineEmits<{
    (e: 'update:symbol', value: string): void;
    (e: 'update:resolution', value: '1h' | '8h' | '1d'): void;
  }>();
  const days = ref(1),
    follow = ref(true),
    loading = ref(false),
    error = ref('');
  const symbolOptions = computed(() =>
    Array.from(new Set(props.symbols?.length ? props.symbols : ['BTC'])),
  );
  const selectedSymbol = ref(props.symbol),
    resolutionOptions = [
      { value: '1h' as const, label: '1H' },
      { value: '8h' as const, label: '8H' },
      { value: '1d' as const, label: '日' },
    ],
    selectedResolution = ref<'1h' | '8h' | '1d'>(props.resolution);
  const data = ref<ResearchResponse>();
  const chartRef = ref<HTMLDivElement>();
  const chart = useECharts(chartRef as Ref<HTMLDivElement>);
  const pageActive = useKeepAliveActive();
  let timer: ReturnType<typeof setTimeout> | undefined,
    stopped = false;
  watch(
    () => props.symbol,
    (value) => {
      selectedSymbol.value = value;
    },
  );
  watch(
    () => props.resolution,
    (value) => {
      selectedResolution.value = value;
    },
  );
  watch(symbolOptions, (options) => {
    if (!options.includes(selectedSymbol.value)) selectedSymbol.value = options[0] || 'BTC';
  });
  watch(selectedSymbol, (value) => emit('update:symbol', value));
  watch(selectedResolution, (value) => emit('update:resolution', value));
  async function load() {
    if (loading.value || !pageActive.value) return;
    loading.value = true;
    error.value = '';
    const pair = props.pairId;
    try {
      const end = Date.now();
      const result = await researchHistory(
        pair,
        new Date(end - days.value * 86400000).toISOString(),
        new Date(end).toISOString(),
        selectedSymbol.value,
        selectedResolution.value,
      );
      if (!stopped && pair === props.pairId) {
        data.value = result;
        render();
      }
    } catch {
      error.value = '历史暂时读取失败；保留上次结果。回补进度可在采集状态查看。';
    } finally {
      loading.value = false;
    }
  }
  function render() {
    const prepared = (data.value?.data?.chartSeries || []) as Array<{
      name: string;
      type: string;
      selected: boolean;
      axis: number;
      data: unknown[];
    }>;
    const selected: Record<string, boolean> = {};
    const previous = (chart.getInstance()?.getOption()?.legend as any)?.[0]?.selected || {};
    const series: any[] = prepared.map((s) => {
      selected[s.name] = previous[s.name] ?? s.selected;
      return {
        name: s.name,
        type: s.type,
        yAxisIndex: s.axis,
        showSymbol: false,
        connectNulls: false,
        symbolSize: 2,
        barMaxWidth: 8,
        data: s.data,
        ...(s.type === 'bar'
          ? { itemStyle: { color: (p: any) => (Number(p.value[1]) >= 0 ? '#2db87c' : '#cf3f4f') } }
          : {}),
      };
    });
    const escape = (v: unknown) =>
      String(v).replace(
        /[&<>"']/g,
        (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!),
      );
    void chart.setOptions({
      color: ['#d79a1e', '#507bda', '#2db87c', '#cf3f4f', '#a373c2'],
      tooltip: {
        trigger: 'axis',
        formatter: (items: any) => {
          const rows = Array.isArray(items) ? items : [items];
          return rows.length
            ? escape(new Date(Number(rows[0].value[0])).toLocaleString()) +
                '<br/>' +
                rows
                  .map(
                    (p) =>
                      `${escape(p.seriesName)}：${escape(
                        p.data?.exactPrice ?? p.value[1] ?? '缺数据',
                      )}`,
                  )
                  .join('<br/>')
            : '';
        },
      },
      legend: { type: 'scroll', selected },
      grid: { left: 75, right: 80, top: 50, bottom: 75 },
      xAxis: { type: 'time' },
      yAxis: [
        { type: 'value', scale: true, name: '价格' },
        {
          type: 'value',
          name: props.pairId === 'funding-btc' ? '资金费率 (%)' : '',
          show: props.pairId === 'funding-btc',
          scale: true,
        },
      ],
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 18, bottom: 10 }],
      series,
    });
  }
  async function refresh() {
    if (follow.value && !document.hidden) await load();
    if (!stopped && pageActive.value) {
      if (timer) clearTimeout(timer);
      timer = setTimeout(refresh, 60000);
    }
  }
  watch(pageActive, (active) => {
    if (active) {
      void refresh();
    } else if (timer) {
      clearTimeout(timer);
      timer = undefined;
    }
  });
  onUnmounted(() => {
    stopped = true;
    if (timer) clearTimeout(timer);
  });
  watch(
    () => props.pairId,
    () => {
      data.value = undefined;
      void load();
    },
  );
  watch([selectedSymbol, selectedResolution], () => {
    if (props.pairId === 'funding-btc') void load();
  });
</script>
<style scoped lang="less">
  .history-panel {
    min-width: 0;
    padding: var(--strategy-space-4);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  header,
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  select {
    min-height: 34px;
    padding: 6px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
  }

  .resolution-tabs {
    display: inline-flex;
    gap: 4px;
  }

  h3 {
    margin: 0;
    font-size: var(--strategy-font-section-title);
  }

  button {
    padding: 8px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    cursor: pointer;
  }

  button.active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .external-link {
    display: inline-flex;
    align-items: center;
    min-height: 34px;
    padding: 8px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: inherit;
    text-decoration: none;
  }

  .external-link:hover,
  .external-link:focus-visible {
    border-color: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .history-chart {
    height: 420px;
  }

  p {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .table-scroll {
    max-height: 300px;
    overflow: auto;
  }

  table {
    width: 100%;
    text-align: left;
  }

  td,
  th {
    padding: 8px;
    border-bottom: 1px solid var(--strategy-border-soft);
  }

  label {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  @media (max-width: 600px) {
    .history-chart {
      height: 320px;
    }
  }
</style>
