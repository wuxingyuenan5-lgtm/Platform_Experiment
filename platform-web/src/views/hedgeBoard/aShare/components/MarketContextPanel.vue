<template>
  <section
    class="context"
    :class="{
      'context--compact': section !== 'breadth' || !!breadthPart,
    }"
    :aria-label="titles[section]"
  >
    <p v-if="loading" role="status">正在读取{{ titles[section] }}…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <template v-if="document">
      <template v-if="section === 'risk'">
        <FinancingChart
          v-for="chart in riskCharts"
          :key="chart.key + riskIndex"
          :title="chart.title"
          :rows="riskRows"
          :lines="chart.lines"
          :axis-names="chart.axisNames"
          :range-days="0"
          hide-ranges
          allow-table
        >
          <template #range-controls>
            <label class="risk-index"
              >指数
              <select v-model="riskIndex">
                <option v-for="(name, code) in riskNames" :key="code" :value="code">{{
                  name
                }}</option>
              </select>
            </label>
            <button
              v-for="years in historyRanges"
              :key="years"
              type="button"
              :class="{ active: riskYears === years }"
              :aria-pressed="riskYears === years"
              @click="riskYears = years"
              >{{ years ? `${years}年` : '全部' }}</button
            >
          </template>
        </FinancingChart>
        <p v-if="!latestRisk" class="notice context-notice">暂无同日有效数据。</p>
        <p v-else-if="lagged(riskIndex, 'erpTtm')" class="notice context-notice"
          >股债差更新至 {{ latestRisk.date }}。</p
        >
      </template>
      <template v-else-if="section === 'breadth'">
        <template v-if="breadthPart !== 'history'">
          <div class="below-book-summary">
            <h3>破净比例</h3>
            <div class="below-book-options">
              <button
                v-for="item in belowBookMetrics"
                :key="item.key"
                type="button"
                :class="{ active: market === item.key }"
                :aria-pressed="market === item.key"
                @click="market = item.key"
              >
                <span>{{ item.name }}</span>
                <strong>{{ item.row ? fmt(item.row.value) + '%' : '—' }}</strong>
                <time v-if="!belowBookDate && item.row" :datetime="item.row.date">{{
                  item.row.date
                }}</time>
              </button>
            </div>
            <time v-if="belowBookDate" :datetime="belowBookDate">{{ belowBookDate }}</time>
            <span
              v-if="selectedBelowBook?.count != null && selectedBelowBook?.total != null"
              class="below-book-sample"
              title="破净口径：0 < PB < 1，净资产为负的公司不计入破净数量"
              >{{ fmt(selectedBelowBook.count, 0) }} /
              {{ fmt(selectedBelowBook.total, 0) }} 只破净</span
            >
          </div>
          <FinancingChart
            v-if="rows('below_' + market).length"
            :key="market"
            :title="`${markets[market]} · 破净比例`"
            :rows="breadthPart === 'belowBook' ? belowBookRows : rows('below_' + market)"
            :range-days="breadthPart === 'belowBook' ? 0 : undefined"
            :hide-ranges="breadthPart === 'belowBook'"
            :lines="[
              { key: 'value', name: '破净比例', color: '#2864ec', unit: '%' },
              {
                key: 'close',
                name: market === 'all' ? '参考指数' : markets[market],
                color: '#171717',
                unit: '点',
                right: true,
              },
            ]"
          >
            <template v-if="breadthPart === 'belowBook'" #range-controls>
              <button
                v-for="years in belowBookRanges ?? historyRanges"
                :key="years"
                type="button"
                :class="{ active: belowBookYears === years }"
                :aria-pressed="belowBookYears === years"
                @click="belowBookYears = years"
                >{{ years ? `${years}年` : '全部' }}</button
              >
            </template>
          </FinancingChart>
          <SourceState
            :source="document.sources['below_' + market]"
            :rows="rows('below_' + market)"
          />
        </template>
        <div v-if="breadthPart === 'history'" class="breadth-history-grid">
          <div v-for="chart in breadthCharts" :key="chart.key" class="breadth-history-card">
            <FinancingChart
              :title="chart.title"
              :rows="rows(chart.key)"
              :lines="chart.lines"
              :alternate="breadthRanks?.[chart.key]"
              primary-label="市场广度"
              allow-table
            >
              <template v-if="chart.key === 'highlow'" #range-controls>
                <div class="history-controls">
                  <select v-model="highLowPeriod" aria-label="观察窗口">
                    <option :value="20">20日</option>
                    <option :value="60">60日</option>
                    <option :value="120">120日</option>
                  </select>
                </div>
              </template>
              <template #summary>
                <div v-if="chart.key === 'ma'" class="chart-summary-line">
                  <template v-if="breadthSnapshot">
                    <time :datetime="breadthSnapshot.date">收盘 {{ breadthSnapshot.date }}</time>
                    <span
                      >上涨<strong>{{
                        breadthSnapshot.valid ? fmt(breadthSnapshot.advancing, 0) : '—'
                      }}</strong></span
                    >
                    <span
                      >下跌<strong>{{
                        breadthSnapshot.valid ? fmt(breadthSnapshot.declining, 0) : '—'
                      }}</strong></span
                    >
                    <span
                      >平盘<strong>{{
                        breadthSnapshot.valid ? fmt(breadthSnapshot.unchanged, 0) : '—'
                      }}</strong></span
                    >
                    <span
                      >上涨占比<strong>{{
                        breadthSnapshot.valid
                          ? fmt((breadthSnapshot.advancing / breadthSnapshot.valid) * 100) + '%'
                          : '—'
                      }}</strong></span
                    >
                    <span v-if="snapshotStale" class="notice">待更新</span>
                  </template>
                  <span v-else>暂无当日涨跌</span>
                </div>
                <div class="chart-summary-line">
                  <template v-if="chart.latest">
                    <time :datetime="chart.latest.date">历史截至 {{ chart.latest.date }}</time>
                    <span v-for="line in chart.lines" :key="line.key">
                      {{ line.name
                      }}<strong>{{ historyValue(chart.latest[line.key], line.unit) }}</strong>
                    </span>
                  </template>
                  <span v-else>暂无有效历史读数</span>
                </div>
              </template>
            </FinancingChart>
            <SourceState
              :source="document.sources[chart.key]"
              :rows="rows(chart.key)"
              hide-source
            />
          </div>
        </div>
        <template v-else-if="breadthPart !== 'belowBook'">
          <div>
            <h3 v-if="!breadthPart">全A · 均线宽度</h3>
            <div class="cards"
              ><article v-for="period in [5, 20, 60]" :key="period"
                ><span>收盘价高于{{ period }}日均线</span
                ><strong>{{ fmt(latest('ma', 'ma' + period)?.['ma' + period], 0) }}%</strong
                ><small>{{ latest('ma', 'ma' + period)?.date || '暂无有效日期' }}</small></article
              ></div
            >
            <p class="notice" v-if="lagged('ma', 'ma20')"
              >公开来源均线统计截至 {{ latest('ma', 'ma20')?.date }}，其后暂无公开统计值。</p
            >
            <FinancingChart
              v-if="rows('ma').length"
              title="全A · 站上均线的股票比例"
              :rows="rows('ma')"
              allow-table
              :lines="[
                { key: 'ma5', name: '高于5日均线', color: '#2864ec', unit: '%' },
                { key: 'ma20', name: '高于20日均线', color: '#00976f', unit: '%' },
                { key: 'ma60', name: '高于60日均线', color: '#d09a14', unit: '%' },
              ]"
            />
            <SourceState :source="document.sources.ma" :rows="rows('ma')" />
          </div>
          <div>
            <div v-if="!breadthPart" class="controls"
              ><h3>全A · 创新高 / 新低</h3
              ><label
                >观察窗口
                <select v-model="highLowPeriod"
                  ><option :value="20">20日</option
                  ><option :value="60">60日</option
                  ><option :value="120">120日</option></select
                ></label
              ></div
            >
            <div class="cards"
              ><article
                ><span>{{ highLowPeriod }}日新高</span
                ><strong
                  >{{
                    fmt(latest('highlow', 'high' + highLowPeriod)?.['high' + highLowPeriod], 0)
                  }}只</strong
                ><small>{{ latest('highlow', 'high' + highLowPeriod)?.date }}</small></article
              ><article
                ><span>{{ highLowPeriod }}日新低</span
                ><strong
                  >{{
                    fmt(latest('highlow', 'low' + highLowPeriod)?.['low' + highLowPeriod], 0)
                  }}只</strong
                ><small>{{ latest('highlow', 'low' + highLowPeriod)?.date }}</small></article
              ><article
                ><span>新高 − 新低</span
                ><strong
                  >{{
                    fmt(latest('highlow', 'net' + highLowPeriod)?.['net' + highLowPeriod], 0)
                  }}只</strong
                ><small>同日数量差</small></article
              ></div
            >
            <p v-if="lagged('highlow', 'high20')" class="notice"
              >公开来源新高新低统计截至
              {{ latest('highlow', 'high20')?.date }}，其后暂无公开统计值。</p
            >
            <FinancingChart
              v-if="rows('highlow').length"
              :key="highLowPeriod"
              title="全A · 创新高与创新低数量"
              :rows="rows('highlow')"
              allow-table
              :lines="[
                {
                  key: 'high' + highLowPeriod,
                  name: '创新高',
                  color: '#d84f5a',
                  unit: '只',
                  bar: true,
                },
                {
                  key: 'low' + highLowPeriod,
                  name: '创新低',
                  color: '#00976f',
                  unit: '只',
                  bar: true,
                },
              ]"
            />
            <SourceState :source="document.sources.highlow" :rows="rows('highlow')" />
          </div>
          <p class="definition"
            >均线和新高新低均为来源的全A统计、剔除停牌股，区别于股票池样本广度。</p
          >
        </template>
      </template>
      <template v-else>
        <FinancingChart
          v-if="buffettRows.length"
          :key="buffettYears"
          title="巴菲特指标 · 总市值 / GDP"
          :rows="buffettRows"
          :range-days="0"
          hide-ranges
          :lines="[
            { key: 'value', name: '总市值 / GDP', color: '#2864ec', unit: '%' },
            { key: 'close', name: '沪深300', color: '#171717', unit: '点', right: true },
          ]"
        >
          <template #range-controls>
            <button
              v-for="years in historyRanges"
              :key="years"
              type="button"
              :class="{ active: buffettYears === years }"
              :aria-pressed="buffettYears === years"
              @click="buffettYears = years"
              >{{ years ? `${years}年` : '全部' }}</button
            >
          </template>
        </FinancingChart>
        <SourceState :source="document.sources.buffett" :rows="rows('buffett')" hide-source />
      </template>
    </template>
  </section>
