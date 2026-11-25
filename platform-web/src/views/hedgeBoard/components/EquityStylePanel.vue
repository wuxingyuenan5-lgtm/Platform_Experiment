<template>
  <section class="style-workbench" :class="{ 'daily-style': compact }" aria-label="风格轮动">
    <header class="style-heading">
      <div>
        <h3>{{ compact ? '风格轮动' : '市场在奖励什么风格' }}</h3>
        <p
          ><template v-if="observationDate">{{ observationDate }} 收盘 · </template>20日超额基准
          {{ benchmark }}</p
        >
      </div>
      <select v-if="!compact" v-model="order" aria-label="风格排序"
        ><option value="return20">近20日</option
        ><option value="return5">近5日</option
        ><option value="return1">当日</option
        ><option value="relative20">20日相对基准</option></select
      >
    </header>
    <div v-if="compact && dailySummary" class="style-summary" aria-label="风格收盘摘要">
      <span
        >20日超额领先 <b>{{ dailySummary.first.name }}</b>
        {{ fmt(dailySummary.first.relative20, 'pp') }}</span
      >
      <span
        >20日超额落后 <b>{{ dailySummary.last.name }}</b>
        {{ fmt(dailySummary.last.relative20, 'pp') }}</span
      >
      <span
        >跑赢{{ benchmark }}
        <b>{{ dailySummary.winners }} / {{ dailySummary.count }}</b> 个有效风格</span
      >
    </div>
    <div
      v-memo="[sorted, activeEtf, compact, compact || chartMode === 'etf', order, ascending]"
      class="style-table"
      tabindex="0"
      role="region"
      aria-label="风格ETF比较"
    >
      <table
        ><thead
          ><tr
            ><th>风格 / 工具</th
            ><th
              v-for="column in metrics"
              :key="column.key"
              :aria-sort="
                compact && order === column.key
                  ? ascending
                    ? 'ascending'
                    : 'descending'
                  : undefined
              "
            >
              <button v-if="compact" type="button" @click="sortBy(column.key)"
                >{{ column.label
                }}{{ order === column.key ? (ascending ? ' ↑' : ' ↓') : '' }}</button
              >
              <template v-else>{{ column.label }}</template> </th
            ><th>数据日期</th></tr
          ></thead
        >
        <tbody
          ><tr
            v-for="row in sorted"
            :key="row.code"
            :class="{ selected: activeEtf?.code === row.code && (compact || chartMode === 'etf') }"
            @click="compact && selectEtf(row.code)"
          >
            <th
              ><button
                type="button"
                :aria-pressed="activeEtf?.code === row.code && (compact || chartMode === 'etf')"
                @click.stop="selectEtf(row.code)"
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
    <div
      v-for="chart in shownCharts"
      :key="chart.mode"
      class="style-chart-group"
      :class="{ 'style-chart-group--paired': compact && chart.mode === 'pair' }"
    >
      <template v-if="!compact || chart.mode === 'pair'">
        <header class="pair-heading">
          <h3>风格相对强弱</h3>
          <label v-if="compact"
            >左侧减右侧 · 收益差
            <select v-model="pairWindow" aria-label="配对收益差窗口"
              ><option value="spread1">当日</option
              ><option value="spread5">5日</option
              ><option value="spread20">20日</option></select
            ></label
          >
          <span v-else>左侧风格减右侧 · 20日收益差</span>
        </header>
        <div class="pair-grid" role="group" aria-label="风格相对组合">
          <button
            v-for="pair in data?.pairs || []"
            :key="pair.name"
            type="button"
            :aria-pressed="chart.mode === 'pair' && activePair?.name === pair.name"
            @click="selectPair(pair.name)"
          >
            <span>{{ pair.name }}</span>
            <strong :class="tone(pair[compact ? pairWindow : 'spread20'])">{{
              fmt(pair[compact ? pairWindow : 'spread20'], 'pp')
            }}</strong>
            <small>{{ pair.numerator }} / {{ pair.denominator }}</small>
          </button>
        </div>
      </template>
      <section
        class="style-chart"
        :class="{ 'style-chart--rank': compact && chart.mode === 'etf' }"
        :aria-label="
          compact ? (chart.mode === 'pair' ? '风格相对走势' : 'ETF价格走势') : '风格走势'
        "
      >
        <header
          v-if="!compact || chart.mode === 'pair' || !chart.points.some((p) => p.value != null)"
          class="style-heading"
        >
          <div>
            <h3 v-if="!compact || !chart.points.some((point) => point.value != null)">{{
              chart.title
            }}</h3>
            <p v-if="!compact || chart.mode === 'pair'">{{
              chart.mode === 'pair'
                ? `相对价格比值，${chart.points[0]?.date || '基期'}=100；上升表示左侧风格相对走强。`
                : `ETF价格，${chart.points[0]?.date || '基期'}=100。`
            }}</p>
          </div>
          <a
            v-if="!compact && chart.mode === 'etf' && activeEtf"
            :href="activeEtf.url"
            target="_blank"
            rel="noopener noreferrer"
            >产品与方法 ↗</a
          >
        </header>
        <VibeTimeChart
          v-if="chart.points.some((p) => p.value != null)"
          :key="`${market}:${chart.mode}:${chart.title}`"
          :title="chart.title"
          y-label="基期=100"
          :hide-footer="compact && chart.mode === 'etf'"
          :compact-plot="compact && chart.mode === 'etf'"
          :initial-window="125"
          :dates="chart.dates"
          :series="chart.series"
        />
        <p v-else class="empty">历史不足或窗口首日缺失，暂不能计算走势。</p>
      </section>
    </div>
    <component :is="alwaysExpanded && !compact ? 'section' : 'details'" class="method"
      ><component
        :is="alwaysExpanded && !compact ? 'h3' : 'summary'"
        :class="{ 'disclosure-title': alwaysExpanded && !compact }"
        >风格口径</component
      ><p
        >ETF是风格代理，存在行业、规模与多因子交叉暴露；这里比较价格表现，不是纯因子多空收益或组合因子归因。超额和收益差以百分点（pp）表示，走势图为价格比值归一化，二者含义不同。</p
      ><p
        >{{
          market === 'cn'
            ? 'A股使用来源复权价格；成长与价值工具样本空间不同，动量成长及红利低波均为混合策略。央企属于所有制维度。'
            : '美股使用收盘价格，不含分红再投资；红利工具的价格回报不等于含分红总回报。'
        }}
        缺失交易日不补零。</p
      ></component
    >
  </section>
