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
          ><ResearchSourceState
            v-if="!vibe?.sentiment && dashboard?.breadth"
            :meta="dashboard.breadth.meta"
        /></div>
        <p v-if="vibe?.sentiment" class="source-note"
          >vibe-research 实时聚合 · {{ formatDate(vibe.sentiment.date) }}</p
        >
        <div v-if="breadth" class="metric-grid"
          ><div v-for="item in breadthMetrics" :key="item.label" class="metric-cell"
            ><span>{{ item.label }}</span
            ><strong :class="item.tone">{{ item.value }}</strong
            ><small>{{ item.note }}</small></div
          ></div
        >
        <div v-if="latestHistory" class="overview-meta-grid">
          <div
            ><span>全A成交额</span
            ><strong>{{ formatHundredMillion(latestHistory.total_amount_100m) }}</strong></div
          >
          <button
            type="button"
            class="meta-action"
            :disabled="!hotMatrixRows.length"
            @click="hotMatrixOpen = true"
            ><span>百亿成交股</span
            ><strong>{{ hotStockCount == null ? '—' : `${hotStockCount}只` }}</strong></button
          >
          <div
            ><span>市场宽度</span
            ><strong>{{ formatPct(latestHistory.market_breadth, true) }}</strong></div
          >
        </div>
        <div v-if="!breadth" class="empty">暂无市场情绪数据</div>
      </article>
      <article class="metric-panel">
        <div class="panel-title"
          ><h3>短线情绪</h3
          ><ResearchSourceState
            v-if="!vibe?.emotion && dashboard?.emotion"
            :meta="dashboard.emotion.meta"
        /></div>
        <p v-if="vibe?.emotion" class="source-note"
          >vibe-research 实时聚合 · {{ vibe.emotion.date || '最新交易日' }}</p
        >
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
          <article class="emotion-subpanel emotion-summary-panel">
            <h4>连板股明细</h4>
            <p>{{
              emotionLeaders.length
                ? `共 ${emotionLeaders.length} 只，点击左侧连板梯队查看完整清单`
                : '暂无二板及以上个股'
            }}</p>
          </article>
        </div>
      </article>
    </div>
    <VibeTrendCharts v-if="allHistoryRows.length" :rows="allHistoryRows" />
    <article v-if="false && historyRows.length" class="panel history-panel">
      <div class="panel-title">
        <h3>市场涨跌结构与宽度</h3>
        <div class="history-actions" role="group" aria-label="历史范围">
          <button
            v-for="option in historyRangeOptions"
            :key="option.key"
            type="button"
            :class="{ active: historyRange === option.key }"
            @click="historyRange = option.key"
            >{{ option.label }}</button
          >
        </div>
      </div>
      <div class="history-charts">
        <div class="history-chart">
          <div class="chart-title"
            ><strong>市场涨跌结构</strong><span>上涨 / 下跌家数（家）</span></div
          >
          <svg viewBox="0 0 720 220" preserveAspectRatio="none" aria-label="市场涨跌结构历史图">
            <line
              v-for="tick in marketTicks"
              :key="`market-${tick}`"
              x1="44"
              :y1="chartY(tick, marketDomain)"
              x2="706"
              :y2="chartY(tick, marketDomain)"
              class="chart-grid"
            />
            <polyline
              :points="
                chartPoints(
                  historyRows.map((row) => row.advance),
                  marketDomain,
                )
              "
              class="chart-line chart-line--up"
            />
            <polyline
              :points="
                chartPoints(
                  historyRows.map((row) => row.decline),
                  marketDomain,
                )
              "
              class="chart-line chart-line--down"
            />
            <text x="44" y="211" class="chart-label">{{ historyRows[0]?.date?.slice(5) }}</text>
            <text x="706" y="211" text-anchor="end" class="chart-label">
              {{ historyRows.at(-1)?.date?.slice(5) }}
            </text>
          </svg>
          <div class="chart-legend"
            ><span><i class="legend-dot legend-dot--up"></i>上涨家数</span
            ><span><i class="legend-dot legend-dot--down"></i>下跌家数</span></div
          >
        </div>
        <div class="history-chart">
          <div class="chart-title"
            ><strong>市场宽度</strong><span>（上涨 − 下跌）/ 有效股票数</span></div
          >
          <svg viewBox="0 0 720 220" preserveAspectRatio="none" aria-label="市场宽度历史图">
            <line
              v-for="tick in breadthTicks"
              :key="`breadth-${tick}`"
              x1="44"
              :y1="chartY(tick, breadthDomain)"
              x2="706"
              :y2="chartY(tick, breadthDomain)"
              class="chart-grid"
            />
            <polyline
              :points="
                chartPoints(
                  historyRows.map((row) => row.market_breadth),
                  breadthDomain,
                )
              "
              class="chart-line chart-line--breadth"
            />
            <text x="44" y="211" class="chart-label">{{ historyRows[0]?.date?.slice(5) }}</text>
            <text x="706" y="211" text-anchor="end" class="chart-label">
              {{ historyRows.at(-1)?.date?.slice(5) }}
            </text>
          </svg>
          <div class="chart-legend"
            ><span><i class="legend-dot legend-dot--breadth"></i>市场宽度</span
            ><span>最新 {{ formatPct(historyRows.at(-1)?.market_breadth, true) }}</span></div
          >
        </div>
      </div>
    </article>
    <article v-if="false && hotMatrixRows.length" class="panel matrix-panel">
      <div class="panel-title"
        ><div><h3>百亿成交 · 行业分布</h3></div></div
      >
      <div class="table-shell matrix-shell">
        <table>
          <thead
            ><tr
              ><th class="is-left">行业</th
              ><th v-for="date in hotMatrixDates" :key="date">{{ date.slice(5) }}</th
              ><th>历史累计</th></tr
            ></thead
          >
          <tbody>
            <tr class="matrix-total"
              ><td class="is-left"><strong>合计</strong></td
              ><td v-for="(total, index) in hotMatrixTotals" :key="index">{{ total || '' }}</td
              ><td>{{ hotMatrixTotal }}</td></tr
            >
            <tr v-for="row in hotMatrixRows" :key="row.industry"
              ><td class="is-left"
                ><strong>{{ row.industry }}</strong></td
              ><td v-for="(count, index) in row.counts" :key="index">{{ count || '' }}</td
              ><td>{{ row.historyTotal }}</td></tr
            >
          </tbody>
        </table>
      </div>
    </article>
    <div class="overview-grid">
      <article class="panel">
        <div class="panel-title"
          ><div><h3>板块资金趋势榜</h3></div
          ><ResearchSourceState
            v-if="!vibe?.sectors?.length && dashboard?.shenwan"
            :meta="dashboard.shenwan.meta"
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
                ><th class="is-left">行业</th><th>涨跌%</th><th>今日净流入</th><th>流入</th
                ><th>流出</th><th>家数</th></tr
              ></thead
            ><tbody
              ><tr v-for="row in visibleSectorRows" :key="row.name"
                ><td class="is-left"
                  ><strong>{{ row.name }}</strong></td
                ><td :class="tone(row.pct)">{{ formatPct(row.pct) }}</td
                ><td :class="tone(row.net)">{{ formatYi(row.netYi) }}</td
                ><td>{{ formatYi(row.inflowYi) }}</td
                ><td>{{ formatYi(row.outflowYi) }}</td
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
        ><div><h3>全市场成交额榜</h3></div
        ><div class="turnover-actions"
          ><span class="top-count">Top {{ topN }}</span
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
      ><div v-else class="empty">暂无成交额榜数据</div></article
    >
    <div v-if="hotMatrixOpen" class="detail-modal-mask" @click.self="hotMatrixOpen = false">
      <article class="detail-modal panel matrix-panel">
        <div class="panel-title"
          ><h3>百亿成交 · 行业分布</h3
          ><button type="button" class="modal-close" @click="hotMatrixOpen = false"
            >关闭</button
          ></div
        >
        <div class="table-shell matrix-shell">
          <table
            ><thead
              ><tr
                ><th class="is-left">行业</th
                ><th v-for="date in hotMatrixDates" :key="date">{{ date.slice(5) }}</th
                ><th>历史累计</th></tr
              ></thead
            >
            <tbody
              ><tr class="matrix-total"
                ><td class="is-left"><strong>合计</strong></td
                ><td v-for="(total, index) in hotMatrixTotals" :key="index">{{ total || '' }}</td
                ><td>{{ hotMatrixTotal }}</td></tr
              >
              <tr v-for="row in hotMatrixRows" :key="row.industry"
                ><td class="is-left"
                  ><strong>{{ row.industry }}</strong></td
                ><td v-for="(count, index) in row.counts" :key="index">{{ count || '' }}</td
                ><td>{{ row.historyTotal }}</td></tr
              ></tbody
            >
          </table>
        </div>
      </article>
    </div>
    <div v-if="ladderOpen" class="detail-modal-mask" @click.self="ladderOpen = false">
      <article class="detail-modal panel">
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
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import type { AShareDashboardResponse } from '@/api/hedgeResearch';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';
  import VibeTrendCharts from './VibeTrendCharts.vue';

  const props = defineProps<{ dashboard: AShareDashboardResponse | null }>();
  const emit = defineEmits<{ (event: 'query', code: string): void }>();
  interface VibeSector {
    name: string;
    pct: number;
    net: number;
    inflow: number;
    outflow: number;
    firms?: number;
  }
  interface VibeLeader {
    code: string;
    name: string;
    boards: number;
    price?: number;
    pct?: number;
    amount?: number;
    float_cap?: number;
    industry?: string;
  }
  interface VibeOverview {
    updated?: string;
    sentiment?: {
      up: number;
      down: number;
      flat: number;
      zt: number;
      zt_real: number;
      dt: number;
      dt_real: number;
      active?: string | number;
      breadth?: string;
      speculation?: string;
      date?: string;
    };
    emotion?: {
      zt_count: number;
      dt_count: number;
      zb_count: number;
      max_boards: number;
      lianban_count: number;
      seal_rate?: number;
      break_rate?: number;
      promotion_rate?: number;
      date?: string;
      ladder?: Array<{ boards: number; count: number; plus?: boolean }>;
      lianban_stocks?: VibeLeader[];
    };
    sectors?: VibeSector[];
    turnover_top?: {
      stocks?: Array<{
        code: string;
        name: string;
        price?: number;
        pct?: number;
        amount: number;
        mcap?: number;
        industry?: string;
      }>;
    };
  }
  interface VibeMonitor {
    market_history?: Array<{
      date: string;
      advance?: number | null;
      decline?: number | null;
      flat?: number | null;
      limit_up?: number | null;
      limit_down?: number | null;
      effective_stocks?: number | null;
      total_amount_100m?: number | null;
      market_breadth?: number | null;
    }>;
    hot_stock_matrix?: {
      dates?: string[];
      rows?: Array<{ industry: string; counts: number[]; history_total: number }>;
    };
    hot_stocks_latest?: unknown[];
  }
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
  const vibe = ref<VibeOverview | null>(null);
  const vibeMonitor = ref<VibeMonitor | null>(null);
  const sectorsExpanded = ref(false);
  const topN = ref<10 | 20>(10);
  const ladderOpen = ref(false);
  const hotMatrixOpen = ref(false);
  const historyRange = ref<'recent' | '90' | 'all'>('recent');
  const historyRangeOptions = [
    { key: 'recent' as const, label: '近60日' },
    { key: '90' as const, label: '近90日' },
    { key: 'all' as const, label: '全部' },
  ];
  onMounted(async () => {
    const [overviewResponse, monitorResponse] = await Promise.allSettled([
      fetch('/vibe-research/api/market/overview-v2', { cache: 'no-store' }),
      fetch('/vibe-research/api/market-monitor', { cache: 'no-store' }),
    ]);
    if (overviewResponse.status === 'fulfilled' && overviewResponse.value.ok) {
      try {
        vibe.value =
          ((await overviewResponse.value.json()) as { data?: VibeOverview }).data || null;
      } catch {
        /* platform contract remains the fallback */
      }
    }
    if (monitorResponse.status === 'fulfilled' && monitorResponse.value.ok) {
      try {
        vibeMonitor.value =
          ((await monitorResponse.value.json()) as { data?: VibeMonitor }).data || null;
      } catch {
        /* historical charts remain explicitly absent */
      }
    }
  });
  const allHistoryRows = computed(() =>
    (vibeMonitor.value?.market_history || []).filter((row) => row.date),
  );
  const historyRows = computed(() => {
    const rows = allHistoryRows.value;
    if (historyRange.value === 'all') return rows;
    const size = historyRange.value === '90' ? 90 : 60;
    return rows.slice(Math.max(0, rows.length - size));
  });
  const marketDomain = computed<[number, number]>(() =>
    domainFor(historyRows.value.flatMap((row) => [row.advance, row.decline])),
  );
  const breadthDomain = computed<[number, number]>(() =>
    domainFor(
      historyRows.value.map((row) => row.market_breadth),
      true,
    ),
  );
  const chartTicks = [0, 0.25, 0.5, 0.75, 1];
  const marketTicks = computed(() => {
    const [min, max] = marketDomain.value;
    return chartTicks.map((fraction) => min + (max - min) * fraction);
  });
  const breadthTicks = [-1, -0.5, 0, 0.5, 1];
  const hotMatrixDates = computed(() => vibeMonitor.value?.hot_stock_matrix?.dates || []);
  const hotMatrixRows = computed(() => vibeMonitor.value?.hot_stock_matrix?.rows || []);
  const hotMatrixTotals = computed(() =>
    hotMatrixDates.value.map((_, index) =>
      hotMatrixRows.value.reduce((total, row) => total + Number(row.counts[index] || 0), 0),
    ),
  );
  const hotMatrixTotal = computed(() =>
    hotMatrixRows.value.reduce((total, row) => total + Number(row.history_total || 0), 0),
  );
  const latestHistory = computed(() => allHistoryRows.value.at(-1) || null);
  const hotStockCount = computed(() => vibeMonitor.value?.hot_stocks_latest?.length ?? null);
  const updatedAt = computed(() => vibe.value?.updated || props.dashboard?.generatedAt || '');
  const breadth = computed(() => {
    const v = vibe.value?.sentiment;
    if (v)
      return {
        up: v.up,
        down: v.down,
        flat: v.flat,
        limitUp: v.zt,
        realLimitUp: v.zt_real,
        limitDown: v.dt,
        realLimitDown: v.dt_real,
        activityPct: v.active,
        breadthState: v.breadth || '—',
        speculationState: v.speculation || '—',
        tradeDate: v.date,
      };
    return props.dashboard?.breadth.data || null;
  });
  const emotion = computed(() => {
    const v = vibe.value?.emotion;
    if (v)
      return {
        limitUpCount: v.zt_count,
        brokenBoardCount: v.zb_count,
        limitDownCount: v.dt_count,
        highestBoardCount: v.max_boards,
        consecutiveBoardCount: v.lianban_count,
        sealRatePct: v.seal_rate == null ? null : v.seal_rate * 100,
        breakRatePct: v.break_rate == null ? null : v.break_rate * 100,
        promotionRatePct: v.promotion_rate == null ? null : v.promotion_rate * 100,
        tradeDate: v.date,
        ladder: (v.ladder || []).map((r) => ({
          boardCount: `${r.boards}${r.plus ? '+' : ''}板`,
          stockCount: r.count,
        })),
        leaders: [],
      };
    return props.dashboard?.emotion.data || null;
  });
  const emotionLeaders = computed<EmotionLeader[]>(() => {
    const rows = vibe.value?.emotion?.lianban_stocks;
    if (rows?.length)
      return rows.map((r) => ({
        code: r.code,
        name: r.name,
        boards: r.boards,
        price: r.price,
        pct: r.pct,
        amountYi: r.amount == null ? null : r.amount / 1e8,
        floatCapYi: r.float_cap == null ? null : r.float_cap / 1e8,
        industry: r.industry,
      }));
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
  const sectorRows = computed<SectorRow[]>(() => {
    if (vibe.value?.sectors?.length)
      return vibe.value.sectors.map((r) => ({
        name: r.name,
        pct: r.pct,
        net: r.net,
        netYi: r.net,
        inflowYi: r.inflow,
        outflowYi: r.outflow,
        firms: r.firms ?? null,
      }));
    return (props.dashboard?.shenwan.data?.sw2All || []).map((r) => ({
      name: r.swL2Name,
      pct: Number(r.returnPct),
      net: r.netInflowYuan == null ? null : Number(r.netInflowYuan),
      netYi: r.netInflowYuan == null ? null : Number(r.netInflowYuan) / 1e8,
      inflowYi: null,
      outflowYi: null,
      firms: null,
    }));
  });
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
  const turnoverRows = computed<TurnoverRow[]>(() => {
    if (vibe.value?.turnover_top?.stocks?.length)
      return vibe.value.turnover_top.stocks.map((r) => ({
        securityCode: r.code,
        securityName: r.name,
        price: r.price,
        returnPct: r.pct,
        turnoverYi: r.amount == null ? null : r.amount / 1e8,
        marketCapYi: r.mcap == null ? null : r.mcap / 1e8,
        industry: r.industry,
      }));
    return (props.dashboard?.shenwan.data?.threshold?.stocks || [])
      .slice()
      .sort((a, b) => Number(b.turnoverYuan) - Number(a.turnoverYuan))
      .slice(0, 20)
      .map((r) => ({
        securityCode: r.securityCode,
        securityName: r.securityName,
        returnPct: r.returnPct,
        turnoverYi: r.turnoverYuan == null ? null : Number(r.turnoverYuan) / 1e8,
        marketCapYi: null,
        industry: r.swL2Name,
      }));
  });
  const breadthMetrics = computed(() => {
    const v = breadth.value;
    if (!v) return [];
    return [
      { label: '上涨', value: v.up, note: '当日上涨家数', tone: 'up' },
      { label: '下跌', value: v.down, note: '当日下跌家数', tone: 'down' },
      { label: '平盘', value: v.flat, note: '当日平盘家数', tone: '' },
      {
        label: '涨停 / 真实涨停',
        value: `${v.limitUp} / ${v.realLimitUp}`,
        note: '来源原始口径',
        tone: 'up',
      },
      {
        label: '跌停 / 真实跌停',
        value: `${v.limitDown} / ${v.realLimitDown}`,
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
  function domainFor(
    values: Array<number | null | undefined>,
    includeZero = false,
  ): [number, number] {
    const finite = values.map((value) => Number(value)).filter(Number.isFinite);
    if (!finite.length) return includeZero ? [-1, 1] : [0, 1];
    let min = Math.min(...finite);
    let max = Math.max(...finite);
    if (includeZero) {
      min = Math.min(0, min);
      max = Math.max(0, max);
    }
    if (min === max) {
      const padding = Math.max(1, Math.abs(min) * 0.1);
      return [min - padding, max + padding];
    }
    const padding = (max - min) * 0.08;
    return [min - padding, max + padding];
  }
  function chartY(value: number, domain: [number, number]) {
    const [min, max] = domain;
    return 18 + (1 - (value - min) / Math.max(max - min, 1e-9)) * 170;
  }
  function chartPoints(values: Array<number | null | undefined>, domain: [number, number]) {
    const last = Math.max(1, values.length - 1);
    return values
      .map((value, index) => {
        const n = numeric(value);
        return n == null ? null : `${44 + (index / last) * 662},${chartY(n, domain)}`;
      })
      .filter((point): point is string => point != null)
      .join(' ');
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
    display: grid;
    grid-template-columns: minmax(220px, 0.7fr) minmax(0, 1.3fr);
    gap: 12px;
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
    margin-bottom: 10px;
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
    gap: 10px;
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
    margin-top: 10px;
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

  .top-count {
    color: var(--strategy-text-4);
    font-size: 11px;
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