</template>
<script setup lang="ts">
  import {
    computed,
    defineComponent,
    h,
    onBeforeUnmount,
    ref,
    shallowRef,
    watch,
    type PropType,
  } from 'vue';
  import {
    getMarketContext,
    type MarketContextSection,
    type MarketMonitor,
    type MonitorRow,
    type MonitorSource,
    type MonitorValue,
  } from '@/api/cnMarketMonitor';
  import type { EquityObservatory } from '@/api/equityObservatory';
  import FinancingChart, { type FinanceLine, type FinanceRow } from './FinancingChart.vue';
  import {
    DEFAULT_RESEARCH_HISTORY_YEARS,
    RESEARCH_HISTORY_YEARS,
    valuationWindow,
  } from '../../components/indexValuationStats';

  const props = defineProps<{
    section: MarketContextSection;
    refreshKey?: number;
    breadthPart?: 'history' | 'belowBook';
    breadthSnapshot?: EquityObservatory['breadth'];
    breadthRanks?: Record<
      'ma' | 'highlow',
      { rows: FinanceRow[]; lines: FinanceLine[]; title: string }
    >;
    snapshotStale?: boolean;
    belowBookRanges?: number[];
  }>();
  const titles = { risk: '股债性价比', breadth: '市场宽度', macroValue: '巴菲特指标' };
  const document = shallowRef<MarketMonitor>(),
    loading = ref(false),
    error = ref('');
  const riskIndex = ref('000300'),
    market = ref('all'),
    highLowPeriod = ref(20);
  const historyRanges = RESEARCH_HISTORY_YEARS;
  const riskYears = ref<number>(DEFAULT_RESEARCH_HISTORY_YEARS);
  const buffettYears = ref<number>(DEFAULT_RESEARCH_HISTORY_YEARS);
  const belowBookYears = ref<number>(DEFAULT_RESEARCH_HISTORY_YEARS);
  const riskNames: Record<string, string> = {
    '000300': '沪深300',
    '000016': '上证50',
    '000905': '中证500',
  };
  const markets: Record<string, string> = {
    all: '全部A股',
    hs300: '沪深300',
    sz50: '上证50',
    zz500: '中证500',
  };
  const rows = (key: string) => (document.value?.sources[key]?.data || []) as MonitorRow[];
  const windowRows = (key: string, years: number) => {
    const history = rows(key);
    const end = history.at(-1)?.date;
    return end ? valuationWindow(history, years, end) : [];
  };
  const buffettRows = computed(() => windowRows('buffett', buffettYears.value));
  const latest = (key: string, field: string) => {
    const history = rows(key);
    for (let i = history.length - 1; i >= 0; i--) {
      if (history[i][field] != null) return history[i];
    }
    return undefined;
  };
  const belowBookMetrics = computed(() =>
    Object.entries(markets).map(([key, name]) => ({
      key,
      name,
      row: latest('below_' + key, 'value'),
    })),
  );
  const belowBookDate = computed(() => {
    const dates = new Set(belowBookMetrics.value.flatMap(({ row }) => (row ? [row.date] : [])));
    return dates.size === 1 ? [...dates][0] : undefined;
  });
  const selectedBelowBook = computed(() => latest('below_' + market.value, 'value'));
  const historyLines = (view: 'ma' | 'highlow'): FinanceLine[] =>
    view === 'ma'
      ? [
          { key: 'ma5', name: '高于5日均线', color: '#2864ec', unit: '%', defaultSelected: false },
          {
            key: 'ma20',
            name: '高于20日均线',
            color: '#00976f',
            unit: '%',
            defaultSelected: false,
          },
          { key: 'ma60', name: '高于60日均线', color: '#d09a14', unit: '%' },
        ]
      : [
          {
            key: 'high' + highLowPeriod.value,
            name: '创新高',
            color: '#d84f5a',
            unit: '只',
            bar: true,
            barColor: 'series',
          },
          {
            key: 'low' + highLowPeriod.value,
            name: '创新低',
            color: '#00976f',
            unit: '只',
            bar: true,
            barColor: 'series',
          },
        ];
  const breadthCharts = computed(() =>
    (['ma', 'highlow'] as const).map((key) => {
      const lines = historyLines(key);
      return {
        key,
        title: key === 'ma' ? '全A · 站上均线' : '全A · 创新高／新低',
        lines,
        latest: rows(key).findLast((row) => lines.some((line) => row[line.key] != null)),
      };
    }),
  );
  function historyValue(value: MonitorValue | undefined, unit: string) {
    const formatted = fmt(value, 0);
    return formatted === '—' ? formatted : formatted + unit;
  }
  const belowBookRows = computed(() => {
    const key = 'below_' + market.value;
    const end = latest(key, 'value')?.date;
    return end ? valuationWindow(rows(key), belowBookYears.value, end) : [];
  });
  const riskRows = computed(() => windowRows(riskIndex.value, riskYears.value));
  const latestRisk = computed(() => latest(riskIndex.value, 'erpTtm'));
  const riskCharts = computed<
    { key: string; title: string; lines: FinanceLine[]; axisNames?: [string, string] }[]
  >(() => [
    {
      key: 'spread',
      title: `${riskNames[riskIndex.value]} · 股债性价比`,
      lines: [
        { key: 'erpTtm', name: '股债差', color: '#2864ec', unit: '百分点' },
        {
          key: 'close',
          name: riskNames[riskIndex.value],
          color: '#171717',
          unit: '点',
          right: true,
        },
      ],
    },
    {
      key: 'yields',
      title: '盈利收益率与国债收益率',
      lines: [
        { key: 'earningsTtm', name: '盈利收益率', color: '#2864ec', unit: '%' },
        { key: 'bond', name: '10年国债收益率', color: '#b57a08', unit: '%', right: true },
      ],
      axisNames: ['盈利收益率（%）', '10年国债收益率（%）'],
    },
  ]);
  const fmt = (v: MonitorValue | undefined, digits = 2) =>
    v == null || v === '' || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', {
          minimumFractionDigits: digits,
          maximumFractionDigits: digits,
        });
  const lagged = (key: string, field: string) =>
    !!latest(key, field)?.date && latest(key, field)!.date < (rows(key).at(-1)?.date || '');
  const SourceState = defineComponent({
    props: {
      source: Object as PropType<MonitorSource>,
      rows: { type: Array as PropType<MonitorRow[]>, required: true },
      hideSource: Boolean,
    },
    setup(p) {
      return () => {
        const conflicts = p.rows.filter((r) => r.conflictFields).map((r) => r.date);
        const content = [
          p.source?.status === 'error'
            ? h('p', { class: 'notice' }, '本轮来源更新失败，保留已有有效历史。')
            : null,
          !p.rows.length ? h('p', { class: 'notice' }, '暂无有效历史，其他图表可继续查看。') : null,
          conflicts.length
            ? h(
                'p',
                { class: 'notice' },
                `历史同日记录存在冲突，相关字段留空：${conflicts.slice(0, 5).join('、')}${
                  conflicts.length > 5 ? ' 等' : ''
                }。`,
              )
            : null,
          !p.hideSource && p.source?.sourceUrl && /^https?:\/\//.test(p.source.sourceUrl)
            ? h(
                'a',
                { href: p.source.sourceUrl, target: '_blank', rel: 'noopener noreferrer' },
                '来源 ↗',
              )
            : null,
        ].filter((item) => item !== null);
        return content.length ? h('div', { class: 'source-state' }, content) : null;
      };
    },
  });
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    document.value = undefined;
    try {
      const d = await getMarketContext(props.section, current.signal);
      if (!current.signal.aborted) document.value = d;
    } catch {
      if (!current.signal.aborted) error.value = `${titles[props.section]}读取失败`;
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  watch(() => [props.section, props.refreshKey], load, { immediate: true });
  onBeforeUnmount(() => controller?.abort());
</script>
<style scoped>
  .history-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .breadth-history-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .breadth-history-card {
    min-width: 0;
  }

  @media (min-width: 1181px) {
    .breadth-history-card,
    .breadth-history-card > :deep(.chart-expand),
    .breadth-history-card :deep(.chart-expand__surface:not(:modal)),
    .breadth-history-card :deep(.chart-expand__surface:not(:modal) > .financing-chart) {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .breadth-history-card > :deep(.chart-expand),
    .breadth-history-card :deep(.chart-expand__surface:not(:modal)),
    .breadth-history-card :deep(.chart-expand__surface:not(:modal) > .financing-chart),
    .breadth-history-card :deep(.chart-expand__surface:not(:modal) .plot) {
      flex: 1 0 auto;
    }

    .breadth-history-card :deep(.chart-expand__surface:not(:modal) .data-scroll) {
      max-height: 340px;
      overflow: auto;
    }
  }

  @media (max-width: 1180px) {
    .breadth-history-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  .history-controls select {
    padding: 4px 6px;
    font-size: 12px;
  }

  .context {
    min-width: 0;
    color: #17324d;
  }

  h3 {
    margin: 24px 0 12px;
    font-size: 16px;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 16px 0;
    gap: 18px;
  }

  button,
  select {
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

  button.active {
    border-color: #a7c0ff;
    background: #edf3ff;
    color: #2864ec;
  }

  .below-book-summary,
  .below-book-options,
  .below-book-options button {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .below-book-summary {
    margin-bottom: 8px;
  }

  .below-book-summary h3 {
    margin: 0 4px 0 0;
    font-size: 16px;
  }

  .below-book-options button {
    padding: 4px 9px;
  }

  .below-book-summary time,
  .below-book-sample,
  .definition {
    color: #71869d;
    font-size: 12px;
  }

  .notice,
  .context :deep(.notice) {
    color: #967025;
    font-size: 12px;
  }

  .context :deep(a) {
    color: #2864ec;
  }

  .risk-index {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
  }

  .risk-index select {
    padding: 4px 8px;
  }

  .context :deep(.source-state) {
    margin: 10px 0 22px;
  }

  .context--compact :deep(.financing-chart),
  .context--compact :deep(.source-state),
  .context-notice {
    margin: 4px 0;
  }
</style>
