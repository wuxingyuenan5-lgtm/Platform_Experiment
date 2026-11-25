<template>
  <section class="broad-panel" aria-label="ETF分类分析">
    <header class="workspace-heading">
      <div class="heading-copy">
        <h2>{{ widgetOnly ? widgetTitle : '宽基与行业资金分析' }}</h2>
        <span v-if="data"
          >{{ data.trackedMemberCount ?? data.members.length }} /
          {{ data.members.length }} 只已有行情 · {{ latest?.date || '暂无交易日' }}</span
        >
      </div>
      <div class="workspace-actions">
        <label
          >ETF分类
          <select
            :value="selected"
            aria-label="ETF分类"
            @change="selectGroup(($event.target as HTMLSelectElement).value)"
          >
            <optgroup
              v-for="kind in ['broad', 'sector']"
              :key="kind"
              :label="kind === 'broad' ? '宽基指数' : '行业、主题与其他'"
            >
              <option
                v-for="o in (data?.options || defaults).filter((o) => (o.kind || 'broad') === kind)"
                :key="o.key"
                :value="o.key"
                >{{ o.label }}</option
              >
            </optgroup>
          </select>
        </label>
        <label v-if="!widgetOnly && data?.singleFunds?.length"
          >单只 ETF
          <select
            :value="selectedFund"
            aria-label="单只ETF"
            @change="selectFund(($event.target as HTMLSelectElement).value)"
          >
            <option value="">集合走势</option>
            <option v-for="fund in selectableFunds" :key="fund.code" :value="fund.code"
              >{{ fund.name }} · {{ fund.code }}</option
            >
          </select>
        </label>
        <button v-if="!widgetOnly" :disabled="loading" @click="load(true)">刷新数据</button>
      </div>
    </header>
    <p v-if="error" role="alert" class="notice">{{ error }}</p>
    <p v-if="loading" role="status" class="notice">正在读取 ETF 数据…</p>
    <EtfMemberAnalysis
      v-if="!widgetOnly && selectedFund"
      :code="selectedFund"
      :range="range"
      :refresh-key="refreshKey"
      @range="range = $event"
    />
    <template v-if="data && loadedIndex === selected">
      <p
        v-if="data.trackedMemberCount != null && data.trackedMemberCount < data.members.length"
        class="notice"
      >
        本分类保留全部{{ data.members.length }}只ETF资料；图表合计包含已有行情的{{
          data.trackedMemberCount
        }}只，其余成员在明细中保留，行情缺失不计零。
      </p>
      <div v-if="!widgetOnly" class="window-cards">
        <article v-for="n in [1, 5, 20]" :key="n">
          <span>{{ n === 1 ? '最新一日' : `近${n}个交易日` }}净申赎</span>
          <strong :class="tone(summaryFlow(n))"
            >{{ amount(summaryFlow(n)) }}<small>亿元</small></strong
          >
        </article>
      </div>
      <p v-if="latest && latest.total == null" class="notice" role="status">
        {{ latest.date }} 净申赎数据未齐（{{
          latest.funds.filter((f) => f.value != null).length
        }}/{{ data.trackedMemberCount ?? data.members.length }}只），当日与包含该日的区间合计留空。
      </p>
      <p v-else-if="data.sources?.groupMarket?.status !== 'ready'" class="notice">
        部分成员来源未完成更新，保留已有交易日数据。
      </p>
      <ChartExpand v-if="widgetOnly !== 'ratio'" :title="flowTitle">
        <section class="flow-card" aria-label="宽基ETF资金图表与明细">
          <header class="card-heading">
            <h3>{{ flowTitle }}</h3>
            <nav aria-label="宽基资金展示">
              <button
                v-for="v in flowViews"
                :key="v.key"
                :aria-pressed="flowView === v.key"
                @click="flowView = v.key"
                >{{ v.label }}</button
              >
            </nav>
          </header>
          <div class="controls">
            <label
              >统计频率
              <select v-model="frequency" aria-label="宽基资金统计频率"
                ><option value="daily">日度</option
                ><option value="weekly">周度</option></select
              >
            </label>
            <nav aria-label="宽基ETF范围选择">
              <button
                v-for="item in ranges"
                :key="item.days"
                :aria-pressed="range === item.days"
                @click="range = item.days"
                >{{ item.label }}</button
              >
            </nav>
            <button
              v-if="
                flowView === 'chart' &&
                !widgetOnly &&
                selected === 'hs300' &&
                data.hasIndex !== false
              "
              :aria-pressed="showHs300MarketCapRatio"
              @click="showHs300MarketCapRatio = !showHs300MarketCapRatio"
              >头部ETF市值占比</button
            >
            <label v-if="flowView === 'details'"
              >明细指标
              <select v-model="metric" aria-label="ETF明细指标"
                ><option v-for="item in metrics" :key="item.key" :value="item.key">{{
                  item.label
                }}</option></select
              >
            </label>
          </div>
          <div class="flow-display">
            <p class="definition"
              >{{
                frequency === 'daily' ? '同日' : '周内'
              }}已跟踪ETF份额变动×价格估算；历史补采段用当日单位净值。累计份额以区间首个完整份额日{{
                shareBaselineDate ? `（${shareBaselineDate}）` : ''
              }}为基准。<span v-if="data.hasIndex !== false">指数使用实际收盘点位。</span></p
            >
            <p v-if="missingUnits" class="notice"
              >所选范围有
              {{ missingUnits }} 个期间缺少完整份额，缺失日期断线，其他日期按真实份额计算。</p
            >
            <p v-if="periods.length && !shareBaselineDate" class="notice">
              所选范围暂无完整份额，累计份额曲线留空。
            </p>
            <BroadEtfChart
              v-show="flowView === 'chart' && periods.length > 0"
              :rows="periods"
              :label="label"
              :title="flowTitle"
              :has-index="data.hasIndex !== false"
              :show-market-cap-ratio="
                !widgetOnly &&
                data.hasIndex !== false &&
                (selected !== 'hs300' || showHs300MarketCapRatio)
              "
            />
            <p v-if="flowView === 'chart' && !periods.length" class="notice">
              暂无已归档行情，成员及披露信息可在资金统计明细中查看。
            </p>
            <template v-if="flowView === 'details'">
              <div class="table-scroll">
                <table>
                  <thead
                    ><tr>
                      <th>交易日／期末</th>
                      <th v-for="member in data.members" :key="member.code"
                        >{{ member.name }}<small>{{ member.code }}</small></th
                      >
                      <th>{{ metricLabel }}合计</th><th>累计份额变动<small>亿份</small></th
                      ><th v-if="data.hasIndex !== false">指数涨跌<small>%</small></th
                      ><th v-if="data.hasIndex !== false">{{ label }}收盘<small>点</small></th>
                      <th v-if="!widgetOnly && data.hasIndex !== false"
                        >头部ETF市值占比<small>%</small></th
                      >
                    </tr></thead
                  >
                  <tbody>
                    <tr v-for="row in tableRows" :key="row.date">
                      <td>{{ row.date }}<small v-if="row.partialWeek">本周未结束</small></td>
                      <td
                        v-for="member in data.members"
                        :key="member.code"
                        :style="cellStyle(fundValue(row, member.code))"
                        >{{ amount(fundValue(row, member.code)) }}</td
                      >
                      <td class="total" :class="isFlowMetric ? tone(rowValue(row)) : ''">{{
                        amount(rowValue(row))
                      }}</td>
                      <td>{{ amount(row.cumulativeUnitsYi) }}</td
                      ><td v-if="data.hasIndex !== false" :class="tone(row.indexReturnPct)">{{
                        amount(row.indexReturnPct)
                      }}</td
                      ><td v-if="data.hasIndex !== false">{{ amount(row.indexClose) }}</td>
                      <td v-if="!widgetOnly && data.hasIndex !== false">{{
                        amount(row.marketCapRatioPct)
                      }}</td>
                    </tr>
                    <tr v-if="!tableRows.length"
                      ><td
                        :colspan="
                          data.members.length + (data.hasIndex === false ? 3 : widgetOnly ? 5 : 6)
                        "
                        class="empty"
                        >暂无符合范围的数据</td
                      ></tr
                    >
                  </tbody>
                </table>
              </div>
              <div class="pagination">
                <span>{{ currentMetric.label }} · {{ periods.length }} 个期间</span>
                <button :disabled="page === 1" @click="page--">上一页</button
                ><span>{{ page }} / {{ pages }}</span
                ><button :disabled="page >= pages" @click="page++">下一页</button>
              </div>
              <details class="member-details">
                <summary>ETF成员及持仓披露</summary>
                <div class="table-scroll"
                  ><table>
                    <thead
                      ><tr
                        ><th>ETF</th><th>分类</th><th>披露持仓占比</th><th>披露规模（亿元）</th
                        ><th>报告期</th></tr
                      ></thead
                    >
                    <tbody
                      ><tr v-for="member in data.members" :key="member.code">
                        <td
                          >{{ member.name }}<small>{{ member.code }}</small></td
                        ><td>{{ member.display_group }}</td>
                        <td>{{ amount(member.latest_combined_ratio_pct) }}%</td
                        ><td>{{ amount(member.latest_combined_value_yi) }}</td
                        ><td>{{ member.latest_report_date || '—' }}</td>
                      </tr></tbody
                    >
                  </table></div
                >
              </details>
            </template>
          </div>
        </section>
      </ChartExpand>
      <template v-if="!widgetOnly">
        <FinancingChart
          :key="selected + ':turnover'"
          :title="`${label} ETF集合成交额（估算）`"
          :rows="financeRows"
          :lines="turnoverLines"
          :range-days="range"
          @range="range = $event"
          note="同日已跟踪ETF成交额合计；任一成员缺失则合计留空。"
        />
        <FinancingChart
          :key="selected + ':etf-financing'"
          :title="`${label} ETF集合融资余额与融资净买入`"
          :rows="financeRows"
          :lines="etfFinancingLines"
          :range-days="range"
          @range="range = $event"
          :note="etfFinancingNote"
        />
        <FinancingChart
          v-if="data.hasIndex !== false"
          :key="selected + ':index-financing'"
          :title="`${label} 指数成分股融资余额与融资净买入`"
          :rows="financeRows"
          :lines="indexFinancingLines"
          :range-days="range"
          @range="range = $event"
          :note="indexFinancingNote"
        />
      </template>
      <FinancingChart
        v-if="widgetOnly === 'ratio' && data.marketCapRatio.rows?.length"
        :key="selected + ':ratio'"
        :title="`${label} · 头部ETF市值占比`"
        :rows="data.marketCapRatio.rows"
        :lines="ratioLines"
        :range-days="range"
        @range="range = $event"
      />
    </template>
  </section>
