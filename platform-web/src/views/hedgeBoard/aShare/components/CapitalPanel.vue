<template>
  <section class="capital-panel" aria-label="A股资金面">
    <div v-if="data" class="metric-strip">
      <article v-for="card in cards" :key="card.label">
        <span>{{ card.label }}</span
        ><div class="metric-value-row"
          ><strong
            >{{ fmt(card.value) }} <small>{{ card.unit }}</small></strong
          ><span v-if="card.comparison" class="metric-comparison">{{ card.comparison }}</span></div
        >
        <span>{{ card.date || '暂无数据' }} · {{ card.state }}</span>
      </article>
    </div>
    <div class="capital-navigation section-tabs">
      <nav class="tabs" aria-label="资金面分类">
        <button
          v-for="item in tabs"
          :key="item.key"
          type="button"
          :aria-pressed="tab === item.key"
          @click="tab = item.key"
          >{{ item.label }}</button
        >
      </nav>
      <nav v-if="tab === 'etf'" class="etf-tabs" aria-label="ETF研究分类">
        <button
          v-for="item in etfTabs"
          :key="item.id"
          type="button"
          :aria-pressed="etfTab === item.id"
          @click="etfTab = item.id"
          >{{ item.label }}</button
        >
      </nav>
    </div>
    <h2 v-if="tab === 'overview'" class="overview-title">资金面总览</h2>
    <KeepAlive>
      <EtfTrackingPanel
        v-if="tab === 'overview' || tab === 'etf'"
        :tab="tab === 'overview' ? 'overview' : etfTab"
        :flow-only="tab === 'overview'"
        :refresh-key="refreshKey"
        @ready="tab === 'etf' && emit('ready')"
      />
    </KeepAlive>
    <KeepAlive>
      <DomesticFinancingPanel
        v-if="tab === 'overview' || tab === 'margin'"
        mode="margin"
        :hide-margin-source="tab === 'overview'"
        :refresh-key="refreshKey"
        @ready="tab === 'margin' && emit('ready')"
      />
    </KeepAlive>
    <CapitalHandbookPanel
      v-if="data && ['overview', 'funds', 'margin', 'others'].includes(tab)"
      :data="data"
      :mode="handbookMode"
    />
    <KeepAlive>
      <MutualFundPanel
        v-if="tab === 'funds'"
        :refresh-key="refreshKey ?? 0"
        @ready="emit('ready')"
      />
    </KeepAlive>
    <p v-if="loading && !isIndependentTab" role="status">正在读取资金面…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <CapitalHandbookPanel v-if="data && tab === 'funds'" :data="data" mode="fund-research" />
    <CapitalHandbookDemo v-if="tab === 'funds'" demo-id="fund-sector-allocation" />
    <CapitalHandbookDemo
      v-if="tab === 'funds' && !data?.handbook?.fundStockReports?.length"
      demo-id="fund-heavy-a"
    />
  </section>
</template>

