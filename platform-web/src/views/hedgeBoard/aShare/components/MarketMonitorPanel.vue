<template>
  <section class="monitor" :class="{ 'monitor--embedded': embedded }" :aria-label="sectionTitle">
    <header v-if="!embedded && tab !== 'fund'"
      ><h2>{{ sectionTitle }}</h2></header
    >
    <p v-if="loading && !contextSection && tab !== 'style'" role="status"
      >正在读取{{ sectionTitle }}…</p
    >
    <p v-if="error && !contextSection && tab !== 'style'" role="alert"
      >{{ error }} <button @click="load(true)">重试</button></p
    >
    <MarketContextPanel v-if="contextSection" :section="contextSection" :refresh-key="refreshKey" />
    <template v-if="tab !== 'style' && tab !== 'fund' && !contextSection && data">
      <div v-if="tab !== 'congestion' && tab !== 'growth'" class="source"
        ><span>{{ sourceDate }}</span
        ><a :href="source?.sourceUrl" target="_blank" rel="noopener noreferrer">来源 ↗</a></div
      >
      <p v-if="source?.status === 'error'" class="notice">来源本轮更新失败，保留上次有效数据。</p>
    </template>
    <template v-if="tab === 'dividend'">
      <div class="cards"
        ><button
          v-for="r in items('dividend')"
          :key="r.code"
          :class="{ active: dividend === r.code }"
          @click="dividend = r.code"
          ><span>{{ r.name }}</span
          ><strong>{{ fmt(last(r.history)?.value) }}%</strong
          ><small>{{ last(r.history)?.date }}</small></button
        ></div
      >
      <FinancingChart
        v-if="selectedDividend"
        :key="dividend"
        :title="`${selectedDividend.name} · 股息率`"
        :rows="selectedDividend.history || []"
        :lines="dividendLines"
      />
      <p v-if="dividendWarnings.length" class="notice"
        >来源异常待复核：{{
          dividendWarnings.join('、')
        }}
        出现单日大幅变化并于次日恢复；图中保留原值。</p
      >
      <p class="definition">板块整体股息率；具体宽基指数股息率可在“估值”中切换查看。</p>
    </template>
    <template v-else-if="tab === 'fund'">
      <FinancingChart
        v-if="data"
        :title="`${fundNames[fund]} · 估算仓位`"
        :rows="rows('fund_' + fund)"
        :lines="[
          { key: 'value', name: '估算股票仓位', color: '#2864ec', unit: '%' },
          { key: 'close', name: '沪深300', color: '#171717', unit: '点', right: true },
        ]"
        allow-table
      >
        <template #toolbar>
          <div class="fund-estimate-controls">
            <label
              >基金类型
              <select v-model="fund" aria-label="基金类型">
                <option value="stock">股票型</option>
                <option value="pingheng">平衡混合型</option>
                <option value="linghuo">灵活配置型</option>
              </select>
            </label>
            <span
              >{{ sourceDate || '暂无观测'
              }}<template v-if="source?.status === 'error'"> · 更新失败</template></span
            >
            <a
              v-if="source?.sourceUrl"
              :href="source.sourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              >来源 ↗</a
            >
          </div>
        </template>
      </FinancingChart>
    </template>
    <template v-else-if="tab === 'style'">
      <p v-if="styleError" role="alert"
        >{{ styleError }} <button @click="loadStyles">重试</button></p
      >
      <EquityStylePanel
        v-if="themes"
        market="cn"
        :data="themes.styles"
        :benchmark="themes.benchmark?.name || '沪深300'"
      />
      <p v-else-if="!styleError" role="status">正在读取风格数据…</p>
    </template>
    <FinancingChart
      v-else-if="tab === 'growth' && data"
      :title="
        growthView === 'comparison' ? '申万一级行业景气对照' : `全A · ${metrics[metric]}中位数`
      "
      :rows="growthView === 'comparison' ? growthBars : rows('growth')"
      :lines="growthView === 'comparison' ? growthLines : growthTrendLines"
      :category-axis="growthView === 'comparison'"
      allow-table
    >
      <template #range-controls>
        <div v-if="!industryCode" class="growth-views" role="group" aria-label="景气视图">
          <button
            v-for="view in growthViews"
            :key="view.key"
            type="button"
            :aria-pressed="growthView === view.key"
            @click="growthView = view.key"
            >{{ view.label }}</button
          >
        </div>
        <select v-model="metric" class="growth-filter" aria-label="景气指标">
          <option v-for="(name, key) in metrics" :key="key" :value="key">{{ name }}</option>
        </select>
        <input
          v-if="growthView === 'comparison' && !industryCode"
          v-model="query"
          class="growth-filter growth-search"
          aria-label="筛选行业"
          placeholder="行业名称"
        />
        <a
          v-if="source?.sourceUrl"
          class="growth-source"
          :href="source.sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          >来源 ↗</a
        >
      </template>
      <template v-if="growthView === 'comparison'" #data-table>
        <div
          class="table-scroll growth-table"
          role="region"
          aria-label="行业景气对照数据"
          tabindex="0"
        >
          <table>
            <thead>
              <tr>
                <th scope="col">申万一级行业</th>
                <th scope="col">{{ growthItems[0]?.date || '本期' }}</th>
                <th scope="col">{{ growthItems[0]?.previousDate || '上期' }}</th>
                <th scope="col" :aria-sort="growthSort ? 'descending' : 'ascending'">
                  <button type="button" @click="growthSort = !growthSort">
                    同比变化（pp） {{ growthSort ? '↓' : '↑' }}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in growthPageItems" :key="row.code">
                <th scope="row">{{ row.name }}</th>
                <td :class="tone(row.value)">{{
                  row.value == null ? '—' : fmt(row.value) + '%'
                }}</td>
                <td>{{ row.previous == null ? '—' : fmt(row.previous) + '%' }}</td>
                <td :class="tone(row.change)">{{ fmt(row.change) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <nav class="growth-pages" aria-label="行业景气数据分页">
          <span>{{ growthItems.length }} 条</span>
          <button type="button" :disabled="growthPage === 1" @click="growthPage--">上一页</button>
          <span>{{ growthPage }} / {{ growthPageCount }}</span>
          <button type="button" :disabled="growthPage === growthPageCount" @click="growthPage++"
            >下一页</button
          >
        </nav>
      </template>
    </FinancingChart>
    <template v-else-if="tab === 'crowding'">
      <div v-if="!industryCode" class="controls"
        ><label
          >行业
          <select v-model="industry"
            ><option v-for="r in items('industry')" :key="r.code" :value="r.code">{{
              r.name
            }}</option></select
          ></label
        ></div
      >
      <FinancingChart
        v-if="selectedIndustry"
        :key="industry"
        :title="`${selectedIndustry.name} · 交易拥挤度`"
        :rows="selectedIndustry.history || []"
        :lines="[
          { key: 'turnover', name: '等权换手率分位', color: '#2864ec', unit: '%' },
          { key: 'amount', name: '成交额占比分位', color: '#e6aa20', unit: '%' },
        ]"
      />
    </template>
    <FinancingChart
      v-else-if="tab === 'congestion' && data"
      title="成交集中度"
      :rows="rows('congestion')"
      :lines="congestionLines"
      allow-table
    >
      <template #summary>
        <div class="chart-summary-line">
          <template v-if="lastCongestion">
            <time :datetime="lastCongestion.date">截至 {{ lastCongestion.date }}</time>
            <strong>{{ pct(lastCongestion.value) }}</strong>
            <span v-if="snapshotStale" class="notice">待更新</span>
          </template>
          <span v-else>暂无有效历史读数</span>
        </div>
        <div class="chart-summary-line">
          <span v-if="source?.referenceEnd">乐咕乐股历史至 {{ source.referenceEnd }}</span>
          <span v-if="source?.platformStart">平台自算自 {{ source.platformStart }} 起</span>
        </div>
      </template>
    </FinancingChart>
    <p
      v-if="
        data && tab !== 'style' && tab !== 'congestion' && !contextSection && !source?.data?.length
      "
      class="notice"
      >当前来源暂无有效数据。</p
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import { industryCode as normalizeIndustryCode } from './industryResearch';
  import {
    getMarketMonitor,
    type MarketMonitor,
    type MonitorItem,
    type MonitorRow,
    type MonitorValue,
    MarketContextSection,
  } from '@/api/cnMarketMonitor';
  import { type EquityObservatory, type EquityThemes } from '@/api/equityObservatory';
  import { researchRequest } from '@/api/hedgeResearch';
  import FinancingChart, { type FinanceLine } from './FinancingChart.vue';
  import EquityStylePanel from '../../components/EquityStylePanel.vue';
  import MarketContextPanel from './MarketContextPanel.vue';

  const props = defineProps<{
    refreshKey?: number;
    embedded?: boolean;
    industryCode?: string;
    concentrationSnapshot?: EquityObservatory['structure'];
    snapshotStale?: boolean;
    section:
      | 'dividend'
      | 'fund'
      | 'style'
      | 'growth'
      | 'crowding'
      | 'congestion'
      | 'risk'
      | 'breadth';
  }>();
  const emit = defineEmits<{ ready: []; industry: [code: string] }>();
  const tabs = [
    { key: 'dividend', name: '股息率' },
    { key: 'fund', name: '基金仓位' },
    { key: 'style', name: '风格跟踪' },
    { key: 'growth', name: '行业景气度' },
    { key: 'crowding', name: '交易拥挤度' },
    { key: 'congestion', name: '全A交易集中度历史' },
    { key: 'risk', name: '股债性价比' },
    { key: 'breadth', name: '市场宽度' },
  ];
  const tab = computed(() => props.section);
  const sectionTitle = computed(() => {
    const name = tabs.find((t) => t.key === tab.value)!.name;
    const selectedName =
      tab.value === 'growth' ? growthItems.value[0]?.name : selectedIndustry.value?.name;
    return props.industryCode && selectedName ? `${selectedName} · ${name}` : name;
  });
  const dividend = ref('shangzheng'),
    fund = ref('stock'),
    localIndustry = ref('801080.SI');
  const industry = computed({
    get: () =>
      props.industryCode ? `${normalizeIndustryCode(props.industryCode)}.SI` : localIndustry.value,
    set: (value: string) => {
      localIndustry.value = value;
      emit('industry', normalizeIndustryCode(value));
    },
  });
  const contextSection = computed(() =>
    ['risk', 'breadth'].includes(tab.value) ? (tab.value as MarketContextSection) : null,
  );
  const metrics: Record<string, string> = {
    netProfitYoy: '净利润同比',
    orYoy: '营业收入同比',
    opYoy: '营业利润同比',
    trYoy: '营业总收入同比',
    ebtYoy: '利润总额同比',
    roeYoy: 'ROE同比增长率',
  };
  const fundNames: Record<string, string> = {
    stock: '股票型基金',
    pingheng: '平衡混合型基金',
    linghuo: '灵活配置型基金',
  };
  const metric = ref('netProfitYoy'),
    query = ref(''),
    growthSort = ref(true);
  const data = shallowRef<MarketMonitor>(),
    themes = shallowRef<Pick<EquityThemes, 'styles' | 'benchmark'>>(),
    error = ref(''),
    styleError = ref(''),
    loading = ref(false);
  let controller: AbortController | undefined;
  let styleController: AbortController | undefined;
  const rows = (key: string) => (data.value?.sources[key]?.data || []) as MonitorRow[];
  const items = (key: string) => (data.value?.sources[key]?.data || []) as MonitorItem[];
  const last = (history?: MonitorRow[]) => history?.at(-1);
  const selectedDividend = computed(() => items('dividend').find((r) => r.code === dividend.value));
  const dividendLines = computed(() => [
    { key: 'value', name: '股息率 TTM', color: '#2864ec', unit: '%' },
    ...(selectedDividend.value?.history?.some((r) => r.close != null)
      ? [{ key: 'close', name: '指数收盘', color: '#171717', unit: '点', right: true }]
      : []),
  ]);
  const dividendWarnings = computed(() => {
    const history = selectedDividend.value?.history || [];
    return history
      .filter((r, i) => {
        if (
          !i ||
          i === history.length - 1 ||
          [history[i - 1].value, r.value, history[i + 1].value].some((v) => v == null)
        )
          return false;
        const previous = Number(history[i - 1].value),
          current = Number(r.value),
          next = Number(history[i + 1].value);
        return (
          previous > 0 &&
          next > 0 &&
          Math.abs(current / previous - 1) > 0.35 &&
          Math.abs(next / previous - 1) < 0.1
        );
      })
      .map((r) => r.date);
  });
  const selectedIndustry = computed(() => items('industry').find((r) => r.code === industry.value));
  const growthItems = computed(() =>
    items('growth_' + metric.value)
      .filter((r) =>
        props.industryCode
          ? normalizeIndustryCode(r.code) === normalizeIndustryCode(props.industryCode)
          : r.name.includes(query.value),
      )
      .slice()
      .sort((a, b) => {
        if (a.change == null) return b.change == null ? 0 : 1;
        if (b.change == null) return -1;
        return (Number(b.change) - Number(a.change)) * (growthSort.value ? 1 : -1);
      }),
  );
  const growthLines: FinanceLine[] = [
    { key: 'change', name: '同比变化', color: '#2864ec', unit: 'pp', bar: true },
  ];
  const growthTrendLines = computed<FinanceLine[]>(() => [
    { key: metric.value, name: metrics[metric.value], color: '#2864ec', unit: '%' },
  ]);
  const growthBars = computed(() =>
    growthItems.value.map((row) => ({ date: row.name, change: row.change })),
  );
  const growthPage = ref(1);
  const growthView = ref<'comparison' | 'trend'>('comparison');
  const growthViews = [
    { key: 'comparison', label: '行业对照' },
    { key: 'trend', label: '全A中位数走势' },
  ] as const;
  const growthPageSize = 20;
  const growthPageCount = computed(() =>
    Math.max(1, Math.ceil(growthItems.value.length / growthPageSize)),
  );
  const growthPageItems = computed(() =>
    growthItems.value.slice(
      (growthPage.value - 1) * growthPageSize,
      growthPage.value * growthPageSize,
    ),
  );
  watch(growthItems, () => {
    growthPage.value = 1;
  });
  const source = computed(
    () =>
      data.value?.sources[
        tab.value === 'fund'
          ? 'fund_' + fund.value
          : tab.value === 'growth'
          ? 'growth_' + metric.value
          : tab.value === 'crowding'
          ? 'industry'
          : tab.value
      ],
  );
  const sourceDate = computed(() =>
    tab.value === 'dividend'
      ? last(selectedDividend.value?.history)?.date
      : tab.value === 'crowding'
      ? last(selectedIndustry.value?.history)?.date
      : tab.value === 'growth'
      ? growthItems.value[0]?.date
      : last(rows('fund_' + fund.value))?.date,
  );
  const congestionBenchmarks: FinanceLine[] = [
    { key: 'hs300', name: '沪深300', color: '#171717', unit: '点', right: true },
    {
      key: 'chinext',
      name: '创业板指',
      color: '#b57a08',
      unit: '点',
      right: true,
      defaultSelected: false,
    },
    {
      key: 'star50',
      name: '科创50',
      color: '#00976f',
      unit: '点',
      right: true,
      defaultSelected: false,
    },
  ];
  const congestionLines: FinanceLine[] = [
    { key: 'value', name: '前5%股票成交额占比', color: '#2864ec', unit: '%', markLatest: true },
    ...congestionBenchmarks,
  ];
  const lastCongestion = computed(() => rows('congestion').findLast((row) => row.value != null));
  const fmt = (v: MonitorValue | undefined, digits = 2) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? '—' : Number(v).toFixed(digits);
  const pct = (value: MonitorValue | undefined) => {
    const result = fmt(value);
    return result === '—' ? result : result + '%';
  };
  const tone = (v: MonitorValue | undefined) =>
    v == null ? '' : Number(v) > 0 ? 'positive' : Number(v) < 0 ? 'negative' : '';
  function currentKeys() {
    if (tab.value === 'dividend') return ['dividend'];
    if (tab.value === 'fund') return ['fund_' + fund.value];
    if (tab.value === 'growth') return ['growth', 'growth_' + metric.value];
    if (tab.value === 'crowding') return ['industry'];
    if (tab.value === 'congestion') return ['congestion'];
    return [];
  }
  async function load(force = false) {
    controller?.abort();
    const keys = currentKeys();
    if (!keys.length || (!force && keys.every((k) => data.value?.sources[k]))) {
      loading.value = false;
      emit('ready');
      return;
    }
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    try {
      const result = await getMarketMonitor(current.signal, keys);
      if (!current.signal.aborted)
        data.value = { ...result, sources: { ...data.value?.sources, ...result.sources } };
    } catch {
      if (!current.signal.aborted) error.value = sectionTitle.value + '读取失败';
    } finally {
      if (!current.signal.aborted) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  async function loadStyles() {
    styleController?.abort();
    const current = new AbortController();
    styleController = current;
    styleError.value = '';
    try {
      const result = await researchRequest<Pick<EquityThemes, 'styles' | 'benchmark'>>({
        method: 'GET',
        url: '/research/equity-styles/cn',
        signal: current.signal,
      });
      if (!current.signal.aborted) themes.value = result;
    } catch {
      if (!current.signal.aborted) styleError.value = '风格数据读取失败';
    }
  }
  watch(
    () => props.refreshKey,
    () => {
      data.value = undefined;
      load(true);
      if (tab.value === 'style') loadStyles();
    },
    { immediate: true },
  );
  watch([tab, fund, metric], () => {
    load();
    if (tab.value === 'style' && !themes.value) loadStyles();
  });
  onBeforeUnmount(() => {
    controller?.abort();
    styleController?.abort();
  });
</script>
<style scoped>
  .monitor.monitor--embedded {
    padding: 0;
    border: 0;
    background: transparent;
  }

  .monitor--embedded .source {
    margin: 0;
  }

  .fund-estimate-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    font-size: 12px;
    gap: 8px;
  }

  .growth-views,
  .growth-pages {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .growth-views {
    gap: 4px;
  }

  .growth-views button,
  .growth-filter {
    padding: 4px 10px;
    font-size: 12px;
  }

  .growth-search {
    width: 120px;
  }

  .growth-source {
    padding: 0 4px;
    font-size: 12px;
    white-space: nowrap;
  }

  .growth-table {
    max-height: none;
  }

  .growth-pages {
    justify-content: flex-end;
    margin: 12px 0 0;
    font-size: 12px;
  }

  .growth-pages button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  .monitor {
    min-width: 0;
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid #dce5ef;
    color: #17324d;
  }

  h2 {
    margin: 0;
    font-size: 20px;
  }

  header p,
  .definition,
  .source {
    color: #71869d;
    font-size: 12px;
  }

  nav,
  .controls,
  .source {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 16px 0;
    gap: 12px;
  }

  button,
  select,
  input {
    padding: 6px 12px;
    border: 1px solid #dce5ef;
    border-radius: 6px;
    background: white;
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button.active,
  button[aria-pressed='true'] {
    border-color: #a7c0ff;
    background: #edf3ff;
    color: #2864ec;
  }

  a {
    color: #2864ec;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .cards button {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 16px;
  }

  strong {
    font-size: 23px;
  }

  small {
    color: #71869d;
    font-size: 11px;
  }

  .table-scroll {
    max-height: 620px;
    margin: 16px 0;
    overflow: auto;
    border: 1px solid #dce5ef;
    border-radius: 10px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 10px 14px;
    border-bottom: 1px solid #edf1f5;
    text-align: right;
  }

  th:first-child {
    text-align: left;
  }

  thead {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #f4f7fb;
  }

  th button {
    padding: 0;
    border: 0;
    background: transparent;
  }

  .positive {
    color: #d84f5a;
  }

  .negative {
    color: #00976f;
  }

  .notice {
    color: #967025;
  }

  details,
  .expanded-disclosure {
    margin: 16px 0;
    padding: 16px;
    border: 1px solid #dce5ef;
    border-radius: 10px;
  }

  summary {
    cursor: pointer;
  }

  @media (max-width: 700px) {
    .cards {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    nav {
      gap: 6px;
    }

    nav button {
      padding: 6px 8px;
    }
  }

  .disclosure-title {
    margin: 0 0 12px;
    color: #354d68;
    font-size: 14px;
    font-weight: 600;
  }
</style>
