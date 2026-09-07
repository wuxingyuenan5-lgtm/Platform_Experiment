<template>
  <section id="a-share-market-overview" class="overview-card">
    <header class="overview-header">
      <div>
        <p class="eyebrow">MARKET OVERVIEW</p>
        <h2>A股市场总览</h2>
      </div>
      <span class="updated" v-if="dashboard?.generatedAt">
        更新于 {{ formatDate(dashboard.generatedAt) }}
      </span>
    </header>

    <div class="overview-grid">
      <article class="metric-panel">
        <div class="panel-title"
          ><h3>市场情绪</h3
          ><ResearchSourceState v-if="dashboard?.breadth" :meta="dashboard.breadth.meta"
        /></div>
        <div v-if="breadth" class="metric-grid">
          <div v-for="item in breadthMetrics" :key="item.label" class="metric-cell">
            <span>{{ item.label }}</span
            ><strong :class="item.tone">{{ item.value }}</strong
            ><small>{{ item.note }}</small>
          </div>
        </div>
        <div v-else class="empty">暂无市场情绪数据</div>
      </article>

      <article class="metric-panel">
        <div class="panel-title"
          ><h3>短线情绪</h3
          ><ResearchSourceState v-if="dashboard?.emotion" :meta="dashboard.emotion.meta"
        /></div>
        <div v-if="emotion" class="metric-grid">
          <div v-for="item in emotionMetrics" :key="item.label" class="metric-cell">
            <span>{{ item.label }}</span
            ><strong :class="item.tone">{{ item.value }}</strong
            ><small>{{ item.note }}</small>
          </div>
        </div>
        <div v-else class="empty">暂无短线情绪数据</div>
      </article>
    </div>

    <div class="overview-grid">
      <article class="panel">
        <div class="panel-title"
          ><div><h3>板块资金趋势榜</h3></div
          ><ResearchSourceState v-if="dashboard?.shenwan" :meta="dashboard.shenwan.meta"
        /></div>
        <div v-if="topSectors.length" class="sector-list">
          <div v-for="row in topSectors" :key="row.swL2Code" class="sector-row"
            ><span class="rank">{{ row.rank }}</span
            ><div class="sector-name"
              ><strong>{{ row.swL2Name }}</strong
              ><small>{{ row.swL1Name }}</small></div
            ><b :class="tone(row.returnPct)">{{ formatPct(row.returnPct) }}</b
            ><span class="money">{{ formatMoney(row.turnoverYuan) }}</span></div
          >
        </div>
        <div v-else class="empty">暂无板块资金数据</div>
      </article>
      <article class="panel">
        <div class="panel-title"
          ><div><h3>资金轮动</h3></div></div
        >
        <div v-if="rotationRows.length" class="sector-list">
          <div v-for="row in rotationRows" :key="row.swL2Code" class="sector-row"
            ><span class="rank">{{
              row.netInflowYuan != null && Number(row.netInflowYuan) >= 0 ? '流入' : '流出'
            }}</span
            ><div class="sector-name"
              ><strong>{{ row.swL2Name }}</strong
              ><small>{{ row.swL1Name }}</small></div
            ><b :class="tone(row.netInflowYuan)">{{ formatMoney(row.netInflowYuan) }}</b></div
          >
        </div>
        <div v-else class="empty">暂无资金轮动数据</div>
      </article>
    </div>

    <article class="panel wide-panel">
      <div class="panel-title"
        ><div><h3>全市场成交额榜</h3></div></div
      >
      <div v-if="turnoverRows.length" class="turnover-grid"
        ><div v-for="row in turnoverRows" :key="row.securityCode" class="turnover-row"
          ><span
            >{{ row.securityName }}<small>{{ row.securityCode }}</small></span
          ><b>{{ formatMoney(row.turnoverYuan) }}</b
          ><em :class="tone(row.returnPct)">{{ formatPct(row.returnPct) }}</em></div
        ></div
      >
      <div v-else class="empty">暂无成交额榜数据</div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { AShareDashboardResponse } from '@/api/hedgeResearch';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';

  const props = defineProps<{ dashboard: AShareDashboardResponse | null }>();
  defineEmits<{ (event: 'open-chart', code: string, name: string): void }>();
  const breadth = computed(() => props.dashboard?.breadth.data || null);
  const emotion = computed(() => props.dashboard?.emotion.data || null);
  const topSectors = computed(() => props.dashboard?.shenwan.data?.sw2Top?.slice(0, 7) || []);
  const rotationRows = computed(
    () =>
      props.dashboard?.shenwan.data?.sw2All
        ?.filter((row) => row.netInflowYuan != null)
        .sort((a, b) => Math.abs(Number(b.netInflowYuan)) - Math.abs(Number(a.netInflowYuan)))
        .slice(0, 8) || [],
  );
  const turnoverRows = computed(
    () =>
      props.dashboard?.shenwan.data?.threshold?.stocks
        ?.slice()
        .sort((a, b) => Number(b.turnoverYuan) - Number(a.turnoverYuan))
        .slice(0, 10) || [],
  );
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
        value: v.activityPct == null ? '—' : `${v.activityPct}%`,
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
        value: formatPct(v.sealRatePct),
        note: '涨停 /（涨停＋炸板）',
        tone: 'up',
      },
      {
        label: '炸板率',
        value: formatPct(v.breakRatePct),
        note: '炸板 /（涨停＋炸板）',
        tone: 'down',
      },
      {
        label: '晋级率',
        value: formatPct(v.promotionRatePct),
        note: '今日二板+ / 昨日涨停',
        tone: '',
      },
    ];
  });
  function numeric(value: unknown) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }
  function formatPct(value: unknown) {
    const n = numeric(value);
    return n == null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(2)}%`;
  }
  function formatMoney(value: unknown) {
    const n = numeric(value);
    if (n == null) return '—';
    if (Math.abs(n) >= 100_000_000) return `${(n / 100_000_000).toFixed(2)}亿`;
    if (Math.abs(n) >= 10_000) return `${(n / 10_000).toFixed(2)}万`;
    return n.toLocaleString('zh-CN');
  }
  function tone(value: unknown) {
    const n = numeric(value);
    return n == null ? '' : n > 0 ? 'up' : n < 0 ? 'down' : '';
  }
  function formatDate(value: string) {
    return new Date(value).toLocaleString('zh-CN', { hour12: false });
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
  .panel-title p {
    margin: 0;
    color: var(--strategy-text-4);
    font-size: 12px;
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

  .up {
    color: var(--strategy-up, #ef4444) !important;
  }

  .down {
    color: var(--strategy-down, #10b981) !important;
  }

  .wide-panel {
    display: grid;
    gap: 12px;
  }

  .sector-list {
    display: grid;
    margin-top: 10px;
  }

  .sector-row,
  .turnover-row {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr) auto auto;
    align-items: center;
    gap: 8px;
    padding: 9px 0;
    border-bottom: 1px solid var(--strategy-border);
  }

  .sector-row:last-child,
  .turnover-row:last-child {
    border-bottom: 0;
  }

  .rank {
    color: var(--strategy-text-4);
    font-size: 11px;
  }

  .sector-name strong,
  .sector-name small,
  .turnover-row span,
  .turnover-row small {
    display: block;
  }

  .sector-name small,
  .turnover-row small {
    margin-top: 2px;
    color: var(--strategy-text-4);
    font-size: 11px;
  }

  .sector-row b,
  .turnover-row b,
  .turnover-row em {
    font-size: 12px;
    font-style: normal;
  }

  .money {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .turnover-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 18px;
  }

  .empty {
    padding: 24px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  .metric-panel :deep(.research-source-state),
  .panel :deep(.research-source-state) {
    white-space: nowrap;
  }

  @media (max-width: 900px) {
    .overview-grid {
      grid-template-columns: 1fr;
    }

    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .turnover-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 560px) {
    .metric-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