</template>
<script setup lang="ts">
  import { inject, computed } from 'vue';
  import type {
    EquityPoint,
    EquityThemes,
    EquityValue,
    EquityStyle,
  } from '@/api/equityObservatory';
  import { useResearchViewState } from '../composables/researchWorkspace';
  import VibeTimeChart from '../aShare/components/VibeTimeChart.vue';

  const alwaysExpanded = inject('themeResearchAlwaysExpanded', false);
  const props = defineProps<{
    data: EquityThemes['styles'];
    benchmark: string;
    compact?: boolean;
    observationDate?: string | null;
    market: 'cn' | 'us';
  }>();
  const order = props.compact
    ? useResearchViewState('breadth-style-order', 'relative20')
    : useResearchViewState('style-order', 'return20');
  const ascending = useResearchViewState('style-sort-ascending', false);
  const pairWindow = useResearchViewState<'spread1' | 'spread5' | 'spread20'>(
    'style-pair-window',
    'spread20',
  );
  const metrics = [
    { key: 'return1', label: '当日' },
    { key: 'return5', label: '5日' },
    { key: 'return20', label: '20日' },
    { key: 'relative20', label: '20日超额' },
  ];
  function sortBy(key: string) {
    if (order.value !== key) {
      order.value = key;
      ascending.value = false;
    } else if (!ascending.value) ascending.value = true;
    else {
      order.value = 'relative20';
      ascending.value = false;
    }
  }
  const selectedCode = useResearchViewState('style-etf', '');
  const selectedPair = useResearchViewState('style-pair', '');
  const chartMode = useResearchViewState<'etf' | 'pair'>('style-chart-mode', 'pair');
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
      return av == null
        ? bv == null
          ? 0
          : 1
        : bv == null
        ? -1
        : props.compact && ascending.value
        ? av - bv
        : bv - av;
    }),
  );
  const dailySummary = computed(() => {
    const comparable = (props.data?.items || [])
      .filter(
        (row) =>
          !!props.observationDate &&
          row.date === props.observationDate &&
          row.status === 'ready' &&
          num(row.relative20) != null,
      )
      .sort((a, b) => Number(b.relative20) - Number(a.relative20));
    if (comparable.length < 2) return null;
    return {
      first: comparable[0],
      last: comparable[comparable.length - 1],
      winners: comparable.filter((row) => Number(row.relative20) > 0).length,
      count: comparable.length,
    };
  });
  const activeEtf = computed(
    () =>
      props.data?.items.find((r) => r.code === selectedCode.value) ||
      (props.compact && dailySummary.value?.first) ||
      props.data?.items[0],
  );
  const activePair = computed(
    () => props.data?.pairs.find((r) => r.name === selectedPair.value) || props.data?.pairs[0],
  );
  function chartData(mode: 'etf' | 'pair', title: string, points: EquityPoint[]) {
    return {
      mode,
      title,
      points,
      dates: points.map((point) => point.date),
      series: [
        {
          name: title,
          color: '#2864ec',
          type: 'line' as const,
          values: points.map((point) => num(point.value)),
        },
      ],
    };
  }
  const etfChart = computed(() => {
    const etf = activeEtf.value;
    const points = etf?.history || [];
    const first = num(points[0]?.value);
    return chartData(
      'etf',
      etf ? `${etf.name} · ${etf.code}` : 'ETF价格走势',
      points.map((p) => ({
        date: p.date,
        value: first && num(p.value) != null ? (num(p.value)! / first) * 100 : null,
      })),
    );
  });
  const pairChart = computed(() =>
    chartData('pair', activePair.value?.name || '相对走势', activePair.value?.history || []),
  );
  const shownCharts = computed(() =>
    props.compact
      ? [etfChart.value, pairChart.value]
      : [chartMode.value === 'pair' ? pairChart.value : etfChart.value],
  );
  function selectEtf(code: string) {
    selectedCode.value = code;
    if (!props.compact) chartMode.value = 'etf';
  }
  function selectPair(name: string) {
    selectedPair.value = name;
    if (!props.compact) chartMode.value = 'pair';
  }
