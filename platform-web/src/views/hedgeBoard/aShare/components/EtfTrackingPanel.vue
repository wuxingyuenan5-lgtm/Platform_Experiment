<template>
  <section id="a-share-etf-tracking" class="etf-panel">
    <BroadEtfPanel :refresh-key="refreshKey" />
    <header class="etf-heading"
      ><div><span class="eyebrow">ETF MONITOR</span><h2>机构持仓与 ETF 跟踪</h2></div
      ><button :disabled="loading || detailLoading" @click="refresh()">刷新数据</button></header
    >
    <div class="selector-bar">
      <select v-model="category" aria-label="ETF分类"
        ><option value="">全部分类</option
        ><option v-for="g in groups" :key="g">{{ g }}</option></select
      >
      <input v-model="query" aria-label="搜索ETF" placeholder="名称 / 代码" />
      <select v-model="selected" aria-label="选择ETF" class="fund-select"
        ><option v-if="!filtered.some((i) => i.code === selected)" :value="selected">{{
          detail?.meta.name || selected
        }}</option
        ><option v-for="i in filtered" :key="i.code" :value="i.code"
          >{{ i.name }} · {{ i.code }}</option
        ></select
      >
      <button
        :aria-pressed="favorites.includes(selected)"
        :aria-label="favorites.includes(selected) ? '取消当前ETF自选' : '加入当前ETF自选'"
        class="star"
        @click="toggleFavorite(selected)"
        >{{ favorites.includes(selected) ? '★' : '☆' }}</button
      >
      <label><input v-model="onlyFavorites" type="checkbox" /> 仅自选</label
      ><span class="muted">{{ filtered.length }} 个标的</span>
      <button @click="showHoldings = !showHoldings" :aria-expanded="showHoldings"
        >持仓一览 {{ showHoldings ? '收起' : '展开' }}</button
      >
    </div>
    <div v-if="showHoldings" class="holdings table-scroll"
      ><table
        ><thead
          ><tr
            ><th>自选</th><th>ETF</th><th>分类</th><th>披露占比</th><th>披露规模（亿元）</th
            ><th>报告期</th></tr
          ></thead
        ><tbody
          ><tr v-for="i in filtered" :key="i.code" :class="{ selected: i.code === selected }"
            ><td
              ><button
                @click="toggleFavorite(i.code)"
                :aria-label="`${favorites.includes(i.code) ? '取消自选' : '加入自选'}${i.code}`"
                >{{ favorites.includes(i.code) ? '★' : '☆' }}</button
              ></td
            ><td
              ><button class="text-button" @click="selected = i.code"
                >{{ i.name }} <small>{{ i.code }}</small></button
              ></td
            ><td>{{ i.display_group }}</td
            ><td>{{ fmt(i.latest_combined_ratio_pct) }}%</td
            ><td>{{ fmt(i.latest_combined_value_yi) }}</td
            ><td>{{ i.latest_report_date }}</td></tr
          ><tr v-if="!filtered.length"><td colspan="6">暂无符合条件的标的</td></tr></tbody
        ></table
      ></div
    >
    <p v-if="error" role="alert" class="notice">{{ error }}</p
    ><p v-if="loading || detailLoading" role="status">正在读取 ETF 数据…</p>
    <template v-if="detail">
      <div class="fund-heading"
        ><h3
          >{{ detail.meta.name }} <small>{{ detail.meta.code }}</small></h3
        ><span>{{ detail.groupLabel }}</span
        ><span v-if="detail.sources.market.status !== 'ready'" class="notice"
          >行情更新失败 · 保留上次数据</span
        ></div
      >
      <div class="workspace">
        <main class="chart-column">
          <div class="metrics"
            ><div
              ><span>最新交易日</span
              ><strong class="date-value">{{ latest?.date || '—' }}</strong></div
            ><div
              ><span>价格（元）</span><strong>{{ fmt(latest?.etf_qfq_close, 3) }}</strong
              ><small :class="tone(latest?.return_pct)"
                >{{ signed(latest?.return_pct) }}%</small
              ></div
            ><div
              ><span>成交额（亿元）</span
              ><strong>{{ fmt(latest?.etf_qfq_turnover_est_yi) }}</strong></div
            ><div
              ><span>总份额（亿份）</span
              ><strong>{{ fmt(latest?.qfq_total_units_yi) }}</strong></div
            ><div
              ><span>披露持仓占比</span
              ><strong>{{ fmt(detail.meta.latest_combined_ratio_pct) }}%</strong
              ><small>{{ detail.meta.latest_report_date }}</small></div
            ><div
              ><span>披露规模（亿元）</span
              ><strong>{{ fmt(detail.meta.latest_combined_value_yi) }}</strong
              ><small>{{ detail.meta.latest_report_date }}</small></div
            ></div
          >
          <div class="periods"
            ><button v-for="(p, i) in summaries" :key="p.count" @click="setPeriod(p.count)"
              ><span
                >{{ ['近一周', '近一月', '近三月'][i] }} <small>{{ p.count }} 个交易日</small></span
              ><strong :class="tone(p.change)">{{ signed(p.change) }}<em>%</em></strong
              ><div
                >成交 <b>{{ fmt(p.turnover) }}</b> 亿
                <span
                  >净申赎 <b :class="tone(p.flow)">{{ signed(p.flow) }}</b> 亿</span
                ></div
              ></button
            ></div
          >
          <div class="window-controls">
            <div class="window-heading"
              ><strong>历史走势</strong><span>{{ start }} — {{ end }}</span
              ><label><input v-model="tooltip" type="checkbox" /> 悬浮数据</label></div
            >
            <form @submit.prevent="applyDates(false)" class="date-form"
              ><input
                v-model="draftStart"
                type="date"
                aria-label="ETF开始日期"
                :min="dates[0]"
                :max="dates.at(-1)"
              /><span>至</span
              ><input
                v-model="draftEnd"
                type="date"
                aria-label="ETF结束日期"
                :min="dates[0]"
                :max="dates.at(-1)"
              /><button type="submit">应用</button
              ><button type="button" @click="setThreeYears">3年</button
              ><button type="button" @click="setPeriod(0)">全部</button
              ><button type="button" @click="latestWindow">最新</button></form
            >
            <div class="range-track"
              ><div class="range-selection" :style="rangeStyle"></div
              ><input
                type="range"
                min="0"
                :max="Math.max(0, dates.length - 1)"
                :value="startIndex"
                aria-label="图表起始位置"
                @input="slide($event, true)" /><input
                type="range"
                min="0"
                :max="Math.max(0, dates.length - 1)"
                :value="endIndex"
                aria-label="图表结束位置"
                @input="slide($event, false)"
            /></div>
            <div class="range-labels"
              ><span>{{ dates[0] }}</span
              ><span>{{ dates.at(-1) }}</span></div
            ><p v-if="dateError" role="alert" class="notice">{{ dateError }}</p>
          </div>
          <EtfLinkedCharts
            :detail="detail"
            :start="start"
            :end="end"
            :tooltip="tooltip"
            @range="setRange"
          />
        </main>
        <aside
          class="trend-panel"
          :class="{ fullscreen }"
          :aria-label="`${detail.groupLabel}趋势表`"
          @keydown.esc="fullscreen = false"
        >
          <header
            ><div
              ><h3>{{ detail.groupLabel }} · 趋势表</h3><p>分组合计与各 ETF 每日变化</p></div
            ><button
              @click="fullscreen = !fullscreen"
              :aria-label="fullscreen ? '退出趋势表全屏' : '趋势表全屏'"
              >{{ fullscreen ? '退出全屏' : '全屏' }}</button
            ></header
          >
          <form class="date-form" @submit.prevent="applyDates(true)"
            ><input v-model="trendDraftStart" type="date" aria-label="趋势表开始日期" /><span
              >至</span
            ><input v-model="trendDraftEnd" type="date" aria-label="趋势表结束日期" /><button
              type="submit"
              >应用</button
            ><button type="button" @click="resetTrend">近一周</button></form
          >
          <p v-if="trendError" role="alert" class="notice">{{ trendError }}</p>
          <div class="trend-summary"
            ><div
              ><span>区间净申赎（亿元）</span
              ><strong :class="tone(trendFlow)">{{ signed(trendFlow) }}</strong></div
            ><div
              ><span>占指数成交额</span
              ><strong :class="tone(trendRatio)">{{ signed(trendRatio) }}%</strong></div
            ><div
              ><span>成交额（亿元）</span
              ><b>{{ fmt(total(trendGroup, 'etf_qfq_turnover_est_yi')) }}</b></div
            ><div
              ><span>最大单日净申赎</span
              ><b :class="tone(maxFlow)">{{ signed(maxFlow) }} 亿</b></div
            ></div
          >
          <div class="financing-summary"
            ><span>融资 · {{ detail.margin.at(-1)?.date || '暂无数据' }}</span
            ><div
              ><span>当前 ETF 净买入 / 余额变化</span
              ><b
                >{{ signed(total(trendMargin, 'financing_net_buy_yi')) }} /
                {{
                  signed(balanceChange(detail.margin, trendStart, trendEnd, 'financing_balance_yi'))
                }}
                亿</b
              ></div
            ><div
              ><span>指数成分股净买入 / 余额变化</span
              ><b
                >{{ signed(total(trendIndexMargin, 'index_financing_net_buy_yi')) }} /
                {{
                  signed(
                    balanceChange(
                      detail.groupMargin,
                      trendStart,
                      trendEnd,
                      'index_financing_balance_yi',
                    ),
                  )
                }}
                亿</b
              ></div
            ></div
          >
          <div class="trend-caption"
            ><span>{{ trendStart }} — {{ trendEnd }}</span
            ><span
              ><i class="legend-hot"></i> ≥90分位 <i class="legend-cool"></i> ≤10分位</span
            ></div
          >
          <div class="trend-table table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>日期 / ETF</th><th title="分组涨跌幅按当日成交额加权">涨跌幅</th
                  ><th>成交额<small>亿元 / 分位</small></th
                  ><th>份额变化<small>亿份 / 分位</small></th
                  ><th>净申赎<small>亿元 / 分位</small></th
                  ><th>占指数<small>成交额 %</small></th
                  ><th>融资净买入<small>亿元</small></th></tr
                ></thead
              ><tbody v-for="block in trendBlocks" :key="block.code"
                ><tr class="group-heading"
                  ><th colspan="7"
                    ><button v-if="block.code !== 'group'" @click="selected = block.code"
                      >{{ block.name }} <small>{{ block.code }}</small></button
                    ><span v-else>{{ block.name }} · 合计</span
                    ><small>{{ block.rows.length }} 个交易日</small></th
                  ></tr
                ><tr v-for="r in block.rows" :key="r.date"
                  ><td>{{ r.date.slice(5) }}</td
                  ><td :class="tone(r.return_pct)">{{ signed(r.return_pct) }}%</td
                  ><td
                    >{{ fmt(r.etf_qfq_turnover_est_yi)
                    }}<small :class="rankClass(r.etf_qfq_turnover_est_yi_percentile)">{{
                      rank(r.etf_qfq_turnover_est_yi_percentile)
                    }}</small></td
                  ><td :class="tone(r.qfq_delta_units_yi)"
                    >{{ signed(r.qfq_delta_units_yi, 3)
                    }}<small :class="rankClass(r.qfq_delta_units_yi_percentile)">{{
                      rank(r.qfq_delta_units_yi_percentile)
                    }}</small></td
                  ><td :class="tone(r.flow_yi)"
                    >{{ signed(r.flow_yi)
                    }}<small :class="rankClass(r.flow_yi_percentile)">{{
                      rank(r.flow_yi_percentile)
                    }}</small></td
                  ><td :class="tone(r.flow_to_index_pct)">{{ signed(r.flow_to_index_pct) }}</td
                  ><td :class="tone(r.financing_net_buy_yi)">{{
                    signed(r.financing_net_buy_yi)
                  }}</td></tr
                ><tr v-if="!block.rows.length"><td colspan="7">区间内暂无数据</td></tr></tbody
              ></table
            ></div
          >
        </aside>
      </div>
      <details class="method"
        ><summary>持仓披露与数据口径</summary
        ><p
          >来源：<a href="https://wangwang-etf.com/" target="_blank" rel="noopener noreferrer"
            >汪汪 ETF</a
          >公开数据。持仓为报告期快照；日度份额变动不能归因于特定投资者。价格与份额使用来源调整口径，成交额与净申赎金额为估算值。</p
        ><p
          >净申赎金额 = 调整后份额变化 ×
          前复权均价；均价缺失时采用前复权收盘价。分位为截至当日的历史排名，至少 60
          个有效观测；份额与净申赎按绝对值排名。分组合计须覆盖全部成员，涨跌幅按成交额加权。区间数据不完整时不显示合计。</p
        ><div class="table-scroll"
          ><table
            ><thead
              ><tr><th>报告期</th><th>汇金 / 证金合计占比</th><th>披露规模（亿元）</th></tr></thead
            ><tbody
              ><tr v-for="d in detail.disclosures" :key="d.report_date"
                ><td>{{ d.report_date }}</td
                ><td>{{ fmt(d.combined_ratio_pct) }}%</td
                ><td>{{ fmt(d.combined_value_yi) }}</td></tr
              ></tbody
            ></table
          ></div
        ></details
      >
      <section class="flow-history">
        <button
          type="button"
          class="flow-history-toggle"
          :aria-expanded="showFlowCharts"
          aria-controls="etf-flow-history"
          :aria-label="showFlowCharts ? '收起ETF申赎历史' : '展开ETF申赎历史'"
          @click="showFlowCharts = !showFlowCharts"
          ><strong>ETF申赎历史</strong><span>{{ showFlowCharts ? '收起' : '展开' }}</span></button
        >
        <div v-if="showFlowCharts" id="etf-flow-history">
          <EtfLinkedCharts
            flows-only
            :detail="detail"
            :start="start"
            :end="end"
            :tooltip="tooltip"
            @range="setRange"
          />
        </div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
  import BroadEtfPanel from './BroadEtfPanel.vue';
  import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
  import {
    getEtfCatalog,
    getEtfDetail,
    type EtfCatalog,
    type EtfDetail,
    type EtfValue,
    type EtfRow,
  } from '@/api/etfTracking';
  import { useUserStore } from '@/store/modules/user';
  import EtfLinkedCharts from './EtfLinkedCharts.vue';
  import {
    numeric,
    total,
    trailingSummary,
    ranged,
    balanceChange,
    alignDates,
  } from './etfTrackingModel';

  import { useResearchViewState, useResearchSnapshots } from '../../composables/researchWorkspace';

  const emit = defineEmits<{ ready: [] }>();
  const snapshots = useResearchSnapshots();
  const props = defineProps<{ refreshKey?: number }>();
  const user = useUserStore();
  const storageKey = computed(() => `etf-tracking:${user.getUserInfo.userId || 'anonymous'}`);
  const favorites = ref<string[]>([]),
    catalog = shallowRef<EtfCatalog>(),
    detail = shallowRef<EtfDetail>();
  const loading = ref(false),
    detailLoading = ref(false),
    error = ref('');
  const showFlowCharts = ref(false);
  const selected = useResearchViewState('selected', '510310'),
    query = useResearchViewState('query', ''),
    category = useResearchViewState('category', ''),
    onlyFavorites = useResearchViewState('onlyFavorites', false),
    showHoldings = useResearchViewState('showHoldings', true);
  const start = useResearchViewState('start', ''),
    end = useResearchViewState('end', ''),
    draftStart = useResearchViewState('draftStart', ''),
    draftEnd = useResearchViewState('draftEnd', ''),
    tooltip = useResearchViewState('tooltip', true),
    dateError = ref('');
  const trendStart = useResearchViewState('trendStart', ''),
    trendEnd = useResearchViewState('trendEnd', ''),
    trendDraftStart = useResearchViewState('trendDraftStart', ''),
    trendDraftEnd = useResearchViewState('trendDraftEnd', ''),
    trendError = ref(''),
    fullscreen = ref(false);
  let catalogController: AbortController | undefined, detailController: AbortController | undefined;
  watch(
    storageKey,
    (key) => {
      try {
        const value = JSON.parse(localStorage.getItem(key) || '[]');
        favorites.value = Array.isArray(value)
          ? value.filter((v) => typeof v === 'string' && /^\d{6}$/.test(v))
          : [];
      } catch {
        favorites.value = [];
      }
    },
    { immediate: true },
  );
  function toggleFavorite(code: string) {
    const next = favorites.value.includes(code)
      ? favorites.value.filter((c) => c !== code)
      : [...favorites.value, code];
    try {
      localStorage.setItem(storageKey.value, JSON.stringify(next));
      favorites.value = next;
    } catch {
      error.value = '浏览器未允许保存自选。';
    }
  }
  const numberFormats = [0, 1, 2, 3, 4].map(
    (digits) =>
      new Intl.NumberFormat('zh-CN', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }),
  );
  const fmt = (v: EtfValue | undefined, digits = 2) => {
    const value = numeric(v);
    return value == null ? '—' : numberFormats[digits].format(value);
  };
  const signed = (v: EtfValue | undefined, digits = 2) =>
    (numeric(v) != null && numeric(v)! > 0 ? '+' : '') + fmt(v, digits);
  const tone = (v: EtfValue | undefined) =>
    (numeric(v) ?? 0) > 0 ? 'up' : (numeric(v) ?? 0) < 0 ? 'down' : '';
  const rank = (v: EtfValue | undefined) => (numeric(v) == null ? '—' : `${fmt(v, 0)}分位`);
  const rankClass = (v: EtfValue | undefined) =>
    numeric(v) == null
      ? 'rank'
      : numeric(v)! >= 90
      ? 'rank hot'
      : numeric(v)! <= 10
      ? 'rank cool'
      : 'rank';
  const groups = computed(() => [
    ...new Set((catalog.value?.items || []).map((i) => i.display_group)),
  ]);
  const filtered = computed(() =>
    (catalog.value?.items || [])
      .filter(
        (i) =>
          (!category.value || i.display_group === category.value) &&
          (!onlyFavorites.value || favorites.value.includes(i.code)) &&
          `${i.name} ${i.code}`.toLowerCase().includes(query.value.trim().toLowerCase()),
      )
      .sort(
        (a, b) =>
          (numeric(b.latest_combined_ratio_pct) ?? -Infinity) -
          (numeric(a.latest_combined_ratio_pct) ?? -Infinity),
      ),
  );
  const dates = computed(() => detail.value?.series.map((r) => r.date) || []);
  const latest = computed(() => detail.value?.series.at(-1));
  const summaries = computed(() =>
    [5, 21, 63].map((n) => trailingSummary(detail.value?.series || [], n)),
  );
  const startIndex = computed(() => Math.max(0, dates.value.indexOf(start.value)));
  const endIndex = computed(() => Math.max(0, dates.value.indexOf(end.value)));
  const rangeStyle = computed(() => ({
    left: `${(startIndex.value / Math.max(1, dates.value.length - 1)) * 100}%`,
    right: `${100 - (endIndex.value / Math.max(1, dates.value.length - 1)) * 100}%`,
  }));
  function setRange(a: string, b: string) {
    start.value = draftStart.value = a;
    end.value = draftEnd.value = b;
    dateError.value = '';
  }
  function setPeriod(count: number) {
    if (dates.value.length)
      setRange(
        dates.value[Math.max(0, dates.value.length - (count || dates.value.length))],
        dates.value.at(-1)!,
      );
  }
  function latestWindow() {
    setPeriod(endIndex.value - startIndex.value + 1);
  }
  function setThreeYears() {
    const latestDate = dates.value.at(-1);
    if (!latestDate) return;
    const cutoff = new Date(`${latestDate}T00:00:00Z`);
    cutoff.setUTCFullYear(cutoff.getUTCFullYear() - 3);
    const first = dates.value.find((date) => date >= cutoff.toISOString().slice(0, 10));
    setRange(first || dates.value[0], latestDate);
  }
  function slide(event: Event, left: boolean) {
    const i = Number((event.target as HTMLInputElement).value);
    setRange(
      dates.value[left ? Math.min(i, endIndex.value) : startIndex.value],
      dates.value[left ? endIndex.value : Math.max(i, startIndex.value)],
    );
  }
  function resetTrend() {
    trendStart.value = trendDraftStart.value =
      dates.value[Math.max(0, dates.value.length - 5)] || '';
    trendEnd.value = trendDraftEnd.value = dates.value.at(-1) || '';
    trendError.value = '';
  }
  function applyDates(trend: boolean) {
    const a = trend ? trendDraftStart.value : draftStart.value,
      b = trend ? trendDraftEnd.value : draftEnd.value;
    const targetError = trend ? trendError : dateError;
    if (!a || !b || a > b) {
      targetError.value = '请选择有效的起止日期。';
      return;
    }
    const available = dates.value.filter((d) => d >= a && d <= b);
    if (!available.length) {
      targetError.value = '所选区间没有交易数据。';
      return;
    }
    targetError.value = '';
    if (trend) {
      trendStart.value = trendDraftStart.value = available[0];
      trendEnd.value = trendDraftEnd.value = available.at(-1)!;
    } else setRange(available[0], available.at(-1)!);
  }
  const trendGroup = computed(() =>
    ranged(detail.value?.group || [], trendStart.value, trendEnd.value),
  );
  const trendMargin = computed(() =>
    alignDates(
      detail.value?.margin || [],
      trendGroup.value.map((r) => r.date),
    ),
  );
  const trendIndexMargin = computed(() =>
    alignDates(
      detail.value?.groupMargin || [],
      trendGroup.value.map((r) => r.date),
    ),
  );
  const trendFlow = computed(() => total(trendGroup.value, 'flow_yi'));
  const trendRatio = computed(() => {
    const amount = total(trendGroup.value, 'index_turnover_yi');
    return trendFlow.value != null && amount ? (trendFlow.value / amount) * 100 : null;
  });
  const maxFlow = computed(() => {
    const values = trendGroup.value.map((r) => numeric(r.flow_yi));
    return values.length && values.every((v) => v != null)
      ? values.reduce<number>((best, v) => (Math.abs(v!) > Math.abs(best) ? v! : best), 0)
      : null;
  });
  const trendBlocks = computed<Array<{ code: string; name: string; rows: EtfRow[] }>>(() => [
    {
      code: 'group',
      name: detail.value?.groupLabel || '',
      rows: trendGroup.value
        .map((row) => ({
          ...row,
          financing_net_buy_yi: total(
            (detail.value?.members || []).map(
              (member) =>
                member.margin.find((margin) => margin.date === row.date) || { date: row.date },
            ),
            'financing_net_buy_yi',
          ),
        }))
        .reverse(),
    },
    ...(detail.value?.members || []).map((m) => {
      const margin = new Map(m.margin.map((r) => [r.date, r]));
      return {
        code: m.meta.code,
        name: m.meta.name,
        rows: ranged(m.series, trendStart.value, trendEnd.value)
          .map((r) => ({
            ...r,
            financing_net_buy_yi: margin.get(r.date)?.financing_net_buy_yi ?? null,
          }))
          .reverse(),
      };
    }),
  ]);
  async function loadCatalog(force = false) {
    catalogController?.abort();
    const controller = (catalogController = new AbortController());
    loading.value = true;
    try {
      const value =
        (!force && snapshots.get<EtfCatalog>('etf:catalog')) ||
        (await getEtfCatalog(controller.signal));
      if (!controller.signal.aborted) {
        catalog.value = value;
        snapshots.set('etf:catalog', value);
      }
    } catch {
      if (!controller.signal.aborted) error.value = 'ETF目录暂不可用，请重试。';
    } finally {
      if (!controller.signal.aborted) loading.value = false;
    }
  }
  async function loadDetail(force = false) {
    detailController?.abort();
    const controller = (detailController = new AbortController());
    detailLoading.value = true;
    error.value = '';
    const oldGroup = detail.value?.groupLabel;
    if (detail.value?.meta.code !== selected.value) detail.value = undefined;
    try {
      const value =
        (!force && snapshots.get<EtfDetail>(`etf:${selected.value}`)) ||
        (await getEtfDetail(selected.value, controller.signal));
      if (!controller.signal.aborted) {
        detail.value = value;
        snapshots.set(`etf:${selected.value}`, value);
        const available = value.series.filter((r) => r.date >= start.value && r.date <= end.value);
        if (available.length) setRange(available[0].date, available.at(-1)!.date);
        else setThreeYears();
        if (!trendStart.value || (oldGroup != null && oldGroup !== value.groupLabel)) resetTrend();
      }
    } catch {
      if (!controller.signal.aborted) error.value = 'ETF详情暂不可用，请重试。';
    } finally {
      if (!controller.signal.aborted) {
        detailLoading.value = false;
        emit('ready');
      }
    }
  }
  function refresh(force = true) {
    void loadCatalog(force);
    void loadDetail(force);
  }
  function escape(event: KeyboardEvent) {
    if (event.key === 'Escape') fullscreen.value = false;
  }
  watch(selected, () => void loadDetail());
  watch(
    () => props.refreshKey,
    (_value, previous) => refresh(previous !== undefined),
    { immediate: true },
  );
  onMounted(() => window.addEventListener('keydown', escape));
  onBeforeUnmount(() => {
    catalogController?.abort();
    detailController?.abort();
    window.removeEventListener('keydown', escape);
  });
