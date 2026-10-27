<template>
  <section class="seasonality">
    <div class="controls" role="group" aria-label="月度统计显示设置">
      <button :aria-pressed="view === 'table'" @click="view = 'table'">月度统计</button>
      <button :aria-pressed="view === 'chart'" @click="view = 'chart'">年度走势</button>
      <label
        >起始年
        <select v-model.number="start" aria-label="月度统计起始年"
          ><option v-for="r in rows" :key="r.year" :value="r.year">{{ r.year }}</option></select
        ></label
      >
      <label
        >结束年
        <select v-model.number="end" aria-label="月度统计结束年"
          ><option v-for="r in rows.filter((r) => r.year >= start)" :key="r.year" :value="r.year">{{
            r.year
          }}</option></select
        ></label
      >
      <label v-if="view === 'chart'"><input v-model="average" type="checkbox" />平均走势</label>
    </div>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-else-if="!rows.length">正在读取价格历史…</p>
    <div
      v-show="view === 'table' && rows.length"
      class="table-scroll"
      tabindex="0"
      role="region"
      aria-label="月度收益率表"
    >
      <table
        ><thead
          ><tr
            ><th>年份</th><th v-for="m in 12" :key="m">{{ m }}月</th><th>年 / YTD</th></tr
          ></thead
        >
        <tbody
          ><tr v-for="r in [...selected].reverse()" :key="r.year"
            ><th>{{ r.year }}{{ r.partial ? ' · 截至' + r.latest.slice(5) : '' }}</th
            ><td
              v-for="(v, i) in r.months"
              :key="i"
              :style="cell(v)"
              :title="
                r.partial && i + 1 === Number(r.latest.slice(5, 7)) ? '当月截至最新交易日' : ''
              "
              >{{ fmt(v) }}</td
            ><td :style="cell(r.annual)">{{ fmt(r.annual) }}</td></tr
          >
          <tr
            ><th>平均</th><td v-for="i in 12" :key="i">{{ fmt(mean(i - 1)) }}</td
            ><td>—</td></tr
          >
          <tr
            ><th>上涨 / 下跌</th
            ><td v-for="i in 12" :key="i"
              ><span class="up">{{
                selected.filter((r) => (r.months[i - 1] ?? 0) > 0).length
              }}</span>
              /
              <span class="down">{{
                selected.filter((r) => (r.months[i - 1] ?? 0) < 0).length
              }}</span></td
            ><td
              >{{ selected.filter((r) => (r.annual ?? 0) > 0).length }} /
              {{ selected.filter((r) => (r.annual ?? 0) < 0).length }}</td
            ></tr
          ></tbody
        ></table
      >
    </div>
    <div
      v-show="view === 'chart'"
      ref="element"
      class="plot"
      role="img"
      aria-label="各年度累计收益率，按日历月对齐"
    ></div>
    <p class="source" v-if="source"
      >{{ asset === 'gold' ? 'XAUUSD · MT5' : 'BTC/USDT · Binance' }} ·
      {{ source.observations[0]?.date }} 至 {{ source.observations.at(-1)?.date }} ·
      <a :href="source.sourceUrl || undefined" target="_blank" rel="noreferrer">来源 ↗</a> ·
      月收益按相邻月末收盘计算；当月与当年为截至最新交易日，缺月不跨月计算。</p
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, shallowRef, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { researchRequest, type MacroDashboardSeries } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { seasonalRows } from '../charts/seasonality';

  const props = defineProps<{ asset: 'gold' | 'btc' }>();
  const source = shallowRef<MacroDashboardSeries>(),
    error = ref(''),
    start = ref(0),
    end = ref(9999),
    view = ref('table'),
    average = ref(false);
  const element = ref<HTMLDivElement | null>(null),
    chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const rows = computed(() => seasonalRows(source.value?.observations || []));
  const selected = computed(() =>
    rows.value.filter((r) => r.year >= start.value && r.year <= end.value),
  );
  watch(start, () => {
    end.value = Math.max(start.value, end.value);
  });
  useDashboardRefresh(async () => {
    try {
      source.value = await researchRequest<MacroDashboardSeries>({
        method: 'GET',
        url: `/research/seasonality/${props.asset}`,
      });
      if (!start.value) {
        start.value = rows.value[0]?.year || 0;
        end.value = rows.value.at(-1)?.year || 9999;
      }
      error.value = '';
    } catch {
      error.value = '价格历史读取失败，请刷新重试';
    }
  });
  const fmt = (v: number | null) => (v == null ? '—' : `${v.toFixed(2)}%`);
  const cell = (v: number | null) =>
    v == null
      ? {}
      : {
          background:
            v > 0 ? 'rgba(17,150,108,0.14)' : v < 0 ? 'rgba(224,66,76,0.14)' : 'transparent',
          color: v > 0 ? '#07835e' : v < 0 ? '#c43545' : 'inherit',
        };
  function mean(i: number) {
    const a = selected.value.flatMap((r) => (r.months[i] == null ? [] : [r.months[i] as number]));
    return a.length ? a.reduce((x, y) => x + y, 0) / a.length : null;
  }
  watch(
    [selected, view, average],
    async () => {
      await nextTick();
      if (view.value !== 'chart' || !selected.value.length) return;
      const days = Array.from({ length: 366 }, (_, i) =>
        new Date(Date.UTC(2000, 0, i + 1)).toISOString().slice(5, 10),
      );
      const series = selected.value
        .filter((r) => r.curve.length)
        .flatMap((r) => {
          const chunks: Array<typeof r.curve> = [[]];
          for (const p of r.curve) {
            const last = chunks.at(-1)!.at(-1);
            if (
              last &&
              Date.parse(`2000-${p.date}T00:00:00Z`) - Date.parse(`2000-${last.date}T00:00:00Z`) >
                7 * 86400000
            )
              chunks.push([]);
            chunks.at(-1)!.push(p);
          }
          return chunks.map((chunk) => {
            const map = new Map(chunk.map((p) => [p.date, p.value]));
            return {
              name: String(r.year),
              type: 'line' as const,
              showSymbol: false,
              connectNulls: true,
              data: days.map((d) => map.get(d) ?? null),
              lineStyle: { width: r.partial ? 3 : 1.4 },
            };
          });
        });
      if (average.value)
        series.push({
          name: '平均',
          type: 'line',
          showSymbol: false,
          connectNulls: false,
          data: days.map((_, i) => {
            const a = series.flatMap((s) => (s.data[i] == null ? [] : [s.data[i] as number]));
            return a.length ? a.reduce((x, y) => x + y, 0) / a.length : null;
          }),
          lineStyle: { width: 3 },
        });
      chart.setOptions(
        {
          animation: false,
          backgroundColor: 'transparent',
          tooltip: {
            trigger: 'axis',
            valueFormatter: (v: unknown) => (v == null ? '—' : `${Number(v).toFixed(2)}%`),
          },
          legend: { type: 'scroll' },
          grid: { left: 60, right: 75, top: 45, bottom: 65 },
          xAxis: {
            type: 'category',
            data: days,
            axisLabel: {
              interval: (_index: number, d: string) => d.endsWith('-01'),
              formatter: (d: string) => `${Number(d.slice(0, 2))}月`,
            },
          },
          yAxis: {
            type: 'value',
            scale: true,
            position: 'right',
            axisLabel: { formatter: '{value}%' },
          },
          dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 10 }],
          series,
        } as EChartsOption,
        true,
      );
    },
    { deep: true },
  );
</script>
<style scoped>
  .seasonality {
    color: #17364d;
    font-family: inherit;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 16px;
    font-size: 12px;
    gap: 10px;
  }

  button,
  select {
    padding: 5px 9px;
    border: 1px solid #d9e4ee;
    border-radius: 6px;
    background: white;
    color: inherit;
    font: inherit;
  }

  button[aria-pressed='true'] {
    background: #edf4ff;
    color: #165dff;
  }

  .table-scroll {
    overflow: auto;
  }

  table {
    width: 100%;
    min-width: 950px;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 11px 7px;
    border: 1px solid #e3eaf1;
    text-align: right;
    white-space: nowrap;
  }

  th {
    background: #f5f8fc;
  }

  .up {
    color: #07835e;
  }

  .down {
    color: #c43545;
  }

  .plot {
    width: 100%;
    height: 460px;
  }

  .source {
    margin-top: 12px;
    color: #70879d;
    font-size: 11px;
  }
</style>