</template>
<script setup lang="ts">
  import {
    computed,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { researchRequest } from '@/api/hedgeResearch';
  import { useResearchSnapshots } from '../../composables/researchWorkspace';
  import ChartExpand from '../../components/ChartExpand.vue';
  import FinancingChart, { type FinanceLine, type FinanceRow } from './FinancingChart.vue';
  import BroadEtfChart from './BroadEtfChart.vue';
  import EtfMemberAnalysis from './EtfMemberAnalysis.vue';
  import {
    numeric,
    visiblePeriods,
    withMarketCapRatios,
    type EtfPeriod,
    type EtfFundPeriod,
  } from './broadEtfAnalysis';

  interface Member {
    code: string;
    name: string;
    display_group?: string;
    latest_combined_ratio_pct?: string | null;
    latest_combined_value_yi?: string | null;
    latest_report_date?: string;
  }
  interface Broad {
    singleFunds?: Array<{
      code: string;
      name: string;
      group: string;
      tracked: boolean;
      theme?: string;
    }>;
    options: Array<{ key: string; label: string; kind?: string }>;
    members: Member[];
    trackedMemberCount?: number;
    hasIndex?: boolean;
    daily: EtfPeriod[];
    weekly: EtfPeriod[];
    marketCapRatio: { reason: string; rows: FinanceRow[] };
    sources?: Record<string, { status?: string; fetchedAt?: string; url?: string }>;
  }
  const props = defineProps<{
    refreshKey?: number;
    widgetOnly?: 'flow' | 'details' | 'ratio';
    initialIndex?: string;
  }>();
  const emit = defineEmits<{ ready: [] }>();
  const defaults: Array<{ key: string; label: string; kind?: string }> = [
    { key: 'hs300', label: '沪深300' },
    { key: 'sse50', label: '上证50' },
    { key: 'csi500', label: '中证500' },
    { key: 'csi1000', label: '中证1000' },
    { key: 'chinext', label: '创业板' },
    { key: 'star50', label: '科创50' },
  ];
  const flowViews = [
    { key: 'chart', label: '图表' },
    { key: 'details', label: '资金统计明细' },
  ] as const;
  const flowView = ref<'chart' | 'details'>(props.widgetOnly === 'details' ? 'details' : 'chart');
  const showHs300MarketCapRatio = ref(false);
  const frequency = ref<'daily' | 'weekly'>('daily');
  const range = ref(1095);
  const ranges = [
    { days: 90, label: '3个月' },
    { days: 365, label: '1年' },
    { days: 1095, label: '3年' },
    { days: 0, label: '全部' },
  ];
  const metrics = [
    { key: 'value', total: 'total', label: '净申赎（亿元）', short: '净申赎' },
    { key: 'deltaUnitsYi', total: 'deltaUnitsYi', label: '份额变动（亿份）', short: '份额变动' },
    { key: 'unitsYi', total: 'unitsYi', label: '总份额（亿份）', short: '总份额' },
    { key: 'turnoverYi', total: 'turnoverYi', label: '成交额（估算，亿元）', short: '成交额' },
    {
      key: 'financingBalanceYi',
      total: 'financingBalanceYi',
      label: '融资余额（亿元）',
      short: '融资余额',
    },
    {
      key: 'financingNetBuyYi',
      total: 'financingNetBuyYi',
      label: '融资净买入（亿元）',
      short: '融资净买入',
    },
  ] as const;
  const metric = ref<(typeof metrics)[number]['key']>('value');
  const currentMetric = computed(() => metrics.find((m) => m.key === metric.value)!);
  const metricLabel = computed(() => currentMetric.value.short);
  const isFlowMetric = computed(() =>
    ['value', 'deltaUnitsYi', 'financingNetBuyYi'].includes(metric.value),
  );
  const selected = ref(props.initialIndex || 'hs300'),
    data = shallowRef<Broad>(),
    error = ref(''),
    loading = ref(false);
  let abort: AbortController | undefined;
  let active = true;
  let loadedKey = '';
  const snapshots = useResearchSnapshots();
  const loadedIndex = ref(selected.value);
  const selectedFund = ref('');
  const selectableFunds = computed(() =>
    (data.value?.singleFunds || []).filter((f) => f.group === selected.value),
  );
  function selectGroup(group: string) {
    selectedFund.value = '';
    selected.value = group;
  }
  function selectFund(code: string) {
    selectedFund.value = code;
  }
  async function load(force = false) {
    if (!active) {
      loadedKey = '';
      return;
    }
    abort?.abort();
    const current = new AbortController();
    abort = current;
    loading.value = true;
    error.value = '';
    const requested = selected.value;
    const days = range.value;
    const cacheKey = `broad-etf:${requested}:${days}`;
    try {
      const result =
        (!force && snapshots.get<Broad>(cacheKey)) ||
        (await researchRequest<Broad>({
          method: 'GET',
          url: `/research/a-share/broad-etfs/${requested}?days=${days}`,
          signal: current.signal,
        }));
      if (!current.signal.aborted && selected.value === requested) {
        data.value = result;
        loadedIndex.value = requested;
        loadedKey = cacheKey;
        snapshots.set(cacheKey, result);
      }
    } catch {
      if (!current.signal.aborted) error.value = '宽基统计读取失败，请重试。';
    } finally {
      if (!current.signal.aborted) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  watch(
    [selected, () => props.refreshKey, range],
    (value, previous) => load(Boolean(previous && value[1] !== previous[1])),
    { immediate: true },
  );
  onDeactivated(() => {
    active = false;
    abort?.abort();
    loading.value = false;
  });
  onActivated(() => {
    active = true;
    if (loadedKey !== `broad-etf:${selected.value}:${range.value}` && !loading.value) void load();
  });
  onBeforeUnmount(() => abort?.abort());
  const label = computed(
    () =>
      data.value?.options.find((o) => o.key === loadedIndex.value)?.label ||
      defaults.find((o) => o.key === loadedIndex.value)?.label ||
      '宽基',
  );
  const widgetTitle = computed(() =>
    props.widgetOnly === 'ratio'
      ? '头部ETF市值占比'
      : props.widgetOnly === 'details'
      ? 'ETF资金统计表'
      : 'ETF净申赎',
  );
  const flowTitle = computed(
    () =>
      `${label.value} ETF ${frequency.value === 'daily' ? '日' : '周'}净申赎与累计份额变动（估算）`,
  );
  const activeDays = computed(() => data.value?.[frequency.value] || []);
  const periods = computed(() =>
    withMarketCapRatios(
      visiblePeriods(activeDays.value, range.value),
      data.value?.marketCapRatio?.rows || [],
    ),
  );
  const shareBaselineDate = computed(
    () => periods.value.find((r) => numeric(r.unitsYi) != null)?.date,
  );
  const missingUnits = computed(
    () => periods.value.filter((r) => numeric(r.unitsYi) == null).length,
  );
  const latest = computed(() => data.value?.daily.at(-1));
  function summaryFlow(count: number) {
    const rows = data.value?.daily.slice(-count) || [];
    if (rows.length !== count || rows.some((r) => numeric(r.total) == null)) return null;
    return rows.reduce((sum, r) => sum + Number(r.total), 0);
  }
  const page = ref(1),
    pageSize = 25;
  const pages = computed(() => Math.max(1, Math.ceil(periods.value.length / pageSize)));
  watch([selected, frequency, range, metric, data], () => (page.value = 1));
  const tableRows = computed(() =>
    [...periods.value].reverse().slice((page.value - 1) * pageSize, page.value * pageSize),
  );
  const fundValue = (row: EtfPeriod, code: string) =>
    row.funds.find((f) => f.code === code)?.[metric.value as keyof EtfFundPeriod];
  const rowValue = (row: EtfPeriod) => row[currentMetric.value.total];
  const maximum = computed(() =>
    Math.max(
      1,
      ...periods.value.flatMap((r) => r.funds.map((f) => Math.abs(numeric(f[metric.value]) || 0))),
    ),
  );
  function cellStyle(value: unknown) {
    const n = numeric(value);
    if (!isFlowMetric.value || !n) return {};
    return {
      backgroundColor: `rgba(${n > 0 ? '223,75,71' : '14,159,120'},${
        0.06 + 0.3 * Math.min(1, Math.abs(n) / maximum.value)
      })`,
    };
  }
  const amount = (value: unknown) =>
    numeric(value) == null
      ? '—'
      : Number(value).toLocaleString('zh-CN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
  const tone = (value: unknown) =>
    (numeric(value) ?? 0) > 0 ? 'up' : (numeric(value) ?? 0) < 0 ? 'down' : '';
  const financeRows = computed<FinanceRow[]>(() =>
    activeDays.value.map((r) => ({ ...r, funds: undefined })),
  );
  const etfFinancingLines: FinanceLine[] = [
    { key: 'financingBalanceYi', name: 'ETF集合融资余额', color: '#2563eb', unit: '亿元' },
    {
      key: 'financingNetBuyYi',
      name: 'ETF集合融资净买入',
      color: '#c49749',
      unit: '亿元',
      bar: true,
      right: true,
    },
  ];
  const indexFinancingLines: FinanceLine[] = [
    { key: 'indexFinancingBalanceYi', name: '成分股融资余额', color: '#2563eb', unit: '亿元' },
    {
      key: 'indexFinancingNetBuyYi',
      name: '成分股融资净买入',
      color: '#c49749',
      unit: '亿元',
      bar: true,
      right: true,
    },
  ];
  const turnoverLines: FinanceLine[] = [
    { key: 'turnoverYi', name: 'ETF集合成交额', color: '#637cd0', unit: '亿元', bar: true },
  ];
  const ratioLines: FinanceLine[] = [
    { key: 'ratioPct', name: 'ETF市值 / 指数流通市值', unit: '%', color: '#2563eb' },
  ];
  const lastEtfMargin = computed(() =>
    [...(data.value?.daily || [])]
      .reverse()
      .find((r) => r.financingBalanceYi != null || r.financingNetBuyYi != null),
  );
  const lastIndexMargin = computed(() =>
    [...(data.value?.daily || [])]
      .reverse()
      .find((r) => r.indexFinancingBalanceYi != null || r.indexFinancingNetBuyYi != null),
  );
  function financingGaps(fields: Array<keyof EtfPeriod>) {
    const dates = periods.value
      .filter((row) => fields.some((field) => row[field] == null))
      .map((r) => r.date);
    return dates.length
      ? `所选范围缺少${dates.length}期完整融资记录（${dates.slice(-3).join('、')}${
          dates.length > 3 ? '等' : ''
        }），对应位置断线。`
      : '';
  }
  const etfFinancingNote = computed(
    () =>
      `已跟踪${data.value?.trackedMemberCount ?? data.value?.members.length ?? 0}只ETF${
        frequency.value === 'daily' ? '同日' : '按周'
      }合计，余额取期末、净买入按期求和；缺少任一成员则留空。来源：交易所。${
        lastEtfMargin.value ? `融资数据截至 ${lastEtfMargin.value.date}` : '暂无完整融资数据'
      }。${financingGaps(['financingBalanceYi', 'financingNetBuyYi'])}`,
  );
  const indexFinancingNote = computed(
    () =>
      `对应指数有融资数据的成分股合计，每个指数仅统计一次；来源：交易所。${
        lastIndexMargin.value
          ? `截至 ${lastIndexMargin.value.date}${
              lastIndexMargin.value.indexCoveragePct != null
                ? `，当日覆盖 ${amount(lastIndexMargin.value.indexCoveragePct)}%`
                : '，当日覆盖率未提供'
            }`
          : '暂无成分股融资数据'
      }。${financingGaps(['indexFinancingBalanceYi', 'indexFinancingNetBuyYi'])}`,
  );
</script>
<style scoped>
  .broad-panel {
    display: grid;
    gap: 16px;
    min-width: 0;
    color: var(--strategy-text-2, #354d68);
    font: inherit;
    font-variant-numeric: tabular-nums;
  }

  .workspace-heading,
  .heading-copy,
  .workspace-actions,
  .card-heading,
  .controls,
  nav,
  .pagination {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }

  .workspace-heading,
  .card-heading {
    justify-content: space-between;
  }

  .heading-copy {
    gap: 14px;
  }

  .heading-copy > span,
  .definition,
  .notice {
    color: var(--strategy-text-3, #60758f);
    font-size: 12px;
  }

  h2,
  h3 {
    margin: 0;
    color: var(--strategy-text-1, #10233d);
    font-weight: 600;
  }

  h2 {
    font-size: 17px;
  }

  h3 {
    font-size: 15px;
  }

  label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }

  button,
  select {
    padding: 5px 10px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 6px;
    background: var(--strategy-surface, #fff);
    color: inherit;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #a5bfff;
    background: var(--strategy-accent-soft, #eaf2ff);
    color: var(--strategy-accent, #1d4ed8);
  }

  button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  button:focus-visible,
  select:focus-visible,
  summary:focus-visible {
    outline: 2px solid var(--strategy-accent, #1d4ed8);
    outline-offset: 2px;
  }

  .window-cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .window-cards article {
    display: grid;
    gap: 8px;
    padding: 16px 18px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 10px;
    background: var(--strategy-surface, #fff);
  }

  .window-cards article > span {
    color: var(--strategy-text-3, #60758f);
    font-size: 12px;
  }

  .window-cards strong {
    font-size: 23px;
    font-weight: 600;
  }

  .window-cards small {
    margin-left: 6px;
    color: var(--strategy-text-3, #60758f);
    font-size: 12px;
    font-weight: 400;
  }

  .flow-card {
    min-width: 0;
    padding: 16px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 10px;
    background: var(--strategy-surface, #fff);
  }

  .card-heading {
    margin-bottom: 14px;
    padding-right: 36px;
  }

  .controls {
    gap: 14px;
    margin-bottom: 10px;
  }

  nav {
    gap: 6px;
  }

  .definition,
  .notice {
    margin: 8px 0;
    line-height: 1.6;
  }

  .plot {
    width: 100%;
    min-width: 0;
    height: 440px;
  }

  .table-scroll {
    max-width: 100%;
    overflow: auto;
  }

  table {
    width: 100%;
    min-width: 900px;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--strategy-border, #d9e3ee);
    text-align: right;
    white-space: nowrap;
  }

  th {
    background: var(--strategy-surface-2, #f7f9fc);
    color: var(--strategy-text-2, #354d68);
    font-weight: 500;
  }

  th:first-child,
  td:first-child {
    position: sticky;
    left: 0;
    background: var(--strategy-surface, #fff);
    text-align: left;
  }

  th:first-child {
    background: var(--strategy-surface-2, #f7f9fc);
  }

  td small,
  th small {
    display: block;
    margin-top: 3px;
    color: var(--strategy-text-3, #60758f);
    font-size: 11px;
    font-weight: 400;
  }

  .total {
    font-weight: 600;
  }

  .pagination {
    justify-content: flex-end;
    margin-top: 12px;
    font-size: 12px;
  }

  .pagination > span:first-child {
    margin-right: auto;
    color: var(--strategy-text-3, #60758f);
  }

  .member-details {
    margin-top: 18px;
    border-top: 1px solid var(--strategy-border, #d9e3ee);
  }

  summary {
    padding: 12px 0;
    font-size: 12px;
    cursor: pointer;
  }

  .up {
    color: var(--strategy-up, #df4b47);
  }

  .down {
    color: var(--strategy-down, #0e9f78);
  }

  .empty {
    padding: 24px;
    color: var(--strategy-text-3, #60758f);
    text-align: center;
  }

  .broad-panel :deep(.financing-chart) {
    margin: 0;
    border-radius: 10px;
    border-color: var(--strategy-border, #d9e3ee);
    background: var(--strategy-surface, #fff);
    color: var(--strategy-text-2, #354d68);
  }

  @media (max-width: 650px) {
    .window-cards {
      gap: 6px;
    }

    .window-cards article {
      padding: 12px 8px;
    }

    .window-cards strong {
      font-size: 17px;
    }

    .window-cards small {
      display: block;
      margin-left: 0;
    }

    .flow-card {
      padding: 10px;
    }

    .card-heading {
      align-items: flex-start;
      gap: 12px;
    }

    .plot {
      height: 400px;
    }
  }
</style>
