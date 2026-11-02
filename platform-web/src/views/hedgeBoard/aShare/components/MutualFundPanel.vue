<template>
  <section class="mutual-funds" aria-label="公募持仓跟踪">
    <header class="heading">
      <div><h2>公募持仓</h2><p>主动权益 · 普通股票、偏股混合与灵活配置</p></div>
      <label
        >报告期
        <select v-model="selectedPeriod" :disabled="loading" @change="load"
          ><option v-for="d in overview?.dates || []" :key="d" :value="d">{{ d }}</option></select
        ></label
      >
    </header>
    <p v-if="loading" role="status">正在读取公募披露数据…</p>
    <p v-if="error" class="notice" role="alert"
      >{{ error }} <button type="button" @click="load">重试</button></p
    >
    <template v-if="overview">
      <p v-if="overview.collectionStatus === 'paused'" class="notice" role="status"
        >公募持仓已暂停更新，以下为已留存的历史数据。</p
      >
      <p class="source"
        >{{ overview.source || '天天基金公开基金档案' }} · 数据整理于
        {{ time(overview.generatedAt) }}</p
      >
      <p v-if="overview.status !== 'ready'" class="notice" role="status">
        {{
          overview.status === 'stale' ? '来源更新延迟，保留已取得的数据。' : '当前为部分覆盖样本。'
        }}
        已取得 {{ overview.collectedCount || 0 }} /
        {{ overview.expectedCount || 0 }} 个同名份额归并组合，已检查
        {{ overview.attemptedCount || 0 }} 个。
      </p>
      <div class="metrics">
        <article
          ><span>样本股票仓位</span><strong>{{ fmt(overview.summary?.stockPct, '%') }}</strong
          ><small
            >{{ overview.summary?.fundCount || 0 }} 个同日有效组合 · 净资产加权</small
          ></article
        >
        <article
          ><span>股票仓位环比</span
          ><strong>{{ signed(overview.summary?.stockChangePp, ' 个百分点') }}</strong
          ><small>{{ overview.summary?.commonCount || 0 }} 个两期可比组合</small></article
        >
        <article
          ><span>样本净资产</span><strong>{{ yi(overview.summary?.navYuan) }}</strong
          ><small>同日有效组合 · 亿元</small></article
        >
        <article
          ><span>样本现金占净比</span><strong>{{ fmt(overview.summary?.cashPct, '%') }}</strong
          ><small>{{ overview.summary?.cashPctCount || 0 }} 个有披露值的组合</small></article
        >
      </div>
      <div class="card">
        <VibeTimeChart
          v-if="overview.history.length"
          title="样本仓位历史"
          frequency="quarterly"
          y-label="占净资产（%）"
          :precision="2"
          :initial-window="12"
          :dates="overview.history.map((r) => r.date)"
          :series="overviewSeries"
        />
        <p class="definition"
          >各期样本数量随披露覆盖变化；环比卡片只比较同一批基金。现金占净比不能直接解释为可继续买入的额度。</p
        >
        <details
          ><summary>历史样本覆盖</summary
          ><div class="table-scroll" tabindex="0" role="region" aria-label="公募历史覆盖"
            ><table
              ><thead
                ><tr
                  ><th>报告期</th><th>有效组合</th><th>股票仓位</th><th>净资产 / 亿元</th></tr
                ></thead
              ><tbody
                ><tr v-for="r in overview.history" :key="r.date"
                  ><th>{{ r.date }}</th
                  ><td>{{ r.fundCount }}</td
                  ><td>{{ fmt(r.stockPct, '%') }}</td
                  ><td>{{ yi(r.navYuan) }}</td></tr
                ></tbody
              ></table
            ></div
          ></details
        >
      </div>
      <section class="card">
        <div class="section-heading"
          ><h3>行业配置</h3
          ><label
            >市场
            <select v-model="industryMarket"
              ><option value="CN">A股 · 证监会行业</option
              ><option value="HK">港股 · 来源行业分类</option></select
            ></label
          ></div
        >
        <p class="definition"
          >占样本基金净资产比例；季度变化使用两期行业表完整的相同组合。两地行业分类分别展示。</p
        >
        <div class="table-scroll" tabindex="0" role="region" aria-label="公募行业配置">
          <table
            ><thead
              ><tr
                ><th>行业</th><th>配置比例</th><th>环比 / 百分点</th><th>持有 / 有效样本</th
                ><th>两期可比样本</th></tr
              ></thead
            ><tbody>
              <tr v-for="row in industryRows" :key="row.code"
                ><th>{{ row.name }}</th
                ><td
                  ><span
                    class="bar"
                    :style="{ width: `${Math.min(80, num(row.weightPct) || 0)}px` }"
                  ></span
                  >{{ fmt(row.weightPct, '%') }}</td
                ><td>{{ signed(row.changePp) }}</td
                ><td>{{ row.fundCount }} / {{ row.sampleCount }}</td
                ><td>{{ row.commonCount }}</td></tr
              >
              <tr v-if="!industryRows.length"
                ><td colspan="5">本期尚无可核对完整性的行业数据</td></tr
              >
            </tbody></table
          >
        </div>
      </section>
      <section class="card">
        <div class="section-heading"
          ><h3>前十大重仓股汇总</h3
          ><label
            >筛选股票 <input v-model="stockSearch" type="search" placeholder="名称 / 代码" /></label
        ></div>
        <p class="definition"
          >{{
            overview.holdingFundCount || 0
          }}
          个组合的前十大披露样本。股数变化仅比较两期均披露该股票的同一批基金，未剔除送转等公司行动。</p
        >
        <div class="table-scroll" tabindex="0" role="region" aria-label="公募重仓股排行">
          <table
            ><thead
              ><tr
                ><th>股票</th><th>持仓市值 / 亿元</th><th>持有基金数</th><th>可比股数环比</th
                ><th>可比基金数</th></tr
              ></thead
            ><tbody>
              <tr v-for="row in stocks" :key="`${row.market}:${row.code}`"
                ><th
                  >{{ row.name }}<small>{{ row.market }} {{ row.code }}</small></th
                ><td>{{ yi(row.valueYuan) }}</td
                ><td>{{ row.fundCount }}</td
                ><td>{{ signed(row.shareChangePct, '%') }}</td
                ><td>{{ row.comparableCount }}</td></tr
              >
              <tr v-if="!stocks.length"><td colspan="5">暂无匹配的重仓明细</td></tr>
            </tbody></table
          >
        </div>
        <button
          v-if="stockLimit < filteredStocks.length"
          type="button"
          class="more"
          @click="stockLimit += 50"
          >再显示50只</button
        >
      </section>
      <section class="card">
        <div class="section-heading"
          ><h3>基金追踪</h3
          ><label
            >查找基金
            <input v-model="fundSearch" type="search" placeholder="基金、代码、现任经理" /></label
        ></div>
        <div class="table-scroll fund-list" tabindex="0" role="region" aria-label="基金列表">
          <table
            ><thead
              ><tr
                ><th>基金</th><th>现任经理</th><th>股票仓位</th><th>净资产 / 亿元</th
                ><th>最新报告期</th></tr
              ></thead
            ><tbody>
              <tr
                v-for="fund in funds"
                :key="fund.code"
                :class="{ selected: selectedCode === fund.code }"
                ><th
                  ><button type="button" @click="selectFund(fund.code)"
                    >{{ fund.name }}<small>{{ fund.code }} · {{ fund.type }}</small></button
                  ></th
                ><td>{{ fund.manager || '—' }}</td
                ><td>{{ fmt(fund.stockPct, '%') }}</td
                ><td>{{ yi(fund.navYuan) }}</td
                ><td>{{ fund.date }}</td></tr
              >
              <tr v-if="!funds.length"><td colspan="5">暂无匹配基金</td></tr>
            </tbody></table
          >
        </div>
        <button
          v-if="fundLimit < filteredFunds.length"
          type="button"
          class="more"
          @click="fundLimit += 150"
          >再显示150只基金</button
        >
        <p class="definition"
          >列表显示各基金最新披露，详情可选历史报告期。同名份额只取一个代表，组合汇总另按已取得的基金全称去重；规模与持仓分母不一致的组合不参与加权。</p
        >
      </section>
      <section v-if="selectedCode" ref="detailHost" class="card detail" aria-label="单基金历史">
        <p v-if="detailLoading" role="status">正在读取基金历史…</p>
        <p v-if="detailError" class="notice" role="alert"
          >基金历史读取失败 <button type="button" @click="selectFund(selectedCode)">重试</button></p
        >
        <template v-if="detail">
          <div class="section-heading"
            ><div
              ><h3>{{ detail.fund.name }}</h3
              ><p
                >{{ detail.data.profile?.company }} · 现任经理
                {{ detail.data.profile?.manager || '—' }}</p
              ></div
            ><label
              >持仓截至
              <select v-model="detailPeriod"
                ><option v-for="d in detailDates" :key="d" :value="d">{{ d }}</option></select
              ></label
            ></div
          >
          <p v-if="detail.status !== 'ready'" class="notice"
            >部分来源尚未更新，以下保留各自原始日期的数据。</p
          >
          <p class="source"
            >最近采集 {{ time(detail.attemptedAt) }} · 股票明细
            {{ holding?.coverage === 'full' ? '中报 / 年报完整列表' : '季度重仓披露' }} ·
            {{ holding?.date || '暂无明细' }}</p
          >
          <div class="report-links"
            ><a
              v-for="report in selectedReports"
              :key="report.url"
              :href="report.url"
              target="_blank"
              rel="noopener noreferrer"
              >{{ report.title }} · 公告 {{ report.publishedAt }} ↗</a
            ><span v-if="!selectedReports.length">本期报告公告日期尚未取得</span></div
          >
          <p class="definition"
            >经理观点见原始报告的“管理人报告”；报告期末仓位与公告日期分别保留。</p
          >
          <VibeTimeChart
            v-if="detailHistory.length"
            :key="detail.fund.code"
            :title="`${detail.fund.name} · 仓位历史`"
            frequency="quarterly"
            y-label="占净资产（%）"
            :precision="2"
            :initial-window="12"
            :dates="detailHistory.map((r) => r.date)"
            :series="detailSeries"
          />
          <h4>规模与申赎 · {{ detail.fund.code }} 代表份额</h4>
          <div class="table-scroll" tabindex="0" role="region" aria-label="基金申赎历史"
            ><table
              ><thead
                ><tr
                  ><th>报告期</th><th>申购 / 亿份</th><th>赎回 / 亿份</th><th>期末份额 / 亿份</th
                  ><th>净资产 / 亿元</th></tr
                ></thead
              ><tbody
                ><tr v-for="r in (detail.data.sizes || []).slice(0, 12)" :key="r.date"
                  ><th>{{ r.date }}</th
                  ><td>{{ yi(r.subscriptions) }}</td
                  ><td>{{ yi(r.redemptions) }}</td
                  ><td>{{ yi(r.shares) }}</td
                  ><td>{{ yi(r.navYuan) }}</td></tr
                ></tbody
              ></table
            ></div
          >
          <p class="definition"
            >仅展示该份额代码的来源值，不把其他份额遗漏值补零，也不把份额变化当作资金金额。</p
          >
          <h4>本期股票明细</h4>
          <div class="table-scroll" tabindex="0" role="region" aria-label="基金股票明细"
            ><table
              ><thead
                ><tr
                  ><th>股票</th><th>占净值</th><th>市值 / 亿元</th><th>股数 / 万股</th
                  ><th>股数环比</th><th>市值环比</th></tr
                ></thead
              ><tbody
                ><tr v-for="row in holding?.rows || []" :key="`${row.market}:${row.code}`"
                  ><th
                    >{{ row.name }}<small>{{ row.market }} {{ row.code }}</small></th
                  ><td>{{ fmt(row.weightPct, '%') }}</td
                  ><td>{{ yi(row.valueYuan) }}</td
                  ><td>{{ scaled(row.shares, 10000) }}</td
                  ><td>{{
                    row.comparison === 'newly_disclosed'
                      ? '本期披露 / 前期未披露'
                      : signed(row.shareChangePct, '%')
                  }}</td
                  ><td>{{ signed(row.valueChangePct, '%') }}</td></tr
                ><tr v-if="!holding?.rows.length"
                  ><td colspan="6">本期未取得股票明细，不能据此认定空仓</td></tr
                ></tbody
              ></table
            ></div
          >
          <p class="definition"
            >股数为未调整的披露原值。前期未披露不等于新买入，退出重仓名单不等于清仓；市值变化同时受到价格与持股数量影响。</p
          >
        </template>
      </section>
      <details class="method"
        ><summary>统计口径与披露范围</summary
        ><p
          >样本来自当前公开基金目录，包含普通股票型、偏股混合与灵活配置，剔除指数、QDII、债券及FOF；当前分类不代表历史分类，存续目录回看存在幸存者偏差。同名A/C等份额归并不是全市场官方组合映射。</p
        ><p
          >行业配置按同日组合净资产加权，占净资产而非股票资产。行业表合计须与股票仓位相符后才参与汇总；缺少同日可核验基准时不计算超低配。缺值保持为空。</p
        ><p
          >季度对比统一取各期前十大股票，完整中报、年报持仓保留在单基金详情。数据为报告期末截面，不能代表公告日或今日仓位。第三方整理数据尚未逐份与基金公司原报告全量核验。</p
        ></details
      >
    </template>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
  import {
    readFundOverview,
    readFundDetail,
    type FundOverview,
    type FundDetail,
    type FundAllocation,
  } from '@/api/mutualFunds';
  import VibeTimeChart, { type Series } from './VibeTimeChart.vue';

  const props = defineProps<{ refreshKey: number }>();
  const emit = defineEmits<{ ready: [] }>();
  const overview = shallowRef<FundOverview>();
  const detail = shallowRef<FundDetail>();
  const loading = ref(false),
    error = ref(''),
    detailLoading = ref(false),
    detailError = ref(false);
  const selectedPeriod = ref(''),
    selectedCode = ref(''),
    detailPeriod = ref('');
  const fundSearch = ref(''),
    stockSearch = ref(''),
    industryMarket = ref('CN'),
    stockLimit = ref(50),
    fundLimit = ref(150);
  const detailHost = ref<HTMLElement>();
  let overviewController: AbortController | undefined,
    detailController: AbortController | undefined;
  let active = true;
  const num = (v: unknown): number | null =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const fmt = (v: unknown, unit = '') =>
    num(v) == null
      ? '—'
      : `${num(v)!.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}${unit}`;
  const signed = (v: unknown, unit = '') =>
    num(v) == null
      ? '—'
      : Math.abs(num(v)!) < 0.005
      ? fmt(0, unit)
      : `${num(v)! > 0 ? '+' : ''}${fmt(v, unit)}`;
  const scaled = (v: unknown, scale: number) => (num(v) == null ? '—' : fmt(num(v)! / scale));
  const yi = (v: unknown) => scaled(v, 100000000);
  const time = (v?: string) =>
    v ? new Date(v).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '—';
  function series(rows: FundAllocation[]): Series[] {
    return [
      {
        name: '股票占净比',
        type: 'line',
        color: '#2864ec',
        values: rows.map((r) => num(r.stockPct)),
        unit: '%',
      },
      {
        name: '现金占净比',
        type: 'line',
        color: '#bf8b39',
        values: rows.map((r) => num(r.cashPct)),
        unit: '%',
      },
    ];
  }
  const overviewSeries = computed(() => series(overview.value?.history || []));
  const detailHistory = computed(() =>
    [...(detail.value?.data.allocations || [])].sort((a, b) => a.date.localeCompare(b.date)),
  );
  const detailSeries = computed(() => series(detailHistory.value));
  const industryRows = computed(() =>
    (overview.value?.industries || []).filter((r) => r.market === industryMarket.value),
  );
  const filteredStocks = computed(() =>
    (overview.value?.stocks || []).filter((r) =>
      `${r.name} ${r.code}`.toLowerCase().includes(stockSearch.value.trim().toLowerCase()),
    ),
  );
  const stocks = computed(() => filteredStocks.value.slice(0, stockLimit.value));
  const filteredFunds = computed(() =>
    (overview.value?.funds || []).filter((r) =>
      `${r.name} ${r.code} ${r.manager || ''} ${r.classes.map((c) => c.code).join(' ')}`
        .toLowerCase()
        .includes(fundSearch.value.trim().toLowerCase()),
    ),
  );
  const funds = computed(() => filteredFunds.value.slice(0, fundLimit.value));
  const detailDates = computed(() =>
    [
      ...new Set(
        [...(detail.value?.data.allocations || []), ...(detail.value?.data.holdings || [])].map(
          (r) => r.date,
        ),
      ),
    ]
      .sort()
      .reverse(),
  );
  const holding = computed(() =>
    detail.value?.data.holdings?.find((r) => r.date === detailPeriod.value),
  );
  const selectedReports = computed(
    () => detail.value?.data.reports?.filter((r) => r.date === detailPeriod.value) || [],
  );
  async function load() {
    overviewController?.abort();
    const controller = new AbortController();
    overviewController = controller;
    loading.value = true;
    error.value = '';
    try {
      const data = await readFundOverview(selectedPeriod.value || undefined, controller.signal);
      if (active && !controller.signal.aborted) {
        overview.value = data;
        selectedPeriod.value = data.date || data.expectedPeriod;
      }
    } catch {
      if (active && !controller.signal.aborted)
        error.value = '公募披露数据读取失败，已保留当前内容。';
    } finally {
      if (active && !controller.signal.aborted) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  async function selectFund(code: string) {
    detailController?.abort();
    const controller = new AbortController();
    detailController = controller;
    if (selectedCode.value !== code) detail.value = undefined;
    selectedCode.value = code;
    detailLoading.value = true;
    detailError.value = false;
    try {
      const data = await readFundDetail(code, controller.signal);
      if (!active || controller.signal.aborted) return;
      detail.value = data;
      detailPeriod.value = data.data.allocations?.some((r) => r.date === selectedPeriod.value)
        ? selectedPeriod.value
        : detailDates.value[0] || '';
      await nextTick();
      detailHost.value?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    } catch {
      if (active && !controller.signal.aborted) detailError.value = true;
    } finally {
      if (active && !controller.signal.aborted) detailLoading.value = false;
    }
  }
  watch(
    () => props.refreshKey,
    () => {
      void load();
      if (selectedCode.value) void selectFund(selectedCode.value);
    },
  );
  watch(stockSearch, () => {
    stockLimit.value = 50;
  });
  watch(fundSearch, () => {
    fundLimit.value = 150;
  });
  onMounted(load);
  onBeforeUnmount(() => {
    active = false;
    overviewController?.abort();
    detailController?.abort();
  });
</script>

<style scoped>
  .mutual-funds {
    min-width: 0;
    color: #26384f;
  }

  .heading,
  .section-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    gap: 16px;
  }

  h2 {
    margin: 0 0 6px;
    font-size: 22px;
  }

  h3 {
    margin: 0;
    font-size: 16px;
  }

  h4 {
    margin-top: 24px;
  }

  p {
    line-height: 1.7;
  }

  .heading p,
  .section-heading p {
    margin: 4px 0;
    color: #738196;
    font-size: 12px;
  }

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }

  select,
  input {
    min-width: 0;
    max-width: 100%;
    padding: 7px 10px;
    border: 1px solid #dce4ef;
    border-radius: 6px;
    background: white;
    color: #26384f;
  }

  .source,
  .definition,
  .method {
    color: #6b798b;
    font-size: 12px;
  }

  .notice {
    padding: 10px 14px;
    border-left: 3px solid #d8a348;
    background: #fff8eb;
    color: #80602c;
    font-size: 12px;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 18px 0;
  }

  .metrics article,
  .card {
    min-width: 0;
    padding: 20px;
    border: 1px solid #e0e7ef;
    border-radius: 10px;
    background: white;
  }

  .metrics span,
  .metrics small {
    display: block;
    color: #738196;
    font-size: 11px;
  }

  .metrics strong {
    display: block;
    margin: 10px 0;
    font-size: 24px;
    font-variant-numeric: tabular-nums;
  }

  .card {
    margin-bottom: 18px;
  }

  .table-scroll {
    max-width: 100%;
    overflow: auto;
  }

  .fund-list {
    max-height: 430px;
  }

  .detail .table-scroll {
    max-height: 520px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 11px 12px;
    border-bottom: 1px solid #edf1f6;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  th:first-child {
    text-align: left;
  }

  thead th {
    position: sticky;
    top: 0;
    background: #f7f9fc;
    color: #768399;
    font-weight: 500;
  }

  tbody th {
    font-weight: 500;
  }

  small {
    display: block;
    margin-top: 4px;
    color: #8c98a8;
    font-size: 10px;
    font-weight: 400;
  }

  .bar {
    display: inline-block;
    height: 6px;
    margin-right: 8px;
    border-radius: 2px;
    background: #6c99e8;
  }

  button {
    padding: 0;
    border: 0;
    background: transparent;
    color: #2864b9;
    text-align: left;
    cursor: pointer;
  }

  .more {
    margin-top: 14px;
  }

  .selected {
    background: #f1f6ff;
  }

  .report-links {
    display: grid;
    margin: 12px 0;
    font-size: 12px;
    gap: 6px;
  }

  .report-links a {
    color: #2864b9;
    overflow-wrap: anywhere;
  }

  .detail {
    scroll-margin-top: 20px;
  }

  .method {
    padding: 12px 4px;
  }

  summary {
    cursor: pointer;
  }

  :is(button, a, select, input, .table-scroll):focus-visible {
    outline: 2px solid #2864ec;
    outline-offset: 3px;
  }

  @media (max-width: 1000px) {
    .metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 560px) {
    .card,
    .metrics article {
      padding: 12px;
    }

    .metrics strong {
      font-size: 20px;
    }

    .section-heading label {
      width: 100%;
    }

    input {
      flex: 1;
    }
  }
</style>
