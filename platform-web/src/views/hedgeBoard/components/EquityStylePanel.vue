<template>
  <section class="style-workbench" aria-label="风格轮动">
    <header class="style-heading">
      <div
        ><h3>市场在奖励什么风格</h3><p>ETF价格表现 · 20日相对表现以{{ benchmark }}为基准</p></div
      >
      <select v-model="order" aria-label="风格排序"
        ><option value="return20">近20日</option
        ><option value="return5">近5日</option
        ><option value="return1">当日</option
        ><option value="relative20">20日相对基准</option></select
      >
    </header>
    <div class="style-table" tabindex="0" role="region" aria-label="风格ETF比较">
      <table
        ><thead
          ><tr
            ><th>风格 / 工具</th><th>当日</th><th>5日</th><th>20日</th><th>20日超额</th
            ><th>数据日期</th></tr
          ></thead
        >
        <tbody
          ><tr
            v-for="row in sorted"
            :key="row.code"
            :class="{ selected: selectedCode === row.code && chartMode === 'etf' }"
          >
            <th
              ><button @click="selectEtf(row.code)"
                >{{ row.name }} <span>{{ row.code }}</span></button
              ><small>{{ row.scope }}</small></th
            >
            <td :class="tone(row.return1)">{{ fmt(row.return1) }}</td
            ><td :class="tone(row.return5)">{{ fmt(row.return5) }}</td
            ><td :class="tone(row.return20)">{{ fmt(row.return20) }}</td
            ><td :class="tone(row.relative20)">{{ fmt(row.relative20, 'pp') }}</td
            ><td>{{ row.date || '—' }}<small v-if="row.status !== 'ready'">待更新</small></td> </tr
          ><tr v-if="!sorted.length"><td colspan="6">暂无风格数据</td></tr></tbody
        >
      </table>
    </div>
    <header class="pair-heading"
      ><h3>风格相对强弱</h3><span>左侧风格减右侧 · 20日收益差</span></header
    >
    <div class="pair-grid" role="group" aria-label="风格相对组合">
      <button
        v-for="pair in data?.pairs || []"
        :key="pair.name"
        :aria-pressed="chartMode === 'pair' && activePair?.name === pair.name"
        @click="selectPair(pair.name)"
      >
        <span>{{ pair.name }}</span
        ><strong :class="tone(pair.spread20)">{{ fmt(pair.spread20, 'pp') }}</strong
        ><small>{{ pair.numerator }} / {{ pair.denominator }}</small>
      </button>
    </div>
    <section class="style-chart" aria-label="风格走势">
      <header class="style-heading"
        ><div
          ><h3>{{ chartTitle }}</h3
          ><p>{{
            chartMode === 'pair'
              ? `相对价格比值，${chartPoints[0]?.date || '基期'}=100；上升表示左侧风格相对走强。`
              : `ETF价格，${chartPoints[0]?.date || '基期'}=100。`
          }}</p></div
        ><a
          v-if="chartMode === 'etf' && activeEtf"
          :href="activeEtf.url"
          target="_blank"
          rel="noopener noreferrer"
          >产品与方法 ↗</a
        ></header
      >
      <VibeTimeChart
        v-if="chartPoints.some((p) => p.value != null)"
        :key="`${market}:${chartMode}:${chartTitle}`"
        :title="chartTitle"
        y-label="基期=100"
        :initial-window="125"
        :dates="chartPoints.map((p) => p.date)"
        :series="[
          {
            name: chartTitle,
            color: '#2864ec',
            type: 'line',
            values: chartPoints.map((p) => num(p.value)),
          },
        ]"
      />
      <p v-else class="empty">历史不足或窗口首日缺失，暂不能计算相对走势。</p>
    </section>
    <details class="method"
      ><summary>风格口径</summary
      ><p
        >ETF是风格代理，存在行业、规模与多因子交叉暴露；这里比较价格表现，不是纯因子多空收益或组合因子归因。超额和收益差以百分点（pp）表示，走势图为价格比值归一化，二者含义不同。</p
      ><p
        >{{
          market === 'cn'
            ? 'A股使用来源复权价格；成长与价值工具样本空间不同，动量成长及红利低波均为混合策略。央企属于所有制维度。'
            : '美股使用收盘价格，不含分红再投资；红利工具的价格回报不等于含分红总回报。'
        }}
        缺失交易日不补零。</p
      ></details
    >
  </section>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import type { EquityThemes, EquityValue, EquityStyle } from '@/api/equityObservatory';
  import { useResearchViewState } from '../composables/researchWorkspace';
  import VibeTimeChart from '../aShare/components/VibeTimeChart.vue';

  const props = defineProps<{
    data: EquityThemes['styles'];
    benchmark: string;
    market: 'cn' | 'us';
  }>();
  const order = useResearchViewState('style-order', 'return20');
  const selectedCode = useResearchViewState('style-etf', '');
  const selectedPair = useResearchViewState('style-pair', '');
  const chartMode = useResearchViewState('style-chart-mode', 'pair');
  const num = (v: EquityValue | undefined) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const fmt = (v: EquityValue | undefined, unit = '%') =>
    num(v) == null ? '—' : `${num(v)!.toFixed(2)}${unit}`;
  const tone = (v: EquityValue | undefined) =>
    num(v) == null || num(v) === 0 ? '' : num(v)! > 0 ? 'positive' : 'negative';
  const sorted = computed(() =>
    [...(props.data?.items || [])].sort((a, b) => {
      const av = num(a[order.value as keyof EquityStyle] as EquityValue),
        bv = num(b[order.value as keyof EquityStyle] as EquityValue);
      return av == null ? (bv == null ? 0 : 1) : bv == null ? -1 : bv - av;
    }),
  );
  const activeEtf = computed(
    () => props.data?.items.find((r) => r.code === selectedCode.value) || props.data?.items[0],
  );
  const activePair = computed(
    () => props.data?.pairs.find((r) => r.name === selectedPair.value) || props.data?.pairs[0],
  );
  const chartTitle = computed(() =>
    chartMode.value === 'pair'
      ? activePair.value?.name || '相对走势'
      : `${activeEtf.value?.name || ''} · ${activeEtf.value?.code || ''}`,
  );
  const chartPoints = computed(() => {
    if (chartMode.value === 'pair') return activePair.value?.history || [];
    const points = activeEtf.value?.history || [],
      first = num(points[0]?.value);
    return points.map((p) => ({
      date: p.date,
      value: first && num(p.value) != null ? (num(p.value)! / first) * 100 : null,
    }));
  });
  function selectEtf(code: string) {
    selectedCode.value = code;
    chartMode.value = 'etf';
  }
  function selectPair(name: string) {
    selectedPair.value = name;
    chartMode.value = 'pair';
  }
