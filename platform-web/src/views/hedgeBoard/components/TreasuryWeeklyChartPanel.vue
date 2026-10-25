<template>
  <div class="treasury-weekly">
    <div class="treasury-weekly__controls">
      <button
        v-for="preset in presets"
        :key="preset.label"
        :aria-pressed="range === preset.label"
        @click="selectRange(preset.label, preset.months)"
        >{{ preset.label }}</button
      >
      <label
        >开始
        <input
          v-model="start"
          type="date"
          :min="weeks[0]?.weekDate"
          :max="end"
          @change="range = ''"
      /></label>
      <label
        >结束
        <input
          v-model="end"
          type="date"
          :min="start"
          :max="weeks.at(-1)?.weekDate"
          @change="range = ''"
      /></label>
      <button :aria-pressed="table" @click="table = !table">{{
        table ? '查看图表' : '查看数据'
      }}</button>
    </div>
    <p v-if="failed">数据暂不可用{{ weeks.length ? '，保留上次有效数据。' : '。' }}</p>
    <p v-else-if="!weeks.length">{{ loading ? '正在加载数据…' : '暂无周度数据。' }}</p>
    <div v-if="latest" class="treasury-weekly__summary">
      <span
        >单周总净流入 <strong>{{ latest.netFlowDisplay }}</strong></span
      >
      <span
        >单周比特币总净流入
        <strong>{{ latest.netBtc === null ? '—' : latest.netBtcDisplay + ' BTC' }}</strong></span
      >
      <span
        >比特币价格 <strong>{{ latest.btcPriceDisplay }}</strong></span
      >
      <span>{{ latest.weekDate }}</span>
    </div>
    <div
      v-show="weeks.length && !table"
      ref="chartRef"
      class="treasury-weekly__chart"
      role="img"
      aria-label="BTC财库公司周度净流入：公司堆叠柱、BTC净流入和价格曲线。拖动下方时间轴缩放，悬停查看周度总额和公司分项，点击图例显示或隐藏序列。"
    ></div>
    <div v-if="table" class="treasury-weekly__table">
      <table>
        <thead
          ><tr
            ><th>周度日期</th><th>总净流入（USD）</th><th>BTC净流入</th><th>BTC价格（USD）</th
            ><th>公司分项</th></tr
          ></thead
        >
        <tbody
          ><tr v-for="week in visibleWeeks" :key="week.weekDate">
            <td>{{ week.weekDate }}</td
            ><td>{{ week.netFlowDisplay }}</td
            ><td>{{ week.netBtc === null ? '—' : week.netBtcDisplay }}</td
            ><td>{{ week.btcPriceDisplay }}</td>
            <td
              ><details
                ><summary>{{ week.companies.length }} 家公司</summary
                ><div v-for="company in week.companies" :key="company.name"
                  >{{ company.name }}：{{ company.display }}</div
                ></details
              ></td
            >
          </tr></tbody
        >
      </table>
    </div>
    <a
      href="https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow"
      target="_blank"
      rel="noopener noreferrer"
      >来源：SoSoValue · 周度 ↗</a
    >
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { getTreasuryWeeklyHistory, type TreasuryWeeklyRow } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { buildTreasuryWeeklyOptions } from '../charts/treasuryWeeklyOptions';

  const weeks = ref<TreasuryWeeklyRow[]>([]);
  const loading = ref(true);
  const failed = ref(false);
  const table = ref(false);
  const start = ref('');
  const end = ref('');
  const range = ref('全部');
  const presets = [
    { label: '近90日', months: 3 },
    { label: '1年', months: 12 },
    { label: '3年', months: 36 },
    { label: '全部', months: 0 },
  ];
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  const visibleWeeks = computed(() =>
    weeks.value.filter((w) => w.weekDate >= start.value && w.weekDate <= end.value),
  );
  const latest = computed(() => visibleWeeks.value.at(-1));
  function selectRange(label: string, months: number) {
    range.value = label;
    end.value = weeks.value.at(-1)?.weekDate || '';
    if (!end.value) return;
    const date = new Date(end.value + 'T00:00:00Z');
    date.setUTCMonth(date.getUTCMonth() - months);
    start.value = months ? date.toISOString().slice(0, 10) : weeks.value[0].weekDate;
  }
  watch([weeks, start, end], () => {
    if (!weeks.value.length) return;
    chart.setOptions(
      buildTreasuryWeeklyOptions(weeks.value, start.value, end.value) as EChartsOption,
    );
  });
  useDashboardRefresh(async () => {
    try {
      const data = await getTreasuryWeeklyHistory();
      failed.value = data.status === 'unavailable';
      // Unchanged refreshes must not reset a user's zoom or legend selection.
      if (data.status === 'ready' && JSON.stringify(data.weeks) !== JSON.stringify(weeks.value)) {
        weeks.value = data.weeks;
        if (!start.value) selectRange('全部', 0);
      }
    } catch {
      failed.value = true;
    } finally {
      loading.value = false;
    }
  });
</script>
<style scoped>
  .treasury-weekly {
    min-width: 0;
    font: inherit;
  }

  .treasury-weekly__controls,
  .treasury-weekly__summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }

  button,
  input {
    padding: 4px 8px;
    border: 1px solid #dbe4ea;
    border-radius: 5px;
    background: transparent;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    background: #edf4ff;
    color: #2563eb;
  }

  .treasury-weekly__summary {
    color: #64748b;
    font-size: 12px;
  }

  strong {
    margin-left: 4px;
    color: #173342;
  }

  .treasury-weekly__chart {
    width: 100%;
    height: 520px;
  }

  .treasury-weekly__table {
    max-height: 520px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  td,
  th {
    padding: 8px;
    border-bottom: 1px solid #e3eaf2;
    text-align: left;
    vertical-align: top;
    white-space: nowrap;
  }

  summary {
    cursor: pointer;
  }

  p,
  a {
    font-size: 12px;
  }
</style>
