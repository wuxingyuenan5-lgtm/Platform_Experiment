<template>
  <section class="theme-panorama" aria-label="主题ETF份额观察">
    <header><h2>主题ETF份额排行</h2><button :disabled="loading" @click="load">刷新</button></header>
    <p v-if="loading" role="status">正在读取主题排行…</p>
    <p v-if="error" role="alert">主题份额读取失败，请重试。</p>
    <template v-if="data">
      <div class="rankings">
        <article v-for="item in rankWindows" :key="`${item.days}:${item.direction}`">
          <h3>近{{ item.days }}个交易日份额{{ item.direction === 1 ? '增加' : '减少' }} TOP 5</h3>
          <p
            >{{ (item.days === 5 ? data.start : data.start20) || '基准日缺失' }} —
            {{ data.date || '—' }}</p
          >
          <table
            ><thead
              ><tr><th>主题</th><th>变动（亿份）</th><th>变动比例</th></tr></thead
            ><tbody>
              <tr v-for="fund in ranking(item.days, item.direction)" :key="fund.code">
                <td
                  ><button @click="selectedTheme = fund.code">{{ fund.name }}</button></td
                >
                <td :class="item.direction > 0 ? 'positive' : 'negative'">{{
                  format(item.days === 5 ? fund.delta : fund.delta20, true)
                }}</td>
                <td :class="item.direction > 0 ? 'positive' : 'negative'"
                  >{{ format(item.days === 5 ? fund.changePct : fund.change20Pct, true) }}%</td
                >
              </tr>
              <tr v-if="!ranking(item.days, item.direction).length"
                ><td colspan="3">暂无同区间有效样本</td></tr
              >
            </tbody></table
          >
        </article>
      </div>
      <p class="definition"
        >{{ data.source }} ·
        份额变化可能包含折算，不等同于净流入；各主题按同一交易日端点比较，缺失成员不计零。</p
      >
    </template>
  </section>
  <section v-if="data" class="theme-analysis" aria-label="主题份额与基金分析">
    <header class="analysis-heading"
      ><h2>主题份额与基金走势</h2>
      <div class="controls">
        <label
          >主题
          <select v-model="selectedTheme" aria-label="主题份额分类"
            ><option value="all">全部主题对比</option
            ><option v-for="theme in data.themes" :key="theme.code" :value="theme.code">{{
              theme.name
            }}</option></select
          ></label
        >
        <label
          >ETF
          <select v-model="selectedFund" aria-label="主题内ETF"
            ><option value="">主题合计</option
            ><option v-for="fund in visibleFunds" :key="fund.code" :value="fund.code"
              >{{ fund.name }} · {{ fund.code }}</option
            ></select
          ></label
        >
        <label v-if="!selectedFund"
          >指标
          <select v-model="metric" aria-label="主题份额指标"
            ><option value="units">份额（亿份）</option
            ><option value="indexed">份额走势（首日=100）</option></select
          ></label
        >
      </div>
    </header>
    <p v-if="historyLoading" role="status">正在读取主题历史…</p>
    <p v-if="historyError" role="alert"
      >主题历史读取失败 <button @click="loadHistory(true)">重试</button></p
    >
    <div v-if="currentTheme && !selectedFund" class="theme-metrics">
      <article
        ><span>最新份额</span
        ><strong
          >{{ format(currentTheme.series.at(-1)?.units) }}<small>亿份</small></strong
        ></article
      >
      <article
        ><span>近5交易日份额变动</span
        ><strong>{{ format(currentTheme.delta, true) }}<small>亿份</small></strong></article
      >
      <article
        ><span>近20交易日份额变动</span
        ><strong>{{ format(currentTheme.delta20, true) }}<small>亿份</small></strong></article
      >
    </div>
    <ThemeEtfChart
      v-if="history && !selectedFund"
      :funds="history.themes"
      :range="range"
      :indexed="metric === 'indexed'"
      @range="range = $event"
    />
    <EtfMemberAnalysis
      v-if="selectedFund"
      :code="selectedFund"
      :range="range"
      :refresh-key="refreshKey"
      @range="range = $event"
    />
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
  import ThemeEtfChart from './ThemeEtfChart.vue';
  import EtfMemberAnalysis from './EtfMemberAnalysis.vue';
  import { useResearchSnapshots } from '../../composables/researchWorkspace';
  import type { ThemeFund, ThemePanorama } from './themeEtfAnalysis';

  const props = defineProps<{ refreshKey?: number }>();
  defineEmits<{ ready: [] }>();
  const data = shallowRef<ThemePanorama>();
  const loading = ref(false),
    error = ref(false),
    selectedTheme = ref('all');
  const selectedFund = ref(''),
    metric = ref('units'),
    range = ref(1095);
  const history = shallowRef<ThemePanorama>();
  const currentTheme = computed(() =>
    history.value?.themes.length === 1 ? history.value.themes[0] : undefined,
  );
  const historyLoading = ref(false),
    historyError = ref(false);
  const visibleFunds = computed(() =>
    (data.value?.funds || []).filter(
      (f) => selectedTheme.value === 'all' || f.theme === selectedTheme.value,
    ),
  );
  const snapshots = useResearchSnapshots();
  let historyController: AbortController | undefined;
  let active = true,
    loadedHistoryKey = '',
    loadedTheme = '';
  async function loadHistory(force = false) {
    if (!active) return;
    historyController?.abort();
    const request = (historyController = new AbortController());
    const requestedTheme = selectedTheme.value;
    const key = `theme-chart:${selectedTheme.value}:${range.value}`;
    historyLoading.value = true;
    historyError.value = false;
    if (loadedTheme !== requestedTheme) history.value = undefined;
    try {
      const result =
        (!force && snapshots.get<ThemePanorama>(key)) ||
        (await researchRequest<ThemePanorama>({
          method: 'GET',
          url: `/research/a-share/theme-etfs?theme=${encodeURIComponent(
            selectedTheme.value,
          )}&days=${range.value}`,
          signal: request.signal,
        }));
      if (!request.signal.aborted) {
        history.value = result;
        loadedTheme = requestedTheme;
        snapshots.set(key, result);
        loadedHistoryKey = key;
      }
    } catch {
      if (!request.signal.aborted) historyError.value = true;
    } finally {
      if (historyController === request) historyLoading.value = false;
    }
  }
  watch(selectedTheme, () => {
    selectedFund.value = '';
  });
  watch([selectedTheme, range], () => {
    if (data.value) void loadHistory();
  });
  const rankWindows = [5, 20].flatMap((days) => [1, -1].map((direction) => ({ days, direction })));
  function ranking(days: number, direction: number): ThemeFund[] {
    const value = (f: ThemeFund) => (days === 5 ? f.delta : f.delta20);
    return (data.value?.themes || [])
      .filter((f) => value(f) != null && Number(value(f)) * direction > 0)
      .sort((a, b) => (Number(value(b)) - Number(value(a))) * direction)
      .slice(0, 5);
  }
  const format = (v: string | null | undefined, sign = false) =>
    v == null
      ? '—'
      : `${sign && Number(v) > 0 ? '+' : ''}${Number(v).toLocaleString('zh-CN', {
          maximumFractionDigits: 2,
        })}`;
  let controller: AbortController | undefined;
  async function load() {
    if (!active) return;
    controller?.abort();
    const request = (controller = new AbortController());
    loading.value = true;
    error.value = false;
    try {
      const result = await researchRequest<ThemePanorama>({
        method: 'GET',
        url: '/research/a-share/theme-etfs?include_series=false',
        signal: request.signal,
      });
      if (!request.signal.aborted) {
        data.value = result;
        void loadHistory(true);
      }
    } catch {
      if (!request.signal.aborted) error.value = true;
    } finally {
      if (controller === request) loading.value = false;
    }
  }
  watch(() => props.refreshKey, load, { immediate: true });
  onDeactivated(() => {
    active = false;
    historyController?.abort();
    historyLoading.value = false;
    controller?.abort();
    loading.value = false;
  });
  onActivated(() => {
    active = true;
    if (
      data.value &&
      loadedHistoryKey !== `theme-chart:${selectedTheme.value}:${range.value}` &&
      !historyLoading.value
    )
      void loadHistory();
    if (!data.value && !loading.value) void load();
  });
  onBeforeUnmount(() => {
    controller?.abort();
    historyController?.abort();
  });