<script setup lang="ts">
  import { computed, defineAsyncComponent, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import {
    getAShareCapital,
    type CapitalDashboard,
    type CapitalSource,
  } from '@/api/platform/aShareCapital';
  import CapitalHandbookPanel from './CapitalHandbookPanel.vue';

  const DomesticFinancingPanel = defineAsyncComponent(() => import('./DomesticFinancingPanel.vue'));
  const EtfTrackingPanel = defineAsyncComponent(() => import('./EtfTrackingPanel.vue'));
  const MutualFundPanel = defineAsyncComponent(() => import('./MutualFundPanel.vue'));
  const CapitalHandbookDemo = defineAsyncComponent(() => import('./CapitalHandbookDemo.vue'));

  const props = defineProps<{ refreshKey?: number }>();
  const emit = defineEmits<{ ready: [] }>();
  const data = shallowRef<CapitalDashboard>();
  const loading = ref(false),
    error = ref('');
  const route = useRoute(),
    router = useRouter();
  const selectedTab = ref('overview');
  const handbookMode = computed(() =>
    tab.value === 'funds'
      ? 'funds'
      : tab.value === 'margin'
      ? 'margin'
      : tab.value === 'others'
      ? 'others'
      : 'overview',
  );
  const etfTab = ref<'overview' | 'intraday' | 'single'>('overview');
  const etfTabs = [
    { id: 'overview', label: 'ETF总览' },
    { id: 'intraday', label: '盘中监测' },
    { id: 'single', label: '主题ETF' },
  ] as const;
  const tab = computed({
    get: () => selectedTab.value,
    set: (section: string) => {
      selectedTab.value = section;
      void router.replace({ query: { ...route.query, section } });
    },
  });
  const isIndependentTab = computed(
    () => tab.value === 'margin' || tab.value === 'funds' || tab.value === 'etf',
  );
  let abort: AbortController | undefined;
  async function load() {
    abort?.abort();
    const current = (abort = new AbortController());
    loading.value = true;
    error.value = '';
    try {
      const result = await getAShareCapital(current.signal);
      if (!current.signal.aborted) data.value = result;
    } catch {
      if (!current.signal.aborted) error.value = '资金面读取失败，请重试';
    } finally {
      if (!current.signal.aborted) {
        loading.value = false;
        if (!isIndependentTab.value) emit('ready');
      }
    }
  }
  watch(() => props.refreshKey, load, { immediate: true });
  onBeforeUnmount(() => abort?.abort());
  const tabs = [
    { key: 'overview', label: '总览' },
    { key: 'etf', label: 'ETF跟踪' },
    { key: 'margin', label: '两融' },
    { key: 'funds', label: '公募' },
    { key: 'others', label: '其他资金' },
  ];
  watch(
    () => [route.query.view, route.query.section],
    ([view, section]) => {
      if (view === 'financing') selectedTab.value = 'margin';
      else if (view === 'funds') selectedTab.value = 'funds';
      else if (view === 'capital' && section !== undefined)
        selectedTab.value = tabs.some((item) => item.key === section)
          ? String(section)
          : 'overview';
    },
    { immediate: true },
  );
  const fmt = (value: unknown) =>
    value == null || value === '' || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toLocaleString('zh-CN', {
          maximumFractionDigits: Math.abs(Number(value)) < 0.01 ? 6 : 2,
        });
  const sourceState = (s: CapitalSource) =>
    s.status === 'error'
      ? s.rows.length
        ? '更新失败 · 保留历史'
        : '暂不可用'
      : s.isStale
      ? '待更新'
      : s.status === 'ready'
      ? '已采集'
      : '暂无数据';
  const etfState = computed(() => {
    const etf = data.value?.broadEtf;
    if (etf?.flow1Yi == null || !etf.date) return '暂无数据';
    if (etf.status !== 'ready') return '更新异常 · 保留历史';
    if (etf.basketCount && (etf.coveredCount ?? 0) < etf.basketCount)
      return `部分覆盖 ${etf.coveredCount ?? 0}/${etf.basketCount}只`;
    const age = Date.parse(data.value!.asOf) - Date.parse(etf.date);
    return age > 4 * 86400000 ? '待更新' : '宽基估算';
  });
  const cards = computed(() => {
    const d = data.value!;
    const margin = d.macro.cn_margin_financing_balance,
      rate = d.macro.cn_dr007;
    const month = d.sources.issuance.rows
      .filter((r) => r.date.slice(0, 7) < d.asOf.slice(0, 7))
      .at(-1);
    return [
      {
        label: '融资余额',
        comparison: '近5个交易日变化 ' + fmt(d.comparisons?.marginChange5d) + ' 亿元',
        value: margin?.latestValue,
        unit: '亿元',
        date: margin?.observationDate,
        state: margin?.isStale || margin?.status !== 'ready' ? '待更新' : '已披露',
      },
      {
        label: `宽基ETF${
          d.broadEtf?.basketCount ? `（${d.broadEtf.basketCount}只）` : ''
        } · 单日申赎估算`,
        comparison: '同样本5日累计 ' + fmt(d.broadEtf?.flow5Yi) + ' 亿元',
        value: d.broadEtf?.flow1Yi,
        unit: '亿元',
        date: d.broadEtf?.date,
        state: etfState.value,
      },
      {
        label: '最近完整月 · 股票发行规模',
        value: month?.total,
        unit: '亿元',
        date: month?.date.slice(0, 7),
        state: sourceState(d.sources.issuance),
      },
      {
        label: 'DR007',
        comparison: '较同日7天逆回购 ' + fmt(d.comparisons?.rateSpreadBp) + ' bp',
        value: rate?.latestValue,
        unit: '%',
        date: rate?.observationDate,
        state: rate?.isStale || rate?.status !== 'ready' ? '待更新' : '已披露',
      },
    ];
  });
</script>

<style scoped>
  .capital-panel {
    min-width: 0;
    color: var(--strategy-text-2);
  }

  .overview-title {
    margin: 22px 0 16px;
    color: var(--strategy-text-1);
    font-size: 20px;
  }

  .section-heading,
  .table-controls,
  .pagination {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h3 {
    color: var(--strategy-text-1);
    font-size: 16px;
  }

  p {
    margin: 8px 0 14px;
    line-height: 1.7;
  }

  a {
    color: var(--strategy-accent);
  }

  .metric-strip {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin: 16px 0;
    overflow: hidden;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
  }

  .metric-strip article {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 16px;
    border-right: 1px solid var(--strategy-border);
  }

  .metric-strip article:last-child {
    border-right: 0;
  }

  .metric-strip span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .metric-strip strong {
    color: var(--strategy-text-1);
    font-size: 24px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .metric-value-row {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px 12px;
  }

  .metric-comparison {
    line-height: 1.4;
  }

  .metric-strip small {
    font-size: 12px;
    font-weight: 400;
  }

  .tabs,
  .etf-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .capital-navigation {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    margin: 18px 0;
    gap: 12px;
  }

  .etf-tabs {
    margin-left: auto;
  }

  button,
  input,
  select {
    padding: 7px 11px;
    border: 1px solid var(--strategy-border);
    border-radius: 7px;
    background: var(--strategy-surface);
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: var(--strategy-accent);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent);
  }

  button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  button:focus-visible,
  input:focus-visible,
  select:focus-visible,
  a:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 2px;
  }

  .chart-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
  }

  .section-tabs {
    padding: 6px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  .section-tabs button {
    border-color: transparent;
  }

  .chart-grid > div {
    min-width: 0;
  }

  .source,
  .definition {
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.7;
  }

  .source {
    overflow-wrap: anywhere;
  }

  .section-heading {
    margin-top: 22px;
    padding-top: 10px;
    border-top: 1px solid var(--strategy-border);
  }

  .table-controls {
    justify-content: flex-start;
    margin: 16px 0 10px;
    font-size: 12px;
  }

  .table-scroll {
    overflow-x: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    text-align: left;
  }

  th,
  td {
    min-width: 85px;
    padding: 11px 12px;
    border-bottom: 1px solid var(--strategy-border);
  }

  th {
    background: var(--strategy-surface-2);
    font-weight: 500;
  }

  td {
    max-width: 260px;
    overflow-wrap: anywhere;
  }

  .number {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .pagination {
    justify-content: flex-end;
    margin-top: 14px;
    font-size: 12px;
  }

  .empty {
    padding: 20px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  .references {
    padding-left: 20px;
  }

  .references li {
    padding: 8px 0;
  }

  .references p {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  @media (max-width: 1200px) {
    .chart-grid {
      grid-template-columns: minmax(0, 1fr);
    }

    .metric-strip {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 600px) {
    .metric-strip article {
      padding: 12px;
    }

    .metric-strip article:nth-child(2n) {
      border-right: 0;
    }

    .metric-strip article:nth-child(-n + 2) {
      border-bottom: 1px solid var(--strategy-border);
    }

    .metric-strip strong {
      font-size: 20px;
    }

    .table-controls input {
      width: 170px;
    }
  }
</style>
