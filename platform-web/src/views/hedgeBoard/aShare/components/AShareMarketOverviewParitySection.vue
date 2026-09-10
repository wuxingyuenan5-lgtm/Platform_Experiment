<template>
  <section id="a-share-market-overview" class="overview-card">
    <header class="overview-header">
      <div><p class="eyebrow">MARKET OVERVIEW</p><h2>A股市场总览</h2></div>
      <span v-if="updatedAt" class="updated">更新于 {{ formatDate(updatedAt) }}</span>
    </header>
    <div class="overview-grid">
      <article class="metric-panel">
        <div class="panel-title"
          ><h3>市场情绪</h3
          ><ResearchSourceState v-if="dashboard?.breadth" :meta="dashboard.breadth.meta"
        /></div>
        <div v-if="breadth" class="metric-grid"
          ><div v-for="item in breadthMetrics" :key="item.label" class="metric-cell"
            ><span>{{ item.label }}</span
            ><strong :class="item.tone">{{ item.value }}</strong
            ><small>{{ item.note }}</small></div
          ></div
        >
        <div v-if="latestHistory || turnoverData" class="overview-meta-grid">
          <div
            ><span>全A成交额</span
            ><strong>{{ formatHundredMillion(latestHistory?.total_amount_100m) }}</strong></div
          >
          <button
            type="button"
            class="meta-action"
            :disabled="hotStockCount == null"
            @click="hotMatrixOpen = true"
            ><span>百亿成交股</span
            ><strong>{{ hotStockCount == null ? '—' : `${hotStockCount}只` }}</strong></button
          >
          <div
            ><span>市场宽度</span
            ><strong>{{ formatPct(latestHistory?.market_breadth, true) }}</strong></div
          >
        </div>
        <div v-if="!breadth" class="empty">暂无市场情绪数据</div>
      </article>
      <article class="metric-panel">
        <div class="panel-title"
          ><h3>短线情绪</h3
          ><ResearchSourceState v-if="dashboard?.emotion" :meta="dashboard.emotion.meta"
        /></div>
        <div v-if="emotion" class="metric-grid"
          ><div v-for="item in emotionMetrics" :key="item.label" class="metric-cell"
            ><span>{{ item.label }}</span
            ><strong :class="item.tone">{{ item.value }}</strong
            ><small>{{ item.note }}</small></div
          ></div
        >
        <div v-else class="empty">暂无短线情绪数据</div>
        <div v-if="emotion" class="emotion-detail">
          <button
            type="button"
            class="emotion-subpanel ladder-trigger"
            :disabled="!ladderRows.length"
            @click="ladderOpen = true"
          >
            <span class="subpanel-heading"
              ><strong>连板梯队</strong
              ><span>{{
                ladderRows.length ? '点击查看连板股明细' : '暂无二板及以上个股'
              }}</span></span
            >
            <span v-if="ladderRows.length" class="ladder-list">
              <span v-for="row in ladderRows" :key="row.boardCount" class="ladder-row"
                ><span>{{ row.boardCount }}</span
                ><i class="ladder-track"
                  ><b :style="{ width: `${ladderWidth(row.stockCount)}%` }"></b></i
                ><strong>{{ row.stockCount }}</strong></span
              >
            </span>
          </button>
        </div>
      </article>
    </div>
    <VibeTrendCharts
      v-if="allHistoryRows.length > 1"
      :rows="allHistoryRows"
      :crowding-rows="dashboard?.crowding?.data?.history"
      :innovation-rows="dashboard?.crowding?.data?.innovationHistory"
    />

    <div class="overview-grid">
      <article class="panel">
        <div class="panel-title"
          ><div><h3>板块资金趋势榜</h3></div
          ><ResearchSourceState :meta="sectorFlowMeta"
        /></div>
        <button
          v-if="sectorRows.length > 7"
          type="button"
          class="link-button"
          @click="sectorsExpanded = !sectorsExpanded"
          >{{ sectorsExpanded ? '收起' : '查看完整' }} →</button
        >
        <div v-if="sectorRows.length" class="table-shell"
          ><table
            ><thead
              ><tr
                ><th class="is-left">行业</th><th>涨跌%</th><th>今日主力净流入</th><th>家数</th></tr
              ></thead
            ><tbody
              ><tr v-for="row in visibleSectorRows" :key="row.name"
                ><td class="is-left"
                  ><strong>{{ row.name }}</strong></td
                ><td :class="tone(row.pct)">{{ formatPct(row.pct) }}</td
                ><td :class="tone(row.net)">{{ formatYi(row.netYi) }}</td
                ><td>{{ row.firms ?? '—' }}</td></tr
              ></tbody
            ></table
          ></div
        ><div v-else class="empty">暂无板块资金数据</div>
      </article>
      <article class="panel"
        ><div class="panel-title"
          ><div><h3>资金轮动</h3></div></div
        ><div v-if="rotationRows.length" class="rotation-grid"
          ><div class="rotation-column"
            ><h4 class="is-positive">↑ 流入 Top</h4
            ><div v-for="row in rotationInflow" :key="`in-${row.name}`" class="rotation-row"
              ><span>{{ row.name }}</span
              ><b :class="tone(row.pct)">{{ formatPct(row.pct) }}</b
              ><em class="is-positive">{{ formatYi(row.netYi) }}</em></div
            ><p v-if="!rotationInflow.length" class="empty-inline">暂无净流入数据</p></div
          ><div class="rotation-column"
            ><h4 class="is-negative">↓ 流出 Top</h4
            ><div v-for="row in rotationOutflow" :key="`out-${row.name}`" class="rotation-row"
              ><span>{{ row.name }}</span
              ><b :class="tone(row.pct)">{{ formatPct(row.pct) }}</b
              ><em class="is-negative">{{ formatYi(row.netYi) }}</em></div
            ><p v-if="!rotationOutflow.length" class="empty-inline">暂无净流出数据</p></div
          ></div
        ><div v-else class="empty">暂无资金轮动数据</div></article
      >
    </div>
    <article class="panel wide-panel"
      ><div class="panel-title"
        ><div><h3>全市场成交额榜</h3><ResearchSourceState :meta="turnoverMeta" /></div
        ><div class="turnover-actions"
          ><button
            v-for="n in [10, 20]"
            :key="n"
            type="button"
            :class="{ active: topN === n }"
            @click="topN = n as 10 | 20"
            >T{{ n }}</button
          ></div
        ></div
      ><div v-if="turnoverRows.length" class="table-shell"
        ><table
          ><thead
            ><tr
              ><th>#</th><th class="is-left">名称 / 代码</th><th>现价</th><th>涨跌%</th
              ><th>成交额</th><th>总市值</th><th>行业</th></tr
            ></thead
          ><tbody
            ><tr v-for="(row, index) in turnoverRows.slice(0, topN)" :key="row.securityCode"
              ><td>{{ index + 1 }}</td
              ><td class="is-left"
                ><button
                  type="button"
                  class="stock-name-button"
                  @click="emit('query', row.securityCode)"
                  >{{ row.securityName }}</button
                ><small>{{ row.securityCode }}</small></td
              ><td>{{ row.price ?? '—' }}</td
              ><td :class="tone(row.returnPct)">{{ formatPct(row.returnPct) }}</td
              ><td>{{ formatYi(row.turnoverYi) }}</td
              ><td>{{ formatYi(row.marketCapYi) }}</td
              ><td>{{ row.industry || '—' }}</td></tr
            ></tbody
          ></table
        ></div
      ><div v-else class="empty"
        >{{ turnoverError || '暂无成交额榜数据'
        }}<button
          type="button"
          class="link-button"
          :disabled="turnoverLoading"
          @click="loadLiveTurnover"
          >重试</button
        ></div
      ></article
    >
    <Modal
      v-model:open="hotMatrixOpen"
      title="百亿成交股"
      :footer="null"
      width="min(1000px, calc(100vw - 32px))"
      :get-container="false"
    >
      <article class="panel matrix-panel">
        <div class="panel-title"
          ><h3>百亿成交股 · 最近收盘明细</h3
          ><button type="button" class="modal-close" @click="hotMatrixOpen = false"
            >关闭</button
          ></div
        >
        <div class="hot-stock-summary" v-if="turnoverData">
          <strong>{{ hotStockCount == null ? '—' : `${hotStockCount}只` }}</strong>
          <span
            >成交额严格大于 100 亿元 ·
            {{ turnoverData.dailyObservedAt?.slice(0, 10) || '交易日待确认' }}</span
          >
        </div>
        <div
          v-if="highTurnoverRows.length"
          class="hot-stock-bars"
          aria-label="百亿成交股成交额对比图"
        >
          <button
            v-for="row in highTurnoverRows"
            :key="`bar-${row.securityCode}`"
            type="button"
            class="hot-stock-bar"
            @click="emit('query', row.securityCode)"
          >
            <span>{{ row.securityName }}</span
            ><i><b :style="{ width: `${hotStockBarWidth(row.turnoverYi)}%` }"></b></i
            ><strong>{{ formatYi(row.turnoverYi) }}</strong>
          </button>
        </div>
        <section v-if="turnoverData?.historyDates?.length" class="hot-history-panel">
          <div class="hot-history-head"
            ><div><h4>百亿成交 · 历史统计</h4><span>点击日期查看当日百亿成交股</span></div
            ><label
              >时间范围
              <select v-model="hotHistoryRange" aria-label="百亿成交历史时间范围"
                ><option :value="10">近10</option
                ><option :value="30">近30</option
                ><option value="all">全部</option></select
              ></label
            ></div
          >
          <div class="hot-history-dates"
            ><button
              v-for="{ date, index } in visibleHotDates"
              :key="date"
              type="button"
              :class="{ active: selectedHotDate === date }"
              @click="selectedHotDate = date"
              ><span>{{ date.slice(5) }}</span
              ><strong>{{ turnoverData.historyCounts?.[index] || 0 }}</strong></button
            ></div
          >
          <div class="table-shell hot-history-matrix"
            ><table
              ><thead
                ><tr
                  ><th class="is-left">行业</th
                  ><th v-for="{ date } in visibleHotDates" :key="date">{{ date.slice(5) }}</th
                  ><th>近90日累计</th></tr
                ></thead
              ><tbody
                ><tr v-for="row in turnoverData.historyIndustries" :key="row.industry"
                  ><td class="is-left"
                    ><strong>{{ row.industry }}</strong></td
                  ><td v-for="{ date, index } in visibleHotDates" :key="date">{{
                    row.counts[index] || ''
                  }}</td
                  ><td>{{ row.historyTotal }}</td></tr
                ></tbody
              ></table
            ></div
          >
          <div v-if="selectedHistoricalHotRows.length" class="hot-history-day"
            ><strong>{{ selectedHotDate }} · {{ selectedHistoricalHotRows.length }}只</strong
            ><button
              v-for="row in selectedHistoricalHotRows"
              :key="`${row.observedAt}-${row.securityCode}`"
              type="button"
              @click="emit('query', row.securityCode)"
              >{{ row.securityName }}
              <span>{{
                formatYi(row.turnoverYuan == null ? null : Number(row.turnoverYuan) / 1e8)
              }}</span></button
            ></div
          >
        </section>
      </article>
    </Modal>
    <Modal
      v-model:open="ladderOpen"
      title="连板股清单"
      :footer="null"
      width="min(900px, calc(100vw - 32px))"
      :get-container="false"
    >
      <article class="panel">
        <div class="panel-title"
          ><h3>连板股清单</h3
          ><button type="button" class="modal-close" @click="ladderOpen = false">关闭</button></div
        >
        <div class="table-shell">
          <table
            ><thead
              ><tr
                ><th class="is-left">名称 / 代码</th><th>连板</th><th>现价</th><th>涨跌%</th
                ><th class="is-right">成交额</th><th>流通市值</th><th>行业</th></tr
              ></thead
            >
            <tbody
              ><tr v-for="row in emotionLeaders" :key="row.code"
                ><td class="is-left"
                  ><strong>{{ row.name }}</strong
                  ><small>{{ row.code }}</small></td
                ><td>{{ row.boards }}板</td><td>{{ row.price ?? '—' }}</td
                ><td :class="tone(row.pct)">{{ formatPct(row.pct) }}</td
                ><td class="is-right">{{ formatYi(row.amountYi) }}</td
                ><td>{{ formatYi(row.floatCapYi) }}</td
                ><td>{{ row.industry || '—' }}</td></tr
              >
              <tr v-if="!emotionLeaders.length"
                ><td colspan="7" class="empty-cell">暂无二板及以上个股</td></tr
              ></tbody
            >
          </table>
        </div>
      </article>
    </Modal>
  </section>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
  import {
    getAShareLiveSectorFundFlow,
    getAShareLiveMarketTurnover,
    type AShareDashboardResponse,
    type AShareLiveSectorFundFlowResponse,
    type AShareMarketTurnoverResponse,
    type ResearchSourceMeta,
  } from '@/api/hedgeResearch';
  import { Modal } from 'ant-design-vue';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';
  import VibeTrendCharts from './VibeTrendCharts.vue';

  const props = defineProps<{ dashboard: AShareDashboardResponse | null; refreshKey?: number }>();
  const emit = defineEmits<{ (event: 'query', code: string): void }>();
  type EmotionLeader = {
    code: string;
    name: string;
    boards: number;
    price?: number;
    pct?: number;
    amountYi: number | null;
    floatCapYi: number | null;
    industry?: string;
  };
  type SectorRow = {
    name: string;
    pct: number | null;
    net: number | null;
    netYi: number | null;
    inflowYi: number | null;
    outflowYi: number | null;
    firms?: number | null;
  };
  type TurnoverRow = {
    securityCode: string;
    securityName: string;
    price?: number | string | null;
    returnPct?: number | string | null;
    turnoverYi: number | null;
    marketCapYi: number | null;
    industry?: string | null;
  };
  const sectorsExpanded = ref(false);
  const liveSectorFlow = shallowRef<AShareLiveSectorFundFlowResponse | null>(null);
  const turnoverData = shallowRef<AShareMarketTurnoverResponse | null>(null);
  const liveSectorFlowError = ref('');
  const liveSectorFlowLoading = ref(false);
  let liveTimer: number | undefined;
  let lastLiveLoad = 0;
  const turnoverLoading = ref(false);
  const turnoverError = ref('');
  const topN = ref<10 | 20>(10);
  const ladderOpen = ref(false);
  const hotMatrixOpen = ref(false);
  const selectedHotDate = ref('');
  const hotHistoryRange = ref<10 | 30 | 'all'>(10);
  const visibleHotDates = computed(() => {
    const dates = (turnoverData.value?.historyDates || [])
      .map((date, index) => ({ date, index }))
      .sort((a, b) => b.date.localeCompare(a.date));
    return hotHistoryRange.value === 'all' ? dates : dates.slice(0, hotHistoryRange.value);
  });
  watch(visibleHotDates, (dates) => {
    if (!dates.some(({ date }) => date === selectedHotDate.value))
      selectedHotDate.value = dates[0]?.date || '';
  });
  const allHistoryRows = computed(() =>
    (props.dashboard?.marketHistory || []).map((row) => ({
      date: row.observedAt,
      advance: row.up,
      decline: row.down,
      flat: row.flat,
      limit_up: row.limitUp,
      limit_down: row.limitDown,
      total_amount_100m: row.totalAmountYuan == null ? null : Number(row.totalAmountYuan) / 1e8,
      market_breadth: row.marketBreadthPct == null ? null : Number(row.marketBreadthPct) / 100,
    })),
  );
  const latestHistory = computed(() => allHistoryRows.value.at(-1) || null);
  const hotStockCount = computed(() => turnoverData.value?.highTurnoverCount ?? null);
  const updatedAt = computed(() => props.dashboard?.generatedAt || '');
  const breadth = computed(() => {
    return props.dashboard?.breadth.data || null;
  });
  const emotion = computed(() => {
    return props.dashboard?.emotion.data || null;
  });
  const emotionLeaders = computed<EmotionLeader[]>(() => {
    return (props.dashboard?.emotion.data?.leaders || []).map((r) => ({
      code: r.securityCode,
      name: r.securityName,
      boards: r.boardCount,
      amountYi: r.turnoverYuan == null ? null : Number(r.turnoverYuan) / 1e8,
      floatCapYi: null,
    }));
  });
  const ladderRows = computed(() => emotion.value?.ladder || []);
  const maxLadderCount = computed(() => Math.max(1, ...ladderRows.value.map((r) => r.stockCount)));
  function ladderWidth(c: number) {
    return Math.max(4, (c / maxLadderCount.value) * 100);
  }
  const sectorFlowMeta = computed<ResearchSourceMeta>(() => ({
    source: liveSectorFlow.value?.source || '板块资金流',
    fetchedAt: liveSectorFlow.value?.fetchedAt || '',
    status: liveSectorFlowLoading.value
      ? 'loading'
      : liveSectorFlowError.value
      ? liveSectorFlow.value
        ? 'stale'
        : 'error'
      : liveSectorFlow.value?.status || 'no_data',
    isStale: Boolean(
      liveSectorFlow.value?.isStale || (liveSectorFlowError.value && liveSectorFlow.value),
    ),
    message: liveSectorFlowError.value || liveSectorFlow.value?.message,
  }));
  const turnoverMeta = computed<ResearchSourceMeta>(() => ({
    source: turnoverData.value?.source || '成交额榜',
    fetchedAt: turnoverData.value?.fetchedAt || '',
    status: turnoverLoading.value
      ? 'loading'
      : turnoverError.value
      ? turnoverData.value
        ? 'stale'
        : 'error'
      : turnoverData.value?.status || 'no_data',
    isStale: Boolean(turnoverData.value?.isStale || (turnoverError.value && turnoverData.value)),
    message: turnoverError.value || turnoverData.value?.message,
  }));
  const sectorRows = computed<SectorRow[]>(() =>
    (liveSectorFlow.value?.rows || []).map((row) => ({
      name: row.name,
      pct: row.returnPct == null ? null : Number(row.returnPct),
      net: Number(row.netInflowYuan),
      netYi: Number(row.netInflowYuan) / 1e8,
      inflowYi: Number(row.inflowYuan) / 1e8,
      outflowYi: Number(row.outflowYuan) / 1e8,
      firms: row.firmCount ?? null,
    })),
  );
  const visibleSectorRows = computed(() =>
    sectorsExpanded.value ? sectorRows.value : sectorRows.value.slice(0, 7),
  );
  const rotationRows = computed(() =>
    sectorRows.value
      .filter((r) => r.netYi != null)
      .slice()
      .sort((a, b) => Math.abs(b.netYi || 0) - Math.abs(a.netYi || 0)),
  );
  const rotationInflow = computed(() =>
    rotationRows.value.filter((r) => (r.netYi || 0) > 0).slice(0, 6),
  );
  const rotationOutflow = computed(() =>
    rotationRows.value
      .filter((r) => (r.netYi || 0) < 0)
      .sort((a, b) => (a.netYi || 0) - (b.netYi || 0))
      .slice(0, 6),
  );
  async function loadLiveSectorFlow() {
    if (liveSectorFlowLoading.value) return;
    liveSectorFlowLoading.value = true;
    try {
      liveSectorFlow.value = await getAShareLiveSectorFundFlow();
      liveSectorFlowError.value = '';
    } catch (error) {
      liveSectorFlowError.value = error instanceof Error ? error.message : '实时板块资金流加载失败';
    } finally {
      liveSectorFlowLoading.value = false;
    }
  }
  async function loadLiveTurnover() {
    if (turnoverLoading.value) return;
    turnoverLoading.value = true;
    try {
      turnoverData.value = await getAShareLiveMarketTurnover();
      turnoverError.value = '';
      if (!turnoverData.value.historyDates?.includes(selectedHotDate.value))
        selectedHotDate.value = turnoverData.value.historyDates?.at(-1) || '';
    } catch (error) {
      turnoverError.value = error instanceof Error ? error.message : '成交额榜加载失败';
    } finally {
      turnoverLoading.value = false;
    }
  }
  async function loadLive() {
    if (document.visibilityState === 'hidden') return;
    lastLiveLoad = Date.now();
    await Promise.allSettled([loadLiveSectorFlow(), loadLiveTurnover()]);
  }
  function resumeLive() {
    if (Date.now() - lastLiveLoad >= 5 * 60 * 1000) void loadLive();
  }
  watch(
    () => props.refreshKey,
    () => void loadLive(),
  );
  onMounted(() => {
    void loadLive();
    liveTimer = window.setInterval(resumeLive, 5 * 60 * 1000);
    document.addEventListener('visibilitychange', resumeLive);
  });
  onBeforeUnmount(() => {
    if (liveTimer != null) window.clearInterval(liveTimer);
    document.removeEventListener('visibilitychange', resumeLive);
  });
  const turnoverRows = computed<TurnoverRow[]>(() => {
    return (turnoverData.value?.rows || []).map((r) => ({
      securityCode: r.securityCode,
      securityName: r.securityName,
      price: r.price,
      returnPct: r.returnPct,
      turnoverYi: r.turnoverYuan == null ? null : Number(r.turnoverYuan) / 1e8,
      marketCapYi: r.marketCapYuan == null ? null : Number(r.marketCapYuan) / 1e8,
      industry: r.industry,
    }));
  });
  const highTurnoverRows = computed<TurnoverRow[]>(() =>
    (turnoverData.value?.highTurnoverRows || []).map((row) => ({
      securityCode: row.securityCode,
      securityName: row.securityName,
      price: row.price,
      returnPct: row.returnPct,
      turnoverYi: row.turnoverYuan == null ? null : Number(row.turnoverYuan) / 1e8,
      marketCapYi: row.marketCapYuan == null ? null : Number(row.marketCapYuan) / 1e8,
      industry: row.industry,
    })),
  );
  const selectedHistoricalHotRows = computed(() => {
    const date = selectedHotDate.value || turnoverData.value?.historyDates?.at(-1);
    return (turnoverData.value?.historicalRows || []).filter((row) => row.observedAt === date);
  });
  const highTurnoverMaxYi = computed(() =>
    Math.max(1, ...highTurnoverRows.value.map((row) => row.turnoverYi || 0)),
  );
  function hotStockBarWidth(value: number | null) {
    return Math.max(4, ((value || 0) / highTurnoverMaxYi.value) * 100);
  }
  const breadthMetrics = computed(() => {
    const v = breadth.value;
    if (!v) return [];
    return [
      { label: '上涨', value: v.up, note: '当日上涨家数', tone: 'up' },
      { label: '下跌', value: v.down, note: '当日下跌家数', tone: 'down' },
      { label: '平盘', value: v.flat, note: '当日平盘家数', tone: '' },
      {
        label: '涨停 / 真实涨停',
        value: `${v.limitUp ?? '—'} / ${v.realLimitUp ?? '—'}`,
        note: '来源原始口径',
        tone: 'up',
      },
      {
        label: '跌停 / 真实跌停',
        value: `${v.limitDown ?? '—'} / ${v.realLimitDown ?? '—'}`,
        note: '来源原始口径',
        tone: 'down',
      },
      {
        label: '活跃度',
        value: formatActivity(v.activityPct),
        note: '赚钱效应活跃度',
        tone: '',
      },
      { label: '市场宽度', value: v.breadthState, note: v.tradeDate || '最新交易日', tone: '' },
      { label: '题材投机', value: v.speculationState, note: '按真实涨停数量分类', tone: '' },
    ];
  });
  const emotionMetrics = computed(() => {
    const v = emotion.value;
    if (!v) return [];
    return [
      { label: '涨停', value: v.limitUpCount, note: v.tradeDate || '最新交易日', tone: 'up' },
      { label: '炸板', value: v.brokenBoardCount, note: '触板后未封住', tone: 'down' },
      { label: '跌停', value: v.limitDownCount, note: '当日跌停池', tone: 'down' },
      { label: '最高连板', value: `${v.highestBoardCount}板`, note: '涨停池最高', tone: '' },
      { label: '二板及以上', value: v.consecutiveBoardCount, note: '当日连板股数量', tone: '' },
      {
        label: '封板率',
        value: formatRate(v.sealRatePct),
        note: '涨停 /（涨停＋炸板）',
        tone: 'up',
      },
      {
        label: '炸板率',
        value: formatRate(v.breakRatePct),
        note: '炸板 /（涨停＋炸板）',
        tone: 'down',
      },
      {
        label: '晋级率',
        value: formatRate(v.promotionRatePct),
        note: '今日二板+ / 昨日涨停',
        tone: '',
      },
    ];
  });
  function numeric(v: unknown) {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  function formatPct(v: unknown, ratio = false) {
    const n = numeric(v);
    if (n == null) return '—';
    const value = ratio ? n * 100 : n;
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  }
  function formatRate(v: unknown) {
    const n = numeric(v);
    return n == null ? '—' : `${n.toFixed(1)}%`;
  }
  function formatActivity(v: unknown) {
    if (v == null) return '—';
    const text = String(v);
    return text.endsWith('%') ? text : `${text}%`;
  }
  function formatYi(v: unknown) {
    const n = numeric(v);
    return n == null ? '—' : `${n.toFixed(2)}亿`;
  }
  function formatHundredMillion(v: unknown) {
    const n = numeric(v);
    return n == null ? '—' : `${n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}亿`;
  }
  function tone(v: unknown) {
    const n = numeric(v);
    return n == null ? '' : n > 0 ? 'up' : n < 0 ? 'down' : '';
  }
  function formatDate(v: string | null | undefined) {
    if (!v) return '最新交易日';
    const d = new Date(v);
    return Number.isNaN(d.getTime()) ? v : d.toLocaleString('zh-CN', { hour12: false });
  }
</script>

<style scoped lang="less">
  .overview-card,
  .panel {
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .overview-card {
    display: grid;
    gap: 14px;
  }

  .overview-header,
  .panel-title {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .eyebrow {
    margin: 0 0 3px;
    color: var(--strategy-text-4);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .overview-header h2,
  .panel h3 {
    margin: 0;
    color: var(--strategy-text-1);
  }

  .overview-header h2 {
    font-size: 20px;
  }

  .panel h3 {
    font-size: 15px;
  }

  .updated,
  .panel-title p,
  .source-note {
    margin: 0;
    color: var(--strategy-text-4);
    font-size: 12px;
  }

  .source-note {
    margin-top: 6px;
    font-size: 11px;
  }

  .overview-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .metric-panel {
    padding: 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface-2);
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 9px;
    margin-top: 12px;
  }

  .metric-cell {
    min-width: 0;
    padding: 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 9px;
    background: var(--strategy-surface);
  }

  .metric-cell span,
  .metric-cell small {
    display: block;
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  .metric-cell strong {
    display: block;
    margin: 5px 0 2px;
    color: var(--strategy-text-1);
    font-size: 18px;
    font-variant-numeric: tabular-nums;
  }

  .overview-meta-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 9px;
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--strategy-border);
  }

  .overview-meta-grid > div {
    padding: 8px;
    border-radius: 8px;
    background: var(--strategy-surface);
    text-align: center;
  }

  .overview-meta-grid .meta-action {
    display: block;
    width: 100%;
    padding: 8px;
    border: 0;
    border-radius: 8px;
    background: var(--strategy-surface);
    color: inherit;
    text-align: center;
    cursor: pointer;
  }

  .overview-meta-grid .meta-action:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }

  .overview-meta-grid .meta-action:hover:not(:disabled) {
    background: var(--strategy-accent-soft);
  }

  .overview-meta-grid span {
    display: block;
    color: var(--strategy-text-3);
    font-size: 10px;
  }

  .overview-meta-grid strong {
    display: block;
    margin-top: 4px;
    color: var(--strategy-text-1);
    font-size: 15px;
    font-variant-numeric: tabular-nums;
  }

  .up {
    color: var(--strategy-up, #ef4444) !important;
  }

  .down {
    color: var(--strategy-down, #10b981) !important;
  }

  .emotion-detail {
    display: block;
    margin-top: 12px;
  }

  .history-panel,
  .matrix-panel {
    display: grid;
    gap: 12px;
  }

  .history-actions {
    display: flex;
    gap: 4px;
  }

  .history-actions button {
    padding: 3px 8px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    font-size: 11px;
    cursor: pointer;
  }

  .history-actions button.active {
    border-color: var(--strategy-accent-strong);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .history-charts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .history-chart {
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface-2);
  }

  .chart-title {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    color: var(--strategy-text-2);
    font-size: 12px;
  }

  .chart-title span,
  .chart-legend {
    color: var(--strategy-text-4);
    font-size: 11px;
  }

  .history-chart svg {
    display: block;
    width: 100%;
    height: 220px;
    margin-top: 5px;
  }

  .chart-grid {
    stroke-width: 1;
    stroke-dasharray: 3 4;
    stroke: var(--strategy-border);
  }

  .chart-line {
    stroke-width: 2.4;
    stroke-linecap: round;
    fill: none;
    stroke-linejoin: round;
  }

  .chart-line--up {
    stroke: var(--strategy-up, #ef4444);
  }

  .chart-line--down {
    stroke: var(--strategy-down, #10b981);
  }

  .chart-line--breadth {
    stroke: var(--strategy-accent-strong, #4338ca);
  }

  .chart-label {
    fill: var(--strategy-text-4);
    font-size: 10px;
  }

  .chart-legend {
    display: flex;
    gap: 14px;
    align-items: center;
  }

  .chart-legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .legend-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .legend-dot--up {
    background: var(--strategy-up, #ef4444);
  }

  .legend-dot--down {
    background: var(--strategy-down, #10b981);
  }

  .legend-dot--breadth {
    background: var(--strategy-accent-strong, #4338ca);
  }

  .matrix-shell table {
    min-width: 900px;
  }

  .matrix-total td {
    background: var(--strategy-accent-soft);
    font-weight: 700;
  }

  .emotion-subpanel,
  .rotation-column {
    padding: 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  .emotion-subpanel h4,
  .rotation-column h4 {
    margin: 0 0 10px;
    color: var(--strategy-text-2);
    font-size: 13px;
  }

  .ladder-trigger {
    display: flex;
    align-items: center;
    gap: 18px;
    width: 100%;
    border: 1px solid var(--strategy-border);
    color: inherit;
    text-align: left;
    cursor: pointer;
  }

  .ladder-trigger:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .subpanel-heading {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    min-width: 180px;
    margin-bottom: 0;
    gap: 8px;
  }

  .subpanel-heading span,
  .emotion-summary-panel p {
    margin: 0;
    color: var(--strategy-text-4);
    font-size: 11px;
  }

  .ladder-list {
    display: grid;
    flex: 1;
    grid-template-columns: repeat(4, minmax(110px, 1fr));
    gap: 12px;
  }

  .ladder-row {
    display: grid;
    grid-template-columns: 45px minmax(0, 1fr) 24px;
    align-items: center;
    gap: 8px;
    color: var(--strategy-text-2);
    font-size: 12px;
  }

  .ladder-row + .ladder-row {
    margin-top: 0;
  }

  .ladder-list > div {
    display: grid;
    grid-template-columns: 45px minmax(0, 1fr) 24px;
    align-items: center;
    gap: 8px;
    color: var(--strategy-text-2);
    font-size: 12px;
  }

  .ladder-track {
    height: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--strategy-border);
  }

  .ladder-track i {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--strategy-accent-strong);
  }

  .hot-stock-summary {
    display: flex;
    align-items: baseline;
    gap: 12px;
    padding: 8px 2px 2px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .hot-stock-summary strong {
    color: var(--strategy-text-1);
    font-size: 20px;
  }

  .hot-stock-bars {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px 14px;
  }

  .hot-stock-bar {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr) 66px;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    border: 0;
    background: transparent;
    color: var(--strategy-text-2);
    font-size: 11px;
    text-align: left;
    cursor: pointer;
  }

  .hot-stock-bar i {
    height: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--strategy-border);
  }

  .hot-stock-bar b {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--strategy-accent-strong), var(--strategy-up));
  }

  .hot-stock-bar strong {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .hot-history-panel {
    display: grid;
    gap: 10px;
    padding-top: 14px;
    border-top: 1px solid var(--strategy-border);
  }

  .hot-history-head {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 12px;
  }

  .hot-history-head h4 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 14px;
  }
  .hot-history-head span,
  .hot-history-head b {
    color: var(--strategy-text-4);
    font-size: 11px;
    font-weight: 500;
  }

  .hot-history-dates {
    display: grid;
    grid-auto-flow: column;
    grid-auto-columns: minmax(80px, 1fr);
    overflow-x: auto;
    padding-bottom: 6px;
    gap: 6px;
  }

  .hot-history-dates button {
    display: grid;
    gap: 2px;
    padding: 6px;
    border: 1px solid var(--strategy-border);
    border-radius: 7px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    cursor: pointer;
  }

  .hot-history-dates button strong {
    color: var(--strategy-text-1);
    font-size: 15px;
  }
  .hot-history-dates button.active {
    border-color: var(--strategy-accent-strong);
    background: var(--strategy-accent-soft);
  }
  .hot-history-matrix table {
    min-width: 100%;
    width: max-content;
  }
  .hot-history-matrix th,
  .hot-history-matrix td {
    min-width: 68px;
  }
  .hot-history-matrix .is-left {
    position: sticky;
    left: 0;
    background: var(--strategy-surface-2);
    min-width: 130px;
  }
  .hot-history-matrix {
    overflow: auto;
    max-height: 260px;
  }

  .hot-history-day {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .hot-history-day > strong {
    margin-right: 4px;
    color: var(--strategy-text-2);
    font-size: 12px;
  }
  .hot-history-day button {
    padding: 4px 7px;
    border: 1px solid var(--strategy-border);
    border-radius: 999px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-2);
    font-size: 11px;
    cursor: pointer;
  }
  .hot-history-day button span {
    margin-left: 4px;
    color: var(--strategy-text-4);
  }

  .table-shell {
    overflow-x: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
  }

  table {
    width: 100%;
    min-width: 560px;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 9px 8px;
    border-bottom: 1px solid var(--strategy-border);
    color: var(--strategy-text-2);
    font-size: 12px;
    text-align: center;
    white-space: nowrap;
  }

  th {
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  tbody tr:last-child td {
    border-bottom: 0;
  }

  td strong,
  td small {
    display: block;
  }

  td small {
    margin-top: 2px;
    color: var(--strategy-text-4);
    font-size: 10px;
  }

  .is-left {
    text-align: left;
  }

  .stock-name-button {
    display: block;
    padding: 0;
    border: 0;
    background: none;
    color: var(--strategy-text-1);
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }

  .stock-name-button:hover {
    color: var(--strategy-accent-strong);
  }

  .is-right {
    text-align: right;
  }

  .empty-cell,
  .empty,
  .empty-inline {
    padding: 18px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  .empty-inline {
    margin: 0;
    padding: 8px 0;
    font-size: 11px;
  }

  .link-button {
    display: block;
    margin: 10px 0 0 auto;
    border: 0;
    background: none;
    color: var(--strategy-accent-strong);
    font-size: 11px;
    cursor: pointer;
  }

  .rotation-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 12px;
  }

  .rotation-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    gap: 8px;
    align-items: center;
    padding: 7px 0;
    border-bottom: 1px solid var(--strategy-border);
    font-size: 12px;
  }

  .rotation-row:last-child {
    border-bottom: 0;
  }

  .rotation-row b,
  .rotation-row em {
    font-size: 11px;
    font-style: normal;
  }

  .wide-panel {
    display: grid;
    gap: 12px;
  }

  .turnover-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .turnover-actions button {
    padding: 2px 7px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    font-size: 11px;
    cursor: pointer;
  }

  .turnover-actions button.active {
    border-color: var(--strategy-accent-strong);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .panel :deep(.research-source-state),
  .metric-panel :deep(.research-source-state) {
    white-space: nowrap;
  }

  .detail-modal-mask {
    display: flex;
    position: fixed;
    z-index: 50;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgb(15 23 42 / 55%);
    inset: 0;
  }

  .detail-modal {
    width: min(1100px, 100%);
    max-height: min(78vh, 760px);
    overflow: auto;
  }

  .modal-close {
    padding: 4px 9px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  @media (max-width: 900px) {
    .overview-grid {
      grid-template-columns: 1fr;
    }

    .emotion-detail {
      grid-template-columns: 1fr;
    }

    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .rotation-grid {
      grid-template-columns: 1fr;
    }

    .history-charts {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 560px) {
    .metric-grid {
      grid-template-columns: 1fr;
    }

    .overview-meta-grid {
      grid-template-columns: 1fr;
    }

    .overview-header {
      flex-direction: column;
    }
  }
</style>