</script>
<style scoped>
  .theme-panorama {
    margin-bottom: 24px;
    padding: 20px;
    border: 1px solid #dce5ef;
    border-radius: 12px;
    background: #fff;
    color: #233950;
  }

  header,
  .controls,
  nav {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }

  header {
    justify-content: space-between;
  }

  h2 {
    margin: 0;
    font-size: 22px;
  }

  h3 {
    padding-left: 10px;
    border-left: 3px solid #739ac8;
    font-size: 15px;
  }

  p {
    margin: 8px 0;
    color: #66788b;
    font-size: 12px;
  }

  .definition {
    line-height: 1.7;
  }

  .controls {
    margin-top: 20px;
  }

  button,
  select {
    padding: 6px 10px;
    border: 1px solid #dce5ef;
    border-radius: 6px;
    background: #fff;
    color: inherit;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #8eafe0;
    background: #edf4ff;
    color: #2459a0;
  }

  .funds {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  small {
    display: block;
    color: #7c8999;
    font-size: 11px;
  }

  .rankings {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 24px;
    margin-top: 24px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 12px 5px;
    border-bottom: 1px solid #eef1f5;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  th {
    background: #f6f8fb;
    color: #6c7c8f;
    font-weight: 500;
  }

  td button {
    padding: 0;
    border: 0;
  }

  .positive {
    color: #bd5656;
  }

  .negative {
    color: #278b76;
  }

  @media (max-width: 1100px) {
    .rankings {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .theme-panorama {
      padding: 12px;
    }
  }
</style>

<style scoped>
  @media (max-width: 640px) {
    .rankings {
      grid-template-columns: 1fr;
    }
  }
</style>

<style scoped>
  .theme-analysis {
    min-width: 0;
    margin: 18px 0 28px;
  }

  .analysis-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .analysis-heading h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }

  .controls {
    margin-top: 0;
  }

  .theme-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 14px;
  }

  .theme-metrics article {
    padding: 14px;
    border: 1px solid #d7e3ee;
    border-radius: 12px;
    background: #fff;
  }

  .theme-metrics span {
    color: #65809b;
    font-size: 12px;
  }

  .theme-metrics strong {
    display: block;
    font-size: 22px;
    font-variant-numeric: tabular-nums;
  }

  .theme-metrics small {
    display: inline;
    margin-left: 6px;
    font-size: 12px;
    font-weight: 400;
  }

  @media (max-width: 640px) {
    .theme-metrics {
      grid-template-columns: 1fr;
    }
  }
</style>
