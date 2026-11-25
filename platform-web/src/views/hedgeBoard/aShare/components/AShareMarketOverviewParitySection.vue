<template>
  <section id="a-share-market-overview" class="overview-card">
    <AShareLegacyTerminalSection
      v-if="dashboard && mode !== 'crowding'"
      :dashboard="dashboard"
      view="overview"
      :refresh-key="refreshKey"
    >
      <template #breadth>
        <div class="overview-meta-grid">
          <button
            type="button"
            class="meta-action"
            :disabled="!marketAmountRows.length"
            title="点击查看全A成交额历史统计"
            @click="marketAmountHistoryOpen = true"
            ><span>全A成交额</span
            ><strong>{{ formatHundredMillion(latestHistory?.total_amount_100m) }}</strong
            ><small>点击查看历史</small></button
          >
          <button
            type="button"
            class="meta-action"
            :disabled="hotStockCount == null"
            @click="hotMatrixOpen = true"
            ><span>百亿成交股</span
            ><strong>{{ hotStockCount == null ? '—' : `${hotStockCount}只` }}</strong
            ><small>点击查看明细</small></button
          >
          <button
            type="button"
            class="meta-action"
            :aria-expanded="marketBreadthOpen"
            @click="marketBreadthOpen = !marketBreadthOpen"
            title="沪深A；（上涨家数－下跌家数）/（上涨家数＋下跌家数），不含平盘"
            ><span>市场宽度</span
            ><strong>{{ formatPct(latestHistory?.market_breadth, true) }}</strong
            ><small>{{ breadth?.breadthState || '—' }}</small></button
          >
        </div>
      </template>
    </AShareLegacyTerminalSection>
    <section
      v-if="dashboard && mode !== 'crowding'"
      class="market-structure"
      aria-label="市场涨跌结构"
    >
      <div class="structure-sources">
        <ResearchSourceState v-if="dashboard.breadth" :meta="dashboard.breadth.meta" />
        <ResearchSourceState v-if="dashboard.emotion" :meta="dashboard.emotion.meta" />
      </div>
      <div class="structure-summary">
        <div v-for="item in structureMetrics" :key="item.label" class="structure-metric">
          <span>{{ item.label }}</span
          ><strong :class="item.tone">{{ item.value ?? '—' }}</strong>
        </div>
        <button
          type="button"
          class="structure-metric structure-ladder"
          :disabled="!ladderRows.length"
          @click="ladderOpen = true"
        >
          <span>连板梯队</span>
          <strong>{{
            ladderRows.length
              ? ladderRows.map((row) => `${row.boardCount}：${row.stockCount}只`).join(' · ')
              : '—'
          }}</strong>
        </button>
      </div>
      <VibeTrendCharts
        v-if="allHistoryRows.length > 1"
        mode="overview"
        :show-breadth="false"
        :rows="allHistoryRows"
      />
    </section>
    <VibeTrendCharts
      v-if="mode === 'crowding' && allHistoryRows.length > 1"
      mode="crowding"
      :show-breadth="false"
      :rows="allHistoryRows"
      :crowding-rows="dashboard?.crowding?.data?.history"
      :innovation-rows="dashboard?.crowding?.data?.innovationHistory"
    />
    <Modal
      v-if="marketBreadthOpen"
      v-model:open="marketBreadthOpen"
      title="市场宽度"
      :footer="null"
      width="min(1050px, calc(100vw - 32px))"
      :get-container="false"
    >
      <VibeTimeChart
        title="市场宽度"
        y-label="（上涨－下跌）/（上涨＋下跌）× 100%"
        :dates="allHistoryRows.map((row) => row.date)"
        :series="[
          {
            name: '市场宽度',
            values: allHistoryRows.map((row) => row.market_breadth),
            type: 'line',
            color: '#123d68',
            percent: true,
            domain: [-1, 1],
            ticks: [1, 0.5, 0, -0.5, -1],
          },
        ]"
      />
    </Modal>
    <template v-if="mode !== 'crowding'">
      <div class="fund-flow-layout" role="region" aria-label="行业资金与成交额">
        <article class="panel industry-flow-panel">
          <div class="panel-title"
            ><div><h3>一级行业资金榜</h3></div
            ><ResearchSourceState :meta="sectorFlowMeta"
          /></div>
          <div
            v-if="sectorRows.length"
            class="table-shell funds-table-scroll"
            tabindex="0"
            role="region"
            aria-label="一级行业资金榜明细"
            ><table
              ><thead
                ><tr
                  ><th class="is-left">行业</th><th>涨跌%</th><th>今日主力净流入</th
                  ><th>家数</th></tr
                ></thead
              ><tbody
                ><tr v-for="row in sectorRows" :key="row.name"
                  ><td class="is-left"
                    ><strong>{{ row.name }}</strong></td
                  ><td :class="tone(row.pct)">{{ formatPct(row.pct) }}</td
                  ><td :class="tone(row.net)">{{ formatYi(row.netYi) }}</td
                  ><td>{{ row.firms ?? '—' }}</td></tr
                ></tbody
              ></table
            ></div
          ><div v-else class="empty">{{ sectorEmptyText || '暂无板块资金数据' }}</div>
        </article>
        <div class="fund-flow-right">
          <article class="panel rotation-panel"
            ><div class="panel-title"
              ><div><h3>资金轮动</h3></div></div
            ><div
              v-if="rotationRows.length"
              class="rotation-grid funds-table-scroll"
              tabindex="0"
              role="region"
              aria-label="资金轮动明细"
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
            ><div v-else class="empty">{{ sectorEmptyText || '暂无资金轮动数据' }}</div></article
          >
          <article class="panel turnover-panel"
            ><div class="panel-title"
              ><div><h3>全市场成交额榜</h3><ResearchSourceState :meta="turnoverMeta" /></div></div
            ><div
              v-if="turnoverRows.length"
              class="table-shell funds-table-scroll turnover-table-scroll"
              tabindex="0"
              role="region"
              aria-label="全市场成交额榜明细"
              ><table
                ><thead
                  ><tr
                    ><th>#</th><th class="is-left">名称 / 代码</th><th>现价</th><th>涨跌%</th
                    ><th>成交额</th><th>总市值</th><th>行业</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="(row, index) in turnoverRows.slice(0, 20)" :key="row.securityCode"
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
              >{{ turnoverLoading ? '正在读取成交额榜…' : turnoverError || '暂无成交额榜数据'
              }}<button
                v-if="!turnoverLoading"
                type="button"
                class="link-button"
                @click="loadLiveTurnover"
                >重试</button
              ></div
            ></article
          >
        </div>
      </div>
      <slot v-if="dashboard"></slot>
      <Modal
        v-if="hotMatrixOpen"
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
        v-if="marketAmountHistoryOpen"
        v-model:open="marketAmountHistoryOpen"
        title="全A成交额 · 历史统计"
        :footer="null"
        width="min(960px, calc(100vw - 32px))"
        :get-container="false"
      >
        <article class="panel">
          <div class="market-amount-summary">
            <strong>{{ marketAmountData?.tradingDays ?? marketAmountRows.length }} 个交易日</strong>
            <span>
              {{ marketAmountData?.coverageStart || marketAmountRows.at(-1)?.observedAt || '—' }} 至
              {{ marketAmountData?.coverageEnd || marketAmountRows[0]?.observedAt || '—' }} ·
              单位：亿元 · 最新日期在最上方
            </span>
          </div>
          <div v-if="marketAmountRows.length" class="table-shell market-amount-table">
            <table>
              <thead>
                <tr>
                  <th>交易日</th>
                  <th title="括号内为成交额相对20日日均的变化率">全A成交额（亿元）</th>
                  <th>20日日均（亿元）</th>
                  <th>数据来源</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in pagedMarketAmountRows" :key="row.observedAt">
                  <td>{{ row.observedAt }}</td>
                  <td>
                    {{
                      formatHundredMillion(
                        row.totalAmountYuan == null ? null : Number(row.totalAmountYuan) / 1e8,
                      )
                    }}
                    <span
                      v-if="row.deviationFromAverage != null"
                      class="market-amount-deviation"
                      :class="tone(row.deviationFromAverage)"
                      title="相对20日日均"
                      >（{{ formatPct(row.deviationFromAverage, true) }}）</span
                    >
                  </td>
                  <td>
                    {{
                      formatHundredMillion(
                        row.amount20dAverageYuan == null
                          ? null
                          : Number(row.amount20dAverageYuan) / 1e8,
                      )
                    }}
                  </td>
                  <td class="source-cell" :title="row.source || '来源未记录'">
                    {{ row.source || '来源缺失' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div
            v-if="marketAmountPageCount > 1"
            class="market-amount-pagination"
            aria-label="全A成交额历史分页"
          >
            <button type="button" :disabled="marketAmountPage <= 1" @click="marketAmountPage -= 1"
              >上一页</button
            >
            <span>第 {{ marketAmountPage }} / {{ marketAmountPageCount }} 页</span>
            <button
              type="button"
              :disabled="marketAmountPage >= marketAmountPageCount"
              @click="marketAmountPage += 1"
              >下一页</button
            >
          </div>
          <div v-if="!marketAmountRows.length" class="empty">{{
            marketAmountError ||
            (marketAmountLoading ? '正在加载全A成交额历史' : '暂无全A成交额历史数据')
          }}</div>
        </article>
      </Modal>
      <Modal
        v-if="ladderOpen"
        v-model:open="ladderOpen"
        title="连板股清单"
        :footer="null"
        width="min(900px, calc(100vw - 32px))"
        :get-container="false"
      >
        <article class="panel">
          <div class="panel-title"
            ><h3>连板股清单</h3
            ><button type="button" class="modal-close" @click="ladderOpen = false"
              >关闭</button
            ></div
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
    </template>
  </section>
</template>

<script setup lang="ts">
  import { computed, onDeactivated, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
  import { useDashboardRefresh } from '../../useDashboardRefresh';
  import {
    getAShareLiveSectorFundFlow,
    getAShareLiveMarketTurnover,
    getAShareMarketHistory,
    type AShareDashboardResponse,
    type AShareLiveSectorFundFlowResponse,
    type AShareMarketTurnoverResponse,
    type AShareMarketHistoryResponse,
    type ResearchSourceMeta,
  } from '@/api/hedgeResearch';
  import { Modal } from 'ant-design-vue';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';
  import AShareLegacyTerminalSection from './AShareLegacyTerminalSection.vue';
  import VibeTrendCharts from './VibeTrendCharts.vue';
  import VibeTimeChart from './VibeTimeChart.vue';

  import { useResearchViewState, useResearchSnapshots } from '../../composables/researchWorkspace';

  const snapshots = useResearchSnapshots();
  const controller = new AbortController();
  const props = defineProps<{
    mode?: 'overview' | 'crowding';
    dashboard: AShareDashboardResponse | null;
    refreshKey?: number;
  }>();
  const emit = defineEmits<{ (event: 'query', code: string): void; (event: 'ready'): void }>();
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
  const liveSectorFlow = shallowRef<AShareLiveSectorFundFlowResponse | null>(null);
  const turnoverData = shallowRef<AShareMarketTurnoverResponse | null>(null);
  const liveSectorFlowError = ref('');
  const liveSectorFlowLoading = ref(false);
  const turnoverLoading = ref(false);
  const turnoverError = ref('');
  const marketBreadthOpen = ref(false);
  const ladderOpen = ref(false);
  const hotMatrixOpen = ref(false);
  const marketAmountHistoryOpen = ref(false);
  const marketAmountPage = useResearchViewState('marketAmountPage', 1);
  const marketAmountData = shallowRef<AShareMarketHistoryResponse | null>(null);
  const marketAmountLoading = ref(false);
  const marketAmountError = ref('');
  const selectedHotDate = useResearchViewState('selectedHotDate', '');
  const hotHistoryRange = useResearchViewState<10 | 30 | 'all'>('hotHistoryRange', 10);
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
      limit_up: row.allALimitUp,
      limit_down: row.allALimitDown,
      total_amount_100m: row.totalAmountYuan == null ? null : Number(row.totalAmountYuan) / 1e8,
      market_breadth: row.marketBreadthPct == null ? null : Number(row.marketBreadthPct) / 100,
      csi300Close: row.csi300Close == null ? null : Number(row.csi300Close),
    })),
  );
  const marketAmountRows = computed(() => {
    if (marketAmountData.value) return marketAmountData.value.rows;
    const sourceRows = [...(props.dashboard?.marketHistory || [])].sort((a, b) =>
      a.observedAt.localeCompare(b.observedAt),
    );
    const rows = sourceRows
      .map((row, index) => {
        const window = sourceRows.slice(Math.max(0, index - 19), index + 1);
        return {
          ...row,
          amount20dAverageYuan:
            window.length === 20 && window.every((item) => item.totalAmountYuan != null)
              ? window.reduce((sum, item) => sum + Number(item.totalAmountYuan), 0) / 20
              : null,
        };
      })
      .reverse();
    return rows;
  });
  const marketAmountPageCount = computed(() =>
    Math.max(1, Math.ceil((marketAmountData.value?.total ?? marketAmountRows.value.length) / 100)),
  );
  const pagedMarketAmountRows = computed(() => {
    const rows = marketAmountData.value
      ? marketAmountRows.value
      : marketAmountRows.value.slice(
          (marketAmountPage.value - 1) * 100,
          marketAmountPage.value * 100,
        );
    return rows.map((row) => {
      const amount = numeric(row.totalAmountYuan);
      const average = numeric(row.amount20dAverageYuan);
      return {
        ...row,
        deviationFromAverage:
          amount != null && average != null && average > 0 ? (amount - average) / average : null,
      };
    });
  });
  let historyController: AbortController | undefined;
  async function loadMarketAmountHistory() {
    historyController?.abort();
    const requestController = (historyController = new AbortController());
    marketAmountLoading.value = true;
    try {
      const result = await getAShareMarketHistory(
        marketAmountPage.value,
        100,
        requestController.signal,
      );
      if (requestController.signal.aborted) return;
      marketAmountData.value = result;
      marketAmountError.value = '';
    } catch (error) {
      if (requestController.signal.aborted) return;
      marketAmountError.value = error instanceof Error ? error.message : '全A成交额历史加载失败';
    } finally {
      if (!requestController.signal.aborted) marketAmountLoading.value = false;
    }
  }
  watch(marketAmountHistoryOpen, (open) => {
    if (open) void loadMarketAmountHistory();
    else historyController?.abort();
  });
  watch(marketAmountPage, () => {
    if (marketAmountHistoryOpen.value) void loadMarketAmountHistory();
  });
  const latestHistory = computed(() => allHistoryRows.value.at(-1) || null);
  const hotStockCount = computed(() => turnoverData.value?.highTurnoverCount ?? null);
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
  const sectorEmptyText = computed(() =>
    liveSectorFlowLoading.value ? '正在读取板块资金流…' : liveSectorFlowError.value,
  );
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
      liveSectorFlow.value = await getAShareLiveSectorFundFlow(controller.signal);
      if (!controller.signal.aborted) snapshots.set('sector-flow', liveSectorFlow.value);
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
      turnoverData.value = await getAShareLiveMarketTurnover(controller.signal);
      if (!controller.signal.aborted) snapshots.set('turnover', turnoverData.value);
      turnoverError.value = '';
      if (!turnoverData.value.historyDates?.includes(selectedHotDate.value))
        selectedHotDate.value = turnoverData.value.historyDates?.at(-1) || '';
    } catch (error) {
      turnoverError.value = error instanceof Error ? error.message : '成交额榜加载失败';
    } finally {
      turnoverLoading.value = false;
    }
  }
  async function loadLive(reuse = false) {
    if (props.mode === 'crowding') {
      emit('ready');
      return;
    }
    if (document.visibilityState === 'hidden') return;
    const flow = reuse && snapshots.get<AShareLiveSectorFundFlowResponse>('sector-flow');
    const turnover = reuse && snapshots.get<AShareMarketTurnoverResponse>('turnover');
    if (flow) liveSectorFlow.value = flow;
    if (turnover) turnoverData.value = turnover;
    await Promise.allSettled([
      flow ? undefined : loadLiveSectorFlow(),
      turnover ? undefined : loadLiveTurnover(),
    ]);
    if (!controller.signal.aborted) emit('ready');
  }
  onDeactivated(() => {
    marketBreadthOpen.value =
      ladderOpen.value =
      hotMatrixOpen.value =
      marketAmountHistoryOpen.value =
        false;
  });
  useDashboardRefresh(() => loadLive(), {
    intervalMs: 300_000,
    immediate: false,
    enabled: () =>
      props.mode !== 'crowding' && !liveSectorFlowLoading.value && !turnoverLoading.value,
  });
  watch(
    () => props.refreshKey,
    () => void loadLive(),
  );
  onMounted(() => {
    void loadLive(true);
  });
  onBeforeUnmount(() => {
    controller.abort();
    historyController?.abort();
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
  const structureMetrics = computed(() => [
    { label: '上涨', value: breadth.value?.up, tone: 'up' },
    { label: '下跌', value: breadth.value?.down, tone: 'down' },
    { label: '涨停', value: emotion.value?.limitUpCount, tone: 'up' },
    { label: '跌停', value: emotion.value?.limitDownCount, tone: 'down' },
    { label: '炸板', value: emotion.value?.brokenBoardCount, tone: 'down' },
    { label: '封板率', value: formatRate(emotion.value?.sealRatePct), tone: 'up' },
  ]);
  function numeric(v: unknown) {
    if (v == null || v === '') return null;
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
</script>

<style scoped lang="less">
  .market-structure {
    min-width: 0;
  }

  .structure-sources {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin-bottom: 8px;
  }

  .structure-summary {
    display: flex;
    align-items: stretch;
    margin-bottom: 10px;
    overflow-x: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  .structure-metric {
    display: flex;
    flex: 1 0 auto;
    align-items: center;
    justify-content: center;
    padding: 12px 14px;
    color: var(--strategy-text-3);
    font-size: 12px;
    white-space: nowrap;
    gap: 8px;
  }

  .structure-metric + .structure-metric {
    border-left: 1px solid var(--strategy-border);
  }

  .structure-metric strong {
    color: var(--strategy-text-1);
    font-variant-numeric: tabular-nums;
  }

  .structure-ladder {
    border: 0;
    background: transparent;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  .structure-ladder:hover:not(:disabled) {
    background: var(--strategy-accent-soft);
  }

  .structure-ladder:disabled {
    cursor: default;
  }

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
    grid-template-columns: minmax(0, 1fr);
    min-width: 0;
    container: ashare-overview / inline-size;
    gap: 14px;
  }

  .overview-card > *,
  .panel {
    min-width: 0;
  }

  .panel-title {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .panel h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 15px;
  }

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

  .fund-flow-layout {
    --rotation-height: 280px;
    --turnover-height: 560px;
    --fund-gap: 14px;

    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    min-width: 0;
    height: calc(var(--rotation-height) + var(--turnover-height) + var(--fund-gap));
    gap: var(--fund-gap);
  }

  .fund-flow-right {
    display: grid;
    grid-template-rows: var(--rotation-height) var(--turnover-height);
    gap: var(--fund-gap);
    min-width: 0;
    min-height: 0;
  }

  .industry-flow-panel,
  .rotation-panel,
  .turnover-panel {
    display: flex;
    box-sizing: border-box;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
    gap: 12px;
  }

  .fund-flow-layout .panel-title {
    flex: 0 0 auto;
    flex-wrap: wrap;
  }

  .fund-flow-layout .funds-table-scroll {
    flex: 1 1 0;
    min-width: 0;
    min-height: 0;
    overflow: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .fund-flow-layout .rotation-grid {
    margin-top: 0;
  }

  .fund-flow-layout th {
    position: sticky;
    z-index: 1;
    top: 0;
  }

  .fund-flow-layout table {
    min-width: 460px;
  }

  .turnover-table-scroll table {
    min-width: 680px;
  }

  .turnover-table-scroll th {
    box-sizing: border-box;
    height: 32px;
    padding: 5px 8px;
  }

  .turnover-table-scroll td {
    box-sizing: border-box;
    height: 42px;
    padding: 5px 8px;
    line-height: 16px;
  }

  .turnover-table-scroll td small {
    line-height: 12px;
  }

  .funds-table-scroll:focus-visible {
    outline: 2px solid var(--strategy-accent-strong);
    outline-offset: -2px;
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

  button.metric-cell {
    border: 0;
    font: inherit;
    text-align: left;
    cursor: pointer;
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
    grid-template-columns: repeat(4, minmax(110px, 1fr));
    flex: 1;
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
    grid-auto-columns: minmax(80px, 1fr);
    grid-auto-flow: column;
    padding-bottom: 6px;
    overflow-x: auto;
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
    width: max-content;
    min-width: 100%;
  }

  .hot-history-matrix th,
  .hot-history-matrix td {
    min-width: 68px;
  }

  .hot-history-matrix .is-left {
    position: sticky;
    left: 0;
    min-width: 130px;
    background: var(--strategy-surface-2);
  }

  .hot-history-matrix {
    max-height: 260px;
    overflow: auto;
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

  .market-amount-summary {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 14px;
    margin-bottom: 12px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .market-amount-summary strong {
    color: var(--strategy-text-1);
    font-size: 14px;
  }

  .market-amount-table {
    max-height: min(65vh, 680px);
    overflow: auto;
  }

  .market-amount-table thead th {
    position: sticky;
    z-index: 1;
    top: 0;
    background: var(--strategy-surface-2);
  }

  .market-amount-table .source-cell {
    max-width: 260px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .market-amount-deviation {
    font-variant-numeric: tabular-nums;
  }

  .market-amount-pagination {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 10px;
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  .market-amount-pagination button {
    padding: 4px 8px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  .market-amount-pagination button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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
    .fund-flow-layout {
      grid-template-columns: minmax(0, 1fr);
      height: auto;
    }

    .industry-flow-panel {
      height: var(--turnover-height);
    }

    .emotion-detail {
      grid-template-columns: minmax(0, 1fr);
    }

    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .rotation-grid {
      grid-template-columns: minmax(0, 1fr);
    }

    .history-charts {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 560px) {
    .ladder-trigger {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
    }

    .ladder-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .panel-title {
      flex-wrap: wrap;
    }

    .metric-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
