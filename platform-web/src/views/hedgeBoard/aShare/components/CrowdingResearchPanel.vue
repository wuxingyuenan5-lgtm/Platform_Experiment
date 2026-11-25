<template>
  <template v-if="marketOnly">
    <slot name="market" :breadth-ranks="breadthRanks"></slot>
    <p v-if="loading" role="status">正在读取研究历史…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="loadHistory">重试</button></p>
    <FinancingChart
      v-for="item in marketSeries"
      :key="item.key"
      :title="item.name"
      :rows="item.rows"
      :lines="item.lines"
      :alternate="{ rows: item.rows, lines: rankLines }"
      :primary-label="item.key === 'analyst' ? '季节调整值与价格' : '原始值与价格'"
      allow-table
    />
  </template>
  <section
    v-else
    class="research-supplement crowding-research"
    :class="{ 'industry-split': $slots['industry-history'] }"
    aria-label="拥挤度研究补充"
  >
    <header v-if="!$slots['industry-history']" class="research-heading">
      <div>
        <h2>{{ view === 'industry' ? '行业拥挤度研究' : '交易拥挤度' }}</h2>
        <p v-if="view !== 'industry'">分项时序、行业比较与七项模型。</p>
      </div>
      <div class="research-actions">
        <nav v-if="expanded && !view" class="research-tabs" aria-label="拥挤度研究视角">
          <button
            v-for="item in tabs"
            :key="item.key"
            :aria-pressed="tab === item.key"
            @click="tab = item.key"
            >{{ item.label }}</button
          >
        </nav>
        <button v-if="!alwaysExpanded" type="button" :aria-expanded="open" @click="open = !open">
          {{ open ? '收起' : '展开研究' }}
        </button>
      </div>
    </header>
    <template v-if="expanded">
      <template v-if="tab === 'history'">
        <div class="history-toolbar">
          <label
            >研究分项
            <select v-model="indicator"
              ><option v-for="item in indicators" :key="item.key" :value="item.key">{{
                item.name
              }}</option></select
            ></label
          >
          <span>周度观察 · 原始值 → 一年分位 → 均值与标准差</span>
        </div>
        <p v-if="loading" role="status">正在读取研究历史…</p>
        <p v-if="error" role="alert">{{ error }} <button @click="loadHistory">重试</button></p>
        <p v-if="indicatorNote" class="research-note">{{ indicatorNote }}</p>
        <p v-if="source?.sampleBasis === 'current-universe'" class="research-source">
          样本目录 {{ source.universeDate }} · {{ source.fetchedCount }}/{{
            source.universeCount
          }}只取得行情； 最近完整周符合窗口 {{ fmt(breadthCoverage?.eligible, 0) }}只，满足条件
          {{ fmt(breadthCoverage?.numerator, 0) }}只。
        </p>
        <div class="history-summary">
          <div
            ><span>{{ indicatorTitle }}</span
            ><strong
              >{{ fmt(lastComplete?.value) }}<small>{{ unit }}</small></strong
            ><span>{{ lastComplete?.date || '—' }} · 最近完整观察周</span></div
          >
          <div
            ><span>一年历史分位</span><strong>{{ fmt(lastComplete?.rank) }}<small>%</small></strong
            ><span>最近52个有效观察周</span></div
          >
          <div
            ><span>相对滚动区间位置</span
            ><strong>{{ fmt(lastComplete?.relative) }}<small>%</small></strong
            ><span>0%为均值−1σ，100%为均值+1σ</span></div
          >
        </div>
        <p class="research-source"
          >{{ historySource }} · 数据截至 {{ historyDate || '—' }} · {{ sourceStatus
          }}<span v-if="researchRows.at(-1)?.partial"> · 本周尚未纳入分位与区间计算</span></p
        >
        <div class="history-charts">
          <FinancingChart
            :key="indicator + '-raw'"
            :title="rawTitle(indicatorTitle, indicator)"
            :rows="researchRows"
            :lines="rawLines"
            :range-days="calendarRanges ? undefined : range"
            :range-years="calendarRanges ? range : undefined"
            @range="range = $event"
            @range-years="range = $event"
            allow-table
          />
          <FinancingChart
            :key="indicator + '-rank'"
            :title="indicatorTitle + ' · 一年分位与波动区间'"
            :rows="researchRows"
            :lines="rankLines"
            :range-days="calendarRanges ? undefined : range"
            :range-years="calendarRanges ? range : undefined"
            @range="range = $event"
            @range-years="range = $event"
            allow-table
          />
        </div>
        <component :is="alwaysExpanded ? 'section' : 'details'" class="research-reference"
          ><component
            :is="alwaysExpanded ? 'h3' : 'summary'"
            :class="{ 'disclosure-title': alwaysExpanded }"
            >计算口径与研报对应关系</component
          >
          <p
            >{{
              calculationNote
            }}
            一年采用52个周度观察值；交易数据依据平台独立交易日历排除整周休市，交易日缺值留空；分位是窗口内不高于当前值的比例。分位曲线的均值与总体标准差使用最近52个完整分位值，包含当周；缺周、缺值与零方差不推算。最新未结束周只显示原始值。价格对照为沪深300，区别于研报的万得全A。</p
          >
          <p
            >相对位置 =（分位 −（分位滚动均值 − 标准差））÷（2 ×
            标准差）×100%，可以低于0%或超过100%。这里是所选分项的相对位置，七项综合模型需所有输入完整后才可计算。</p
          >
        </component>
      </template>
      <template v-else-if="tab === 'industry'">
        <div class="industry-comparison">
          <div class="industry-toolbar">
            <label
              >比较方式<select
                v-model="industryMode"
                @change="changeWindow = industryMode === 'relative' ? 4 : 20"
              >
                <option value="relative">52周分位</option
                ><option value="percentile">30交易日分位</option>
              </select></label
            >
            <label
              >拥挤度指标
              <select v-model="metric"
                ><option value="amount">成交额占比分位</option
                ><option value="turnover">等权换手率分位</option></select
              ></label
            >
            <label
              >变化窗口
              <select v-model.number="changeWindow"
                ><option :value="industryMode === 'relative' ? 1 : 5">{{
                  industryMode === 'relative' ? '1个观察周' : '5个观察日'
                }}</option
                ><option :value="industryMode === 'relative' ? 4 : 20">{{
                  industryMode === 'relative' ? '4个观察周（约一月）' : '20个观察日'
                }}</option></select
              ></label
            >
            <span>{{ changes.baseDate || '—' }} → {{ changes.date || '—' }}</span>
          </div>
          <div class="quadrant-filters" role="group" aria-label="拥挤度象限筛选">
            <button
              v-for="item in quadrants"
              :key="item.key"
              type="button"
              :aria-pressed="quadrant === item.key"
              @click="quadrant = item.key"
              >{{ item.label }}</button
            >
          </div>
          <p v-if="monitorLoading" role="status">正在读取行业历史…</p>
          <p v-if="monitorError" role="alert"
            >{{ monitorError }} <button @click="loadMonitor">重试</button></p
          >
          <div class="industry-workbench">
            <ResearchScatter
              title="行业拥挤度 · 分位与变化"
              :subtitle="
                metricTitle + (industryMode === 'relative' ? ' · 52周' : ' · 乐咕乐股30交易日')
              "
              :points="points"
              x-label="当前分位（%）"
              :y-label="
                changeWindow + (industryMode === 'relative' ? '周' : '日') + '分位变化（百分点）'
              "
              :x-bounds="[0, 100]"
              :x-middle="50"
              :selected="selected"
              show-names
              compact-labels
              @select="selected = $event"
            >
              {{ selectedIndustry?.name || '选择一个行业' }}：当前分位
              {{ fmt(selectedIndustry?.value) }}%，变化
              {{ signed(selectedIndustry?.change) }} 个百分点。
            </ResearchScatter>
            <aside class="industry-list" aria-label="行业拥挤度对照表">
              <div class="list-controls"
                ><input v-model="query" aria-label="筛选行业" placeholder="筛选行业"
              /></div>
              <div class="list-scroll" tabindex="0"
                ><table
                  ><thead
                    ><tr
                      ><th scope="col">行业</th
                      ><th
                        v-for="column in comparisonColumns"
                        :key="column.key"
                        scope="col"
                        :aria-sort="
                          sort === column.key ? (ascending ? 'ascending' : 'descending') : undefined
                        "
                        ><button type="button" @click="sortComparison(column.key)">{{
                          column.label
                        }}</button></th
                      ></tr
                    ></thead
                  ><tbody>
                    <tr
                      v-for="row in industries"
                      :key="row.code"
                      :class="{ selected: selected === row.code }"
                      ><th
                        ><button
                          :aria-pressed="selected === row.code"
                          @click="selected = row.code"
                          >{{ row.name }}</button
                        ></th
                      ><td>{{ row.raw == null ? '—' : fmt(row.raw) + '%' }}</td
                      ><td>{{ row.value == null ? '—' : fmt(row.value) + '%' }}</td
                      ><td :class="{ rise: (row.change || 0) > 0, fall: (row.change || 0) < 0 }">{{
                        signed(row.change)
                      }}</td></tr
                    >
                    <tr v-if="!industries.length"><td colspan="4">没有匹配行业</td></tr>
                  </tbody></table
                ></div
              >
            </aside>
          </div>
          <component
            :is="alwaysExpanded && view !== 'industry' ? 'section' : 'details'"
            class="research-reference"
            ><component
              :is="alwaysExpanded && view !== 'industry' ? 'h3' : 'summary'"
              :class="{ 'disclosure-title': alwaysExpanded && view !== 'industry' }"
              >数据口径与综合模型的区别</component
            ><p
              >52周分位为窗口内不高于当前值的观测占比。源站周频值是周末观察，不代表整周成交合计；缺值或未完周不计算分位。30交易日分位采用源站日频分位。纵轴为两个观察端点的分位之差；两种模式均为成交或换手分项，不是综合拥挤度评分。</p
            ></component
          >
        </div>
        <slot name="industry-history" :chart="industryChart">
          <FinancingChart v-bind="industryChart" />
        </slot>
      </template>
      <template v-else>
        <div class="model-heading"
          ><h3>七项等权模型</h3
          ><p>综合拥挤度 = 七项一年分位之和 ÷ 7。缺少任一输入时，不生成综合读数。</p></div
        >
        <p v-if="loading" role="status">正在读取七项历史…</p>
        <p v-if="error" role="alert">{{ error }} <button @click="loadHistory">重试</button></p>
        <p v-if="!loading && !error && missingModelInputs.length" class="research-note">
          {{ latestCompleteModelRow?.date || '最新完整周' }}缺少有效分位：{{
            missingModelInputs.join('、')
          }}
        </p>
        <div class="research-table" tabindex="0" aria-label="七项历史覆盖"
          ><table
            ><thead
              ><tr
                ><th>分项</th><th>最新完整周</th><th>原始值</th><th>一年分位</th
                ><th>有效分位周数</th></tr
              ></thead
            ><tbody>
              <tr v-for="item in modelCoverage" :key="item.key"
                ><th>{{ item.name }}</th
                ><td>{{ item.last?.date || '—' }}</td
                ><td
                  >{{ fmt(item.last?.value) }}
                  <template v-if="item.last?.value != null">{{
                    ['amount', 'fundflow'].includes(item.key)
                      ? '亿元'
                      : item.key === 'analyst'
                      ? '篇（季调）'
                      : '%'
                  }}</template></td
                ><td>{{ item.last?.rank != null ? fmt(item.last.rank) + '%' : '—' }}</td
                ><td>{{ item.valid }}</td></tr
              >
            </tbody></table
          ></div
        >
        <FinancingChart
          title="七项一年分位对照"
          :rows="modelRows"
          :lines="modelLines"
          :bounds="[0, 100]"
          :initial-range="1095"
          allow-table
          note="分项按周一至周日对齐，以周日标记；缺值留空。"
        />
        <div>
          <div class="research-table model-table" tabindex="0" aria-label="七项模型输入"
            ><table
              ><thead
                ><tr><th>维度</th><th>原指标</th><th>处理方法</th><th>当前数据</th></tr></thead
              ><tbody
                ><tr v-for="row in framework" :key="row[1]"
                  ><th>{{ row[0] }}</th
                  ><td>{{ row[1] }}</td
                  ><td>{{ row[2] }}</td
                  ><td>{{ row[3] }}</td></tr
                ></tbody
              ></table
            ></div
          >
          <component :is="alwaysExpanded ? 'section' : 'details'" class="research-reference" open
            ><component
              :is="alwaysExpanded ? 'h3' : 'summary'"
              :class="{ 'disclosure-title': alwaysExpanded }"
              >行业比较的原始定义</component
            ><p
              >以综合指标滚动一年均值±1倍标准差为上下界，相对位置
              =（综合指标−下界）÷（上界−下界）。横轴是当前相对位置，纵轴是近一个月的相对位置变化；0%和100%对应滚动下界与上界。不能用普通行业成交分位替换横轴，也不能用20日均线上比例替换30日指标。</p
            ></component
          >
        </div>
      </template>
      <p v-if="!$slots['industry-history']" class="reference-line"
        >研究依据：兴证策略《拥挤度研究框架》· 图页1–13</p
      >
    </template>
  </section>