</script>

<style scoped>
  :global(.a-share-page-content) {
    overflow: clip;
  }

  .etf-panel {
    margin-top: 24px;
    padding: 22px;
    border: 1px solid #dfe5ef;
    border-radius: 14px;
    background: #f6f8fc;
    color: #27364c;
    font-family: inherit;
    font-variant-numeric: tabular-nums;
    scroll-margin-top: 90px;
  }

  .etf-panel :deep(button),
  .etf-panel :deep(input),
  .etf-panel :deep(select),
  .etf-panel :deep(table) {
    font-family: inherit;
  }

  .etf-heading,
  .selector-bar,
  .fund-heading,
  .window-heading,
  .trend-panel header,
  .trend-caption {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .etf-heading {
    justify-content: space-between;
    margin-bottom: 18px;
  }

  .eyebrow {
    color: #5475ad;
    font-size: 10px;
    letter-spacing: 2px;
  }

  h2 {
    margin: 3px 0 0;
    font-size: 21px;
    font-weight: 650;
  }

  h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 650;
  }

  button,
  input,
  select {
    font: inherit;
  }

  button,
  select,
  input[type='date'],
  input:not([type]) {
    padding: 6px 9px;
    border: 1px solid #d8e0ed;
    border-radius: 6px;
    background: #fff;
    color: #40526c;
    font-size: 12px;
  }

  button {
    cursor: pointer;
  }

  button:hover {
    border-color: #2864ec;
    color: #2864ec;
  }

  button:disabled {
    opacity: 0.5;
    cursor: wait;
  }

  button:focus-visible,
  input:focus-visible,
  select:focus-visible {
    outline: 2px solid #2864ec;
    outline-offset: 2px;
  }

  input[type='checkbox'] {
    accent-color: #2864ec;
  }

  .selector-bar {
    flex-wrap: wrap;
    padding: 12px;
    border: 1px solid #dfe5ef;
    border-radius: 9px;
    background: #fff;
  }

  .selector-bar input:not([type]) {
    width: 130px;
  }

  .fund-select {
    min-width: 210px;
  }

  .selector-bar label {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
  }

  .selector-bar .star {
    padding: 0 8px;
    color: #c59837;
    font-size: 20px;
  }

  .muted {
    color: #8591a4;
    font-size: 11px;
  }

  .fund-heading {
    padding: 17px 0 12px;
  }

  .fund-heading small {
    margin-left: 7px;
    color: #8792a5;
    font-size: 12px;
    font-weight: 400;
  }

  .fund-heading > span {
    color: #8190a6;
    font-size: 11px;
  }

  .workspace {
    display: grid;
    grid-template-columns: minmax(0, 1.9fr) minmax(370px, 1fr);
    gap: 16px;
    align-items: start;
  }

  .chart-column {
    min-width: 0;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 7px;
  }

  .metrics > div {
    display: flex;
    flex-direction: column;
    min-height: 85px;
    padding: 11px 9px;
    border: 1px solid #dfe5ef;
    border-radius: 8px;
    background: #fff;
    gap: 5px;
  }

  .metrics span {
    color: #8491a4;
    font-size: 10px;
    white-space: nowrap;
  }

  .metrics strong {
    font-size: 19px;
    font-weight: 650;
    letter-spacing: -0.5px;
  }

  .metrics .date-value {
    padding-top: 5px;
    font-size: 13px;
    letter-spacing: 0;
  }

  .metrics small {
    color: #8c98a9;
    font-size: 10px;
  }

  .periods {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
    margin: 10px 0;
  }

  .periods > button {
    padding: 12px 13px;
    border-radius: 8px;
    text-align: left;
  }

  .periods > button > span {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    font-weight: 600;
  }

  .periods small {
    color: #99a3b3;
    font-size: 10px;
    font-weight: 400;
  }

  .periods strong {
    display: block;
    margin: 8px 0;
    font-size: 23px;
    font-weight: 600;
  }

  .periods em {
    font-size: 13px;
    font-style: normal;
  }

  .periods button > div {
    display: flex;
    flex-wrap: wrap;
    color: #8894a8;
    font-size: 10px;
    gap: 4px;
  }

  .periods b {
    color: #52637e;
    font-weight: 500;
  }

  .window-controls {
    position: sticky;
    z-index: 4;
    top: 72px;
    margin-bottom: 8px;
    padding: 10px 12px 7px;
    border: 1px solid #dfe5ef;
    border-radius: 8px;
    background: #f6f8fc;
    box-shadow: 0 3px 8px #263c6010;
  }

  .window-heading strong {
    font-size: 12px;
  }

  .window-heading > span {
    color: #8190a6;
    font-size: 10px;
  }

  .window-heading label {
    display: flex;
    align-items: center;
    margin-left: auto;
    font-size: 10px;
    gap: 4px;
  }

  .date-form {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 9px 0;
    color: #8995a8;
    font-size: 10px;
    gap: 5px;
  }

  .date-form input {
    width: 125px;
    min-width: 0;
    padding: 4px;
    font-size: 10px;
  }

  .date-form button {
    padding: 4px 7px;
    font-size: 10px;
  }

  .range-track {
    position: relative;
    height: 5px;
    margin: 15px 7px 7px;
    border-radius: 4px;
    background: #e1e7f1;
  }

  .range-selection {
    position: absolute;
    top: 0;
    bottom: 0;
    background: #a8bff6;
  }

  .range-track input {
    position: absolute;
    inset: -7px 0 auto;
    width: 100%;
    height: 20px;
    margin: 0;
    appearance: none;
    background: transparent;
    pointer-events: none;
  }

  .range-track input::-webkit-slider-thumb {
    width: 12px;
    height: 17px;
    border: 2px solid #5c83e7;
    border-radius: 4px;
    background: #fff;
    cursor: ew-resize;
    pointer-events: auto;
    appearance: none;
  }

  .range-track input::-moz-range-thumb {
    width: 10px;
    height: 15px;
    border: 2px solid #5c83e7;
    border-radius: 4px;
    background: #fff;
    cursor: ew-resize;
    pointer-events: auto;
  }

  .range-labels {
    display: flex;
    justify-content: space-between;
    color: #91a0b6;
    font-size: 9px;
  }

  .trend-panel {
    position: sticky;
    top: 72px;
    min-width: 0;
    padding: 14px;
    overflow: hidden;
    border: 1px solid #dce3ef;
    border-radius: 10px;
    background: #fff;
  }

  .trend-panel header {
    justify-content: space-between;
  }

  .trend-panel h3 {
    font-size: 13px;
  }

  .trend-panel header p {
    margin: 4px 0;
    color: #8c99ac;
    font-size: 10px;
  }

  .trend-panel header button {
    font-size: 10px;
    white-space: nowrap;
  }

  .trend-summary {
    display: grid;
    grid-template-columns: 1fr 1fr;
    padding: 12px 0;
    border-top: 1px solid #e9edf4;
    border-bottom: 1px solid #e9edf4;
    gap: 12px 9px;
  }

  .trend-summary > div {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .trend-summary span {
    color: #7e8da3;
    font-size: 10px;
  }

  .trend-summary strong {
    font-size: 20px;
    font-weight: 600;
  }

  .trend-summary b {
    font-size: 12px;
    font-weight: 500;
  }

  .financing-summary {
    padding: 10px 0;
    color: #8592a6;
    font-size: 9px;
  }

  .financing-summary > span {
    display: block;
    margin-bottom: 6px;
    color: #60738f;
  }

  .financing-summary > div {
    display: flex;
    justify-content: space-between;
    gap: 5px;
    margin: 4px 0;
  }

  .financing-summary b {
    color: #586d8b;
    font-size: 10px;
    font-weight: 400;
  }

  .trend-caption {
    justify-content: space-between;
    margin: 5px 0 9px;
    color: #8c9ab0;
    font-size: 9px;
    gap: 4px;
  }

  .trend-caption i {
    display: inline-block;
    width: 6px;
    height: 6px;
    margin-left: 4px;
    border-radius: 2px;
  }

  .legend-hot {
    background: #efc0c2;
  }

  .legend-cool {
    background: #addfd4;
  }

  .table-scroll {
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    text-align: right;
    white-space: nowrap;
  }

  th {
    background: #f6f8fc;
    color: #7f8da3;
    font-weight: 500;
  }

  td,
  th {
    padding: 8px 9px;
    border-bottom: 1px solid #edf0f5;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  td small,
  th small {
    display: block;
    margin-top: 3px;
    color: #9aa6b7;
    font-size: 9px;
    font-weight: 400;
  }

  .trend-table {
    max-height: max(240px, calc(100vh - 420px));
    margin: 0 -14px -14px;
  }

  .trend-table table {
    font-size: 10px;
  }

  .trend-table th,
  .trend-table td {
    padding: 7px 8px;
  }

  .trend-table thead th {
    position: sticky;
    z-index: 2;
    top: 0;
  }

  .trend-table th small {
    font-size: 8px;
  }

  .group-heading th {
    background: #edf2fb;
    color: #496289;
    font-weight: 600;
    text-align: left;
  }

  .group-heading th > small {
    display: inline;
    margin-left: 10px;
    float: right;
  }

  .group-heading button {
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
    font-size: 10px;
  }

  .group-heading button small {
    display: inline;
  }

  .rank {
    display: table;
    margin: 3px 0 0 auto;
    padding: 1px 4px;
    border-radius: 3px;
    background: #f3f5f9;
    color: #8794aa;
  }

  .rank.hot {
    background: #fce8e8;
    color: #d36c70;
  }

  .rank.cool {
    background: #e2f4ee;
    color: #379b83;
  }

  .up {
    color: #dc6269 !important;
  }

  .down {
    color: #2b9a82 !important;
  }

  .notice {
    margin: 8px 0;
    color: #b07c32 !important;
    font-size: 11px;
  }

  .holdings {
    max-height: 280px;
    margin-top: 8px;
    border: 1px solid #e0e6f0;
    border-radius: 8px;
    background: #fff;
  }

  .holdings th {
    position: sticky;
    top: 0;
  }

  .holdings .selected {
    background: #f0f5ff;
  }

  .text-button {
    padding: 0;
    border: 0;
    background: none;
  }

  .text-button small {
    display: inline;
  }

  .flow-history {
    margin-top: 18px;
  }

  .flow-history-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    margin-bottom: 10px;
    padding: 12px 16px;
  }

  .method {
    margin-top: 15px;
    color: #8492a6;
    font-size: 11px;
    line-height: 1.8;
  }

  .method summary {
    color: #607a9f;
    cursor: pointer;
  }

  .method a {
    color: #2864ec;
  }

  .method table {
    max-width: 650px;
  }

  .fullscreen {
    display: flex;
    position: fixed;
    z-index: 3000;
    flex-direction: column;
    padding: 20px;
    box-shadow: 0 0 0 100vmax #172b4d66;
    inset: 24px;
  }

  .fullscreen .trend-table {
    flex: 1;
    max-height: none;
    margin: 0 -20px -20px;
  }

  .fullscreen .trend-summary {
    grid-template-columns: repeat(4, 1fr);
  }

  .fullscreen .financing-summary {
    max-width: 600px;
  }

  .fullscreen table {
    font-size: 13px;
  }

  .fullscreen .trend-table td,
  .fullscreen .trend-table th {
    padding: 10px 18px;
  }

  @media (min-width: 1700px) {
    .workspace {
      grid-template-columns: minmax(0, 2fr) minmax(460px, 1fr);
    }
  }

  @media (max-width: 1150px) {
    .workspace {
      grid-template-columns: minmax(0, 1fr);
    }

    .trend-panel {
      position: static;
    }

    .trend-panel.fullscreen {
      position: fixed;
    }

    .trend-table {
      max-height: 600px;
    }

    .metrics strong {
      font-size: 18px;
    }
  }

  @media (max-width: 650px) {
    .etf-panel {
      padding: 12px;
    }

    .metrics {
      grid-template-columns: repeat(3, 1fr);
    }

    .periods {
      gap: 5px;
    }

    .periods > button {
      padding: 9px;
    }

    .periods > button > span {
      display: block;
    }

    .periods small {
      display: block;
    }

    .periods strong {
      font-size: 20px;
    }

    .window-heading > span {
      display: none;
    }

    .fullscreen {
      inset: 8px;
    }

    .fullscreen .trend-summary {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