</script>
<style scoped>
  .style-heading,
  .pair-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
    gap: 16px;
  }

  h3,
  p {
    margin: 0;
  }

  h3 {
    color: #26364b;
    font-size: 17px;
    font-weight: 650;
  }

  p,
  .pair-heading span {
    color: #66758a;
    font-size: 12px;
    line-height: 1.8;
  }

  select {
    padding: 7px 10px;
    border: 1px solid #dce5ee;
    border-radius: 8px;
    background: #fff;
    color: #40536b;
    font: inherit;
  }

  .style-table {
    margin-bottom: 28px;
    overflow: auto;
    border: 1px solid #dce5ee;
    border-radius: 12px;
    background: #fff;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 13px 16px;
    border-bottom: 1px solid #edf1f5;
    text-align: right;
  }

  th:first-child {
    text-align: left;
  }

  thead {
    background: #f2f6fb;
    color: #66758a;
    font-size: 12px;
  }

  tbody th {
    min-width: 250px;
    font-weight: 500;
    white-space: normal;
  }

  tbody tr:nth-child(even) {
    background: #f9fbfd;
  }

  tbody tr.selected {
    background: #edf4ff;
  }

  button {
    font: inherit;
    cursor: pointer;
  }

  tbody button {
    padding: 0;
    border: 0;
    background: none;
    color: #26364b;
    font-weight: 650;
    text-align: left;
  }

  tbody button span {
    margin-left: 8px;
    color: #8090a4;
    font-size: 11px;
  }

  small {
    display: block;
    margin-top: 5px;
    color: #8090a4;
    font-size: 11px;
    font-weight: 400;
  }

  .positive {
    color: #c84b55;
  }

  .negative {
    color: #168779;
  }

  .pair-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 10px;
    margin-bottom: 24px;
  }

  .pair-grid button {
    display: grid;
    grid-template-columns: 1fr auto;
    padding: 14px;
    border: 1px solid #dce5ee;
    border-radius: 10px;
    background: #fff;
    color: #40536b;
    font-size: 12px;
    text-align: left;
    gap: 8px;
  }

  .pair-grid button[aria-pressed='true'] {
    border-color: #86aafa;
    background: #edf4ff;
  }

  .pair-grid small {
    grid-column: 1/-1;
    margin: 0;
  }

  .pair-grid strong {
    font-variant-numeric: tabular-nums;
  }

  .style-chart {
    padding: 20px;
    border: 1px solid #dce5ee;
    border-radius: 12px;
    background: #fff;
  }

  .style-chart a {
    color: #2864ec;
    font-size: 12px;
  }

  .empty {
    padding: 50px;
    text-align: center;
  }

  .method {
    margin-top: 20px;
    color: #66758a;
    font-size: 12px;
  }

  .method summary {
    cursor: pointer;
  }

  .method p {
    margin-top: 8px;
  }

  button:focus-visible,
  select:focus-visible {
    outline: 2px solid #2864ec;
    outline-offset: 3px;
  }

  @media (max-width: 680px) {
    .style-heading {
      flex-direction: column;
      align-items: flex-start;
    }

    .style-chart {
      padding: 12px;
    }

    .pair-grid {
      grid-template-columns: 1fr 1fr;
    }
  }
</style>