</script>
<style scoped>
  .daily-style {
    display: grid;
    grid-auto-columns: minmax(0, 1fr);
    align-items: start;
    min-width: 0;
    gap: 10px;
  }

  .daily-style > * {
    min-width: 0;
    margin: 0;
  }

  .daily-style .style-chart {
    padding: 12px;
    border-radius: 8px;
  }

  .daily-style .style-chart .style-heading {
    margin-bottom: 4px;
  }

  .daily-style .style-table {
    border-radius: 8px;
  }

  .daily-style th,
  .daily-style td {
    padding: 5px 8px;
  }

  .daily-style tbody th {
    min-width: 120px;
  }

  .daily-style tbody tr:has(button) {
    cursor: pointer;
  }

  .daily-style tbody tr:has(button):hover:not(.selected) {
    background: #f2f6fb;
  }

  .daily-style thead button {
    padding: 3px 0;
    border: 0;
    background: transparent;
    color: inherit;
  }

  .daily-style .style-summary {
    display: flex;
    flex-wrap: wrap;
    padding: 8px 12px;
    border-radius: 6px;
    background: #f2f6fb;
    color: #40536b;
    font-size: 13px;
    gap: 6px 24px;
    font-variant-numeric: tabular-nums;
  }

  .daily-style .pair-heading {
    justify-content: flex-start;
    gap: 12px;
  }

  .daily-style .pair-heading label {
    color: #526a82;
    font-size: 12px;
  }

  .daily-style .pair-grid button {
    padding: 8px 10px;
  }

  .style-chart-group {
    display: contents;
  }

  .daily-style > .style-chart-group--paired {
    display: grid;
    gap: 10px;
    padding: 12px;
    border: 1px solid #dce5ee;
    border-radius: 8px;
    background: #fff;
  }

  .style-chart-group--paired > .pair-heading,
  .style-chart-group--paired > .pair-grid {
    margin: 0;
  }

  .daily-style .style-chart-group--paired > .style-chart {
    padding: 0;
    border: 0;
  }

  @container style-panel (min-width: 1100px) {
    .daily-style {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .daily-style > * {
      grid-column: 1 / -1;
    }

    .daily-style > .style-table {
      grid-column: 1;
    }

    .daily-style .style-chart--rank {
      grid-column: 2;
    }
  }

  .daily-style > .style-table,
  .daily-style > .pair-grid,
  .daily-style > .method,
  .daily-style > .style-heading {
    margin-top: 0;
    margin-bottom: 0;
  }

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

  .disclosure-title {
    margin: 0 0 12px;
    color: #354d68;
    font-size: 14px;
    font-weight: 600;
  }
</style>