</template>
<script setup lang="ts">
  import { inject, computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import Decimal from 'decimal.js';
  import { getMarketMonitor, type MarketMonitor, type MonitorItem } from '@/api/cnMarketMonitor';
  import type { EquityObservatory } from '@/api/equityObservatory';
  import {
    researchRequest,
    type MacroDashboardSeries,
    type AShareMarketHistoryRow,
  } from '@/api/hedgeResearch';
  import FinancingChart, { type FinanceLine } from './FinancingChart.vue';
  import {
    DEFAULT_RESEARCH_HISTORY_YEARS,
    RESEARCH_HISTORY_RANGE_KEY,
  } from '../../components/indexValuationStats';
  import ResearchScatter from './ResearchScatter.vue';
  import {
    alignedResearchRanks,
    financingSentiment,
    crowdingChanges,
    formatResearch as fmt,
    numeric,
    weeklyResearch,
    researchBands,
  } from './researchFrameworkAnalysis';

  const alwaysExpanded = inject('themeResearchAlwaysExpanded', false);
  const calendarRanges = inject(RESEARCH_HISTORY_RANGE_KEY, false);
  const props = defineProps<{
    data: EquityObservatory;
    refreshKey?: number;
    industryCode?: string;
    marketOnly?: boolean;
    view?: 'history' | 'industry' | 'model';
  }>();
  const emit = defineEmits<{ industry: [code: string] }>();
  const open = ref(true),
    localTab = ref('history'),
    indicator = ref('ma30'),
    range = ref(calendarRanges ? DEFAULT_RESEARCH_HISTORY_YEARS : 1095);
  const expanded = computed(() => alwaysExpanded || open.value);
  const tab = computed({
    get: () => props.view || localTab.value,
    set: (value) => {
      localTab.value = value;
    },
  });
  const indicators = [
    { key: 'amount', name: '全A当周成交额' },
    { key: 'turnover', name: '全市场换手率' },
    { key: 'ma30', name: '30日均线上数量占比' },
    { key: 'high60', name: '60日新高数量占比' },
    { key: 'financing', name: '融资买入情绪' },
    { key: 'fundflow', name: '主力净流入（东财口径）' },
    { key: 'analyst', name: '分析师评级情绪' },
  ];
  type PublicSource = {
    status: string;
    sourceUrl: string;
    observationDate?: string;
    sourceName?: string;
    frequency?: string;
    sampleBasis?: string;
    universeDate?: string;
    universeCount?: number;
    fetchedCount?: number;
    data: Array<{
      date: string;
      value: string | null;
      close?: string | null;
      count?: number;
      partial?: boolean;
      baseline?: string | null;
      eligible?: number;
      numerator?: number;
    }>;
  };
  type PublicResearch = {
    sources: Record<string, PublicSource>;
    calendar?: string[];
    amountHistory?: Pick<AShareMarketHistoryRow, 'observedAt' | 'totalAmountYuan' | 'source'>[];
    benchmarkHistory?: { date: string; close: string }[];
    industryHistory?: MonitorItem[];
    industryHistoryStatus?: string;
  };
  const publicData = shallowRef<PublicResearch>({
    sources: {},
  });
  const publicKeys = ['turnover', 'fundflow', 'analyst', 'ma30', 'high60'];

  const tabs = [
    { key: 'history', label: '分项时序' },
    { key: 'industry', label: '行业拥挤度' },
    { key: 'model', label: '七项模型' },
  ];
  const industryMode = ref('relative');
  const metric = ref<'amount' | 'turnover'>('amount'),
    changeWindow = ref(4),
    localSelected = ref('801080.SI'),
    query = ref(''),
    sort = ref<'raw' | 'value' | 'change'>('value');
  const ascending = ref(false);
  const quadrants = [
    { key: 'all', label: '全部' },
    { key: 'high-up', label: '高位升温' },
    { key: 'high-down', label: '高位降温' },
    { key: 'low-up', label: '低位升温' },
    { key: 'low-down', label: '低位降温' },
  ];
  const quadrant = ref('all');
  const comparisonColumns = computed(
    () =>
      [
        { key: 'raw', label: metric.value === 'amount' ? '成交占比' : '等权换手率' },
        { key: 'value', label: '分位' },
        { key: 'change', label: '变化（pp）' },
      ] as const,
  );
  function sortComparison(key: typeof sort.value) {
    ascending.value = sort.value === key ? !ascending.value : false;
    sort.value = key;
  }
  const selected = computed({
    get: () =>
      props.industryCode ? `${props.industryCode.replace(/\.SI$/i, '')}.SI` : localSelected.value,
    set: (value: string) => {
      localSelected.value = value;
      emit('industry', value.replace(/\.SI$/i, ''));
    },
  });
  const monitor = shallowRef<MarketMonitor>(),
    monitorLoading = ref(false),
    monitorError = ref('');
  let monitorAbort: AbortController | undefined, monitorKey: number | undefined;
  async function loadMonitor() {
    monitorAbort?.abort();
    const current = (monitorAbort = new AbortController());
    monitorLoading.value = true;
    monitorError.value = '';
    try {
      const [result, history] = await Promise.all([
        getMarketMonitor(current.signal, ['industry']),
        researchRequest<PublicResearch>({
          method: 'GET',
          url: '/research/a-share/crowding-research',
          signal: current.signal,
        }),
      ]);
      if (!current.signal.aborted) {
        monitor.value = result;
        publicData.value = history;
        monitorKey = props.refreshKey ?? 0;
      }
    } catch {
      if (!current.signal.aborted) monitorError.value = '行业数据读取失败，可重试。';
    } finally {
      if (!current.signal.aborted) monitorLoading.value = false;
    }
  }
  const items = computed(() => (monitor.value?.sources.industry?.data || []) as MonitorItem[]);
  const weeklyRankItems = computed(() =>
    (publicData.value.industryHistory || []).map((item) => {
      const histories = (['amount', 'turnover'] as const).map((key) =>
        researchBands(
          weeklyResearch(
            (item.history || []).map((r) => ({
              date: r.date,
              value: r[key] ?? null,
              close: r.close ?? null,
            })),
            'last',
            new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date()),
            publicData.value.calendar || [],
          ),
        ).filter((r) => !r.partial),
      );
      return {
        ...item,
        history: histories[0].map((r, i) => ({
          date: r.date,
          amount: r.rank,
          turnover: histories[1][i]?.rank ?? null,
          close: r.close,
        })),
      };
    }),
  );
  const comparisonItems = computed(() =>
    industryMode.value === 'relative' ? weeklyRankItems.value : items.value,
  );
  const changes = computed(() =>
    crowdingChanges(comparisonItems.value, metric.value, changeWindow.value),
  );
  const comparisonRaw = computed(
    () =>
      new Map(
        (publicData.value.industryHistory || []).map((item) => [
          item.code,
          numeric(item.history?.find((point) => point.date === changes.value.date)?.[metric.value]),
        ]),
      ),
  );
  const industries = computed(() =>
    changes.value.rows
      .filter((row) => row.name.includes(query.value.trim()))
      .filter(
        (row) =>
          quadrant.value === 'all' ||
          (row.value != null &&
            row.change != null &&
            row.change !== 0 &&
            quadrant.value ===
              `${row.value >= 50 ? 'high' : 'low'}-${row.change > 0 ? 'up' : 'down'}`),
      )
      .map((row) => ({ ...row, raw: comparisonRaw.value.get(row.code) ?? null }))
      .sort((left, right) => {
        const first = left[sort.value],
          second = right[sort.value];
        if (first == null) return second == null ? 0 : 1;
        if (second == null) return -1;
        return ascending.value ? first - second : second - first;
      }),
  );
  const points = computed(() => {
    const visible = industries.value.filter((row) => row.value != null && row.change != null);
    const extremes = [...visible].sort((left, right) => left.change! - right.change!);
    return visible.map((row) => ({
      id: row.code,
      name: row.name,
      x: row.value!,
      y: row.change!,
      highlightLabel: row === extremes[0] || row === extremes.at(-1),
    }));
  });
  const selectedIndustry = computed(() =>
    changes.value.rows.find((r) => r.code === selected.value),
  );
  const industryHistory = computed(
    () => comparisonItems.value.find((r) => r.code === selected.value)?.history || [],
  );
  const metricTitle = computed(() =>
    metric.value === 'amount' ? '成交额占比分位' : '等权换手率分位',
  );
  const industryLines = computed<FinanceLine[]>(() => [
    {
      key: 'amount',
      name: '成交额占比分位',
      color: '#2563eb',
      unit: '%',
    },
    {
      key: 'turnover',
      name: '等权换手率分位',
      color: '#089184',
      unit: '%',
    },
    ...(industryMode.value === 'relative'
      ? [{ key: 'close', name: '行业指数', color: '#111827', unit: '点', right: true }]
      : []),
  ]);
  const industryChart = computed(() => ({
    title:
      (selectedIndustry.value?.name || '所选行业') +
      (industryMode.value === 'relative' ? ' · 52周拥挤度分位历史' : ' · 30交易日拥挤度分位历史'),
    rows: industryHistory.value,
    lines: industryLines.value,
    bounds: [0, 100] as [number, number],
    initialRange: 0,
    allowTable: true,
  }));
  const signed = (v: unknown) => (numeric(v) === null ? '—' : (Number(v) > 0 ? '+' : '') + fmt(v));
  const margin = shallowRef<MacroDashboardSeries[]>([]),
    loading = ref(false),
    error = ref('');
  const amount = computed(() => publicData.value.amountHistory || []);
  let abort: AbortController | undefined;
  const loaded = new Map<string, number>();
  async function loadHistory() {
    abort?.abort();
    const current = (abort = new AbortController()),
      key = props.marketOnly || tab.value === 'model' ? 'model' : indicator.value;
    loading.value = true;
    error.value = '';
    try {
      {
        const d = await researchRequest<PublicResearch>({
          method: 'GET',
          url: '/research/a-share/crowding-research',
          params: { include_market_history: true },
          signal: current.signal,
        });
        if (!current.signal.aborted) publicData.value = d;
      }
      if (key === 'financing' || key === 'model') {
        const d = await researchRequest<{ margin: MacroDashboardSeries[] }>({
          method: 'GET',
          url: '/research/a-share/financing',
          signal: current.signal,
        });
        if (!current.signal.aborted) margin.value = d.margin;
      }
      if (!current.signal.aborted) {
        for (const ready of key === 'model'
          ? ['model', 'amount', 'financing', ...publicKeys]
          : [key, ...publicKeys])
          loaded.set(ready, props.refreshKey ?? 0);
      }
    } catch {
      if (!current.signal.aborted) error.value = '研究历史读取失败，可重试。';
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  watch(
    [expanded, tab, indicator, () => props.refreshKey],
    () => {
      if (props.marketOnly) {
        if (loaded.get('model') !== (props.refreshKey ?? 0)) void loadHistory();
        return;
      }
      if (!expanded.value) return;
      if (tab.value === 'history' && loaded.get(indicator.value) !== (props.refreshKey ?? 0))
        void loadHistory();
      if (tab.value === 'model' && loaded.get('model') !== (props.refreshKey ?? 0))
        void loadHistory();
      if (tab.value === 'industry' && monitorKey !== (props.refreshKey ?? 0)) void loadMonitor();
    },
    { immediate: true },
  );
  onBeforeUnmount(() => {
    abort?.abort();
    monitorAbort?.abort();
  });
  const buy = computed(() => margin.value.find((s) => s.seriesId === 'cn_margin_financing_buy'));
  const price = computed(
    () =>
      new Map([
        ...(publicData.value.sources.turnover?.data || []).map(
          (r) => [r.date, r.close ?? null] as const,
        ),
        ...(publicData.value.benchmarkHistory || []).map((r) => [r.date, r.close] as const),
        ...(
          props.data.indices?.find((s) => s.code === '000300' || s.name === '沪深300')?.history ||
          []
        ).map((r) => [r.date, r.value ?? r.close ?? null] as const),
      ]),
  );
  const weekPrice = (day: string) => {
    const start = new Date(day + 'T00:00:00Z');
    start.setUTCDate(start.getUTCDate() - 6);
    const first = start.toISOString().slice(0, 10);
    const dates = [...price.value.keys()].filter((d) => d <= day && d >= first).sort();
    return price.value.get(dates.at(-1)!) ?? null;
  };
  const source = computed(() => publicData.value.sources[indicator.value]);
  function rowsFor(key: string) {
    const currentSource = publicData.value.sources[key];
    const asOf = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Asia/Shanghai' }).format(new Date());
    if (key === 'analyst' || currentSource?.frequency === 'weekly')
      return researchBands(
        (currentSource?.data || []).map((r) => ({ ...r, close: weekPrice(r.date) })),
      );
    const daily = publicKeys.includes(key)
      ? (currentSource?.data || []).map((r) => ({
          ...r,
          close: r.close ?? price.value.get(r.date) ?? null,
        }))
      : key === 'financing'
      ? financingSentiment(margin.value).map((r) => ({
          date: r.date,
          value: r.sentiment,
          close: price.value.get(r.date) ?? null,
        }))
      : amount.value.map((r) => ({
          date: r.observedAt,
          value:
            numeric(r.totalAmountYuan) === null
              ? null
              : new Decimal(r.totalAmountYuan!).div(100000000).toString(),
          close: price.value.get(r.observedAt) ?? null,
        }));
    return researchBands(
      weeklyResearch(
        daily,
        ['amount', 'fundflow', 'turnover'].includes(key) ? 'sum' : 'last',
        asOf,
        publicData.value.calendar || [],
      ),
    );
  }
  const researchRows = computed(() => rowsFor(indicator.value));
  const lastComplete = computed(() => researchRows.value.filter((r) => !r.partial).at(-1));
  const breadthCoverage = computed(() => source.value?.data.filter((r) => !r.partial).at(-1));
  const unitFor = (key: string) =>
    ['amount', 'fundflow'].includes(key) ? '亿元' : key === 'analyst' ? '篇' : '%';
  const unit = computed(() => unitFor(indicator.value));
  const indicatorTitle = computed(
    () => indicators.find((i) => i.key === indicator.value)?.name || '',
  );
  const historySource = computed(() =>
    publicKeys.includes(indicator.value)
      ? source.value?.sourceName ||
        (['turnover', 'ma30', 'high60'].includes(indicator.value)
          ? '乐咕乐股公开历史'
          : '东方财富公开数据')
      : indicator.value === 'amount'
      ? [...new Set(amount.value.map((r) => r.source).filter(Boolean))].join(' / ')
      : buy.value?.source || '沪深两融',
  );
  const historyDate = computed(() =>
    publicKeys.includes(indicator.value)
      ? source.value?.observationDate
      : indicator.value === 'amount'
      ? amount.value
          .map((r) => r.observedAt)
          .sort()
          .at(-1)
      : buy.value?.observationDate,
  );
  const sourceStatus = computed(() =>
    publicKeys.includes(indicator.value)
      ? source.value?.status === 'ready'
        ? '已读取'
        : source.value?.status === 'error'
        ? '更新失败，保留已有数据'
        : '数据未齐'
      : '归档数据',
  );
  const indicatorNote = computed(
    () =>
      ((
        {
          ma30: '公开前复权收盘价严格高于30个交易日均值的股票占比。采用采集日沪深A股目录回看，包含ST，不含北交所和历史已退市股票；不是历史时点全市场样本。分母仅含窗口内每天有有效行情的股票，停牌缺口与上市不足30日不补值。',
          high60:
            '当周任一天收盘价严格超过此前59个交易日最高收盘价，按股票去重。分母要求本周每天均有完整60日窗口。使用采集日沪深A股目录回看，存在生存者偏差；收盘新高口径不含盘中触及新高，不冒充Wind全市场原值。',
          fundflow:
            '目前公开接口约覆盖半年，未满足一年分位所需的52个完整周。东财大单与超大单口径也未证实等同研报“单笔成交额大于20万元”，因此仅作独立对照，不计入七项模型。',
          analyst:
            '每周买入与增持评级记录数，减去过去三年同ISO周的平均数。使用东方财富评级分类，与研报Wind统计样本有差异；第53周缺少同比周时留空。',
          turnover: '日换手率求和为当周换手率。公开来源覆盖最近三年；与Wind全A统计样本可能有差异。',
        } as Record<string, string>
      )[indicator.value] || ''),
  );
  const calculationNote = computed(
    () =>
      ((
        {
          financing:
            '融资买入情绪 = 近20个交易观察日融资买入额合计 ÷ 近60个合计，再取每周最后一个观察值。',
          amount: '含北交所的全A日成交额相加为当周成交额。',
          turnover: '同一周日换手率求和为周换手率；缺少整周时留空。',
          fundflow: '同一周主力净流入金额求和，单位亿元。',
          analyst:
            '先按自然周汇总评级记录数，再减去过去三年同ISO周均值；以调整后的周数值计算一年分位。',
          ma30: '每周最后一个交易日采样；分子、分母来自同一股票池及同一30日有效窗口。',
          high60: '每周内创60日收盘新高的股票去重计数，再除以本周拥有完整窗口的股票数。',
        } as Record<string, string>
      )[indicator.value] || '该分项尚缺计算输入。'),
  );
  const rawTitle = (name: string, key: string) =>
    name + (key === 'analyst' ? ' · 季节调整值与价格' : ' · 原始值与价格');
  const rawLinesFor = (name: string, unit: string): FinanceLine[] => [
    { key: 'value', name, color: '#2563eb', unit, width: 2 },
    ...(['mean', 'upper', 'lower'] as const).map((key, i) => ({
      key,
      name: ['52周均值', '均值+1σ', '均值−1σ'][i],
      unit,
      color: ['#94a3b8', '#ba8b3b', '#7c9b93'][i],
      lineType: 'dashed' as const,
      width: 1,
    })),
    { key: 'close', name: '沪深300', color: '#b95656', unit: '点', right: true },
  ];
  const rawLines = computed(() => rawLinesFor(indicatorTitle.value, unit.value));
  const rankLines: FinanceLine[] = [
    { key: 'rank', name: '一年历史分位', color: '#2563eb', unit: '%', width: 2 },
    {
      key: 'rankMean',
      name: '分位52周均值',
      color: '#94a3b8',
      unit: '%',
      lineType: 'dashed',
      width: 1,
    },
    {
      key: 'rankUpper',
      name: '均值+1σ',
      color: '#ba8b3b',
      unit: '%',
      lineType: 'dashed',
      width: 1,
    },
    {
      key: 'rankLower',
      name: '均值−1σ',
      color: '#7c9b93',
      unit: '%',
      lineType: 'dashed',
      width: 1,
    },
    { key: 'close', name: '沪深300', color: '#b95656', unit: '点', right: true },
  ];
  const modelSeries = computed(() =>
    indicators.map((item) => ({ ...item, rows: rowsFor(item.key) })),
  );
  const breadthRanks = computed(() => ({
    ma: { rows: rowsFor('ma30'), lines: rankLines, title: '30日均线上数量占比' },
    highlow: { rows: rowsFor('high60'), lines: rankLines, title: '60日新高数量占比' },
  }));
  const marketSeries = computed(() =>
    indicators
      .filter((item) => !['fundflow', 'ma30', 'high60'].includes(item.key))
      .map((item) => ({
        ...item,
        rows: rowsFor(item.key),
        lines: rawLinesFor(item.name, unitFor(item.key)),
      })),
  );
  const modelRows = computed(() => alignedResearchRanks(modelSeries.value));
  const latestCompleteModelRow = computed(() =>
    alignedResearchRanks(
      modelSeries.value.map((item) => ({ ...item, rows: item.rows.filter((row) => !row.partial) })),
    ).at(-1),
  );
  const missingModelInputs = computed(() => {
    const latest = latestCompleteModelRow.value;
    return indicators.filter((item) => latest?.[item.key] == null).map((item) => item.name);
  });
  const modelLines: FinanceLine[] = indicators.map((item, i) => ({
    key: item.key,
    name: item.name,
    unit: '%',
    color: ['#2563eb', '#0d9488', '#b45309', '#9333ea', '#be123c', '#475569', '#0891b2'][i],
  }));
  const modelCoverage = computed(() =>
    modelSeries.value.map((item) => ({
      ...item,
      last: item.rows.filter((row) => !row.partial).at(-1),
      valid: item.rows.filter((row) => row.rank !== null).length,
    })),
  );
  const framework = [
    [
      '量能',
      '成交额 / 行业成交占比',
      '当周值 → 滚动一年分位',
      '已接全A成交额及31行业五年周频成交占比',
    ],
    ['量能', '换手率', '当周值 → 滚动一年分位', '已接全市场三年日换手及31行业五年周频等权换手'],
    [
      '价格',
      '30日均线上股票数量占比',
      '周度采样 → 滚动一年分位',
      '已接公开前复权日线重建；当前目录回看，不等同历史全市场',
    ],
    [
      '价格',
      '创60日新高股票数量占比',
      '周内股票去重 → 滚动一年分位',
      '已接周内收盘新高占比；当前目录回看，样本差异保留',
    ],
    [
      '资金',
      '融资买入情绪',
      '20日买入合计 / 60日买入合计 → 一年分位',
      '已接日历史，支持周度分位及滚动区间',
    ],
    [
      '资金',
      '主力资金净流入',
      '单笔成交额大于20万元 → 一年分位',
      '已接东财约半年历史；门槛差异和长度不足，不能纳入综合',
    ],
    [
      '分析师情绪',
      '增持 / 买入评级研报数量',
      '当期值减过去三年同期均值，滚动一年分位',
      '已接东方财富每周评级记录数与三年同期调整',
    ],
  ];
</script>
<style scoped src="./researchSupplement.css"></style>
<style scoped>
  .research-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .research-actions .research-tabs {
    margin: 0;
  }

  .history-toolbar,
  .industry-split {
    display: contents;
  }

  .industry-split .industry-comparison {
    margin-bottom: 14px;
    padding: 14px;
    border: 1px solid var(--strategy-border, #e2e8f0);
    border-radius: 12px;
    background: var(--strategy-surface, #fff);
  }

  .quadrant-filters {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 10px;
  }

  .industry-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 18px 0 14px;
    font-size: 13px;
    gap: 16px;
  }

  .history-toolbar label,
  .industry-toolbar label {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .history-toolbar > span,
  .industry-toolbar > span {
    color: #64748b;
    font-size: 12px;
  }

  .history-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-block: 1px solid #e2e8f0;
    padding: 16px 0;
    gap: 20px;
  }

  .history-summary > div {
    display: flex;
    flex-direction: column;
    color: #64748b;
    font-size: 12px;
    gap: 6px;
  }

  .history-summary strong {
    color: #18324d;
    font-size: 25px;
    font-variant-numeric: tabular-nums;
  }

  .history-summary small {
    margin-left: 6px;
    font-size: 12px;
    font-weight: 400;
  }

  .history-charts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .industry-workbench {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 330px;
    align-items: stretch;
    margin: 12px 0 20px;
    gap: 16px;
  }

  .industry-list {
    min-width: 0;
    padding: 12px;
    border: 1px solid #dce5ee;
    border-radius: 9px;
    background: #fff;
  }

  .list-controls {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }

  .list-controls input {
    width: 100%;
    min-width: 0;
  }

  .list-controls select {
    width: 125px;
  }

  .list-scroll {
    height: 500px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 8px 6px;
    border-bottom: 1px solid #edf1f5;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  th:first-child {
    text-align: left;
  }

  thead {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #f7f9fc;
  }

  .list-scroll th button {
    padding: 5px 4px;
    border: 0;
    background: none;
    font-size: 13px;
  }

  .selected {
    background: #edf4ff;
  }

  .rise {
    color: #b34c4c;
  }

  .fall {
    color: #07816d;
  }

  .reference-line {
    margin: 18px 0 0;
    color: #71869e;
    font-size: 11px;
  }

  .model-heading h3 {
    margin-bottom: 8px;
    font-size: 16px;
  }

  .model-heading p {
    color: #64748b;
    font-size: 13px;
  }

  .model-table td {
    line-height: 1.8;
    text-align: left;
  }

  @media (min-width: 1800px) {
    .industry-workbench {
      grid-template-columns: minmax(0, 1fr) 380px;
    }
  }

  @media (max-width: 1150px) {
    .history-charts {
      grid-template-columns: 1fr;
    }

    .industry-workbench {
      grid-template-columns: 1fr;
    }

    .list-scroll {
      height: 320px;
    }
  }

  @media (max-width: 650px) {
    .history-summary {
      grid-template-columns: 1fr;
      gap: 14px;
    }

    .history-summary > div {
      padding-bottom: 10px;
      border-bottom: 1px solid #edf1f5;
    }

    .history-summary > div:last-child {
      border: 0;
    }
  }

  .disclosure-title {
    margin: 0 0 12px;
    color: #354d68;
    font-size: 14px;
    font-weight: 600;
  }
</style>
