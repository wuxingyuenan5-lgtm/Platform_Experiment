<template>
  <section id="a-share-emotion" class="research-card">
    <header class="research-card__header">
      <div>
        <p class="research-card__eyebrow">SHORT-TERM SENTIMENT</p>
        <h2>短线情绪</h2>
      </div>
      <ResearchSourceState v-if="module" :meta="module.meta" />
    </header>

    <template v-if="data">
      <div class="emotion-metrics">
        <article v-for="item in metrics" :key="item.label">
          <span>{{ item.label }}</span>
          <strong :class="item.tone">{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </article>
      </div>

      <div class="emotion-layout">
        <article class="emotion-panel">
          <h3>连板梯队</h3>
          <div class="ladder-list">
            <div v-for="row in data.ladder" :key="row.boardCount">
              <span>{{ row.boardCount }}</span>
              <div class="ladder-track"><i :style="{ width: ladderWidth(row.stockCount) }" /></div>
              <strong>{{ row.stockCount }}</strong>
            </div>
          </div>
        </article>

        <article class="emotion-panel emotion-panel--table">
          <h3>连板股明细</h3>
          <div class="table-shell">
            <table>
              <thead><tr><th class="is-left">名称 / 代码</th><th>连板</th><th class="is-right">成交额</th></tr></thead>
              <tbody>
                <tr v-for="row in data.leaders" :key="row.securityCode">
                  <td class="is-left"><strong>{{ row.securityName }}</strong><small>{{ row.securityCode }}</small></td>
                  <td>{{ row.boardCount }}板</td>
                  <td class="is-right">{{ formatMoney(row.turnoverYuan) }}</td>
                </tr>
                <tr v-if="!data.leaders.length"><td colspan="3" class="empty-cell">暂无二板及以上个股</td></tr>
              </tbody>
            </table>
          </div>
        </article>
      </div>
    </template>
    <div v-else class="research-empty">{{ module?.meta.message || '暂无短线情绪数据' }}</div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { ResearchModuleResult, ShortTermEmotionSnapshot } from '@/api/hedgeResearch';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';

  const props = defineProps<{ module?: ResearchModuleResult<ShortTermEmotionSnapshot> | null }>();
  const data = computed(() => props.module?.data || null);

  const metrics = computed(() => {
    const value = data.value;
    if (!value) return [];
    return [
      { label: '涨停', value: value.limitUpCount, note: value.tradeDate || '最新交易日', tone: 'is-positive' },
      { label: '炸板', value: value.brokenBoardCount, note: '触板后未封住', tone: 'is-negative' },
      { label: '跌停', value: value.limitDownCount, note: '当日跌停池', tone: 'is-negative' },
      { label: '最高连板', value: `${value.highestBoardCount}板`, note: '涨停池最高 lbc', tone: '' },
      { label: '二板及以上', value: value.consecutiveBoardCount, note: '当日连板股数量', tone: '' },
      { label: '封板率', value: formatPct(value.sealRatePct), note: '涨停 /（涨停＋炸板）', tone: 'is-positive' },
      { label: '炸板率', value: formatPct(value.breakRatePct), note: '炸板 /（涨停＋炸板）', tone: 'is-negative' },
      { label: '晋级率', value: formatPct(value.promotionRatePct), note: '今日二板+ / 昨日涨停', tone: '' },
    ];
  });

  const maxLadderCount = computed(() => Math.max(1, ...(data.value?.ladder || []).map((row) => row.stockCount)));

  function ladderWidth(count: number) {
    return `${Math.max(4, (count / maxLadderCount.value) * 100)}%`;
  }

  function numeric(value: string | number | null | undefined) {
    const result = Number(value);
    return Number.isFinite(result) ? result : null;
  }

  function formatPct(value: string | number | null | undefined) {
    const result = numeric(value);
    return result == null ? '—' : `${result.toFixed(2)}%`;
  }

  function formatMoney(value: string | number | null | undefined) {
    const result = numeric(value);
    if (result == null) return '—';
    if (Math.abs(result) >= 100_000_000) return `${(result / 100_000_000).toFixed(2)}亿`;
    if (Math.abs(result) >= 10_000) return `${(result / 10_000).toFixed(2)}万`;
    return result.toLocaleString('zh-CN');
  }
</script>

<style scoped lang="less">
  .research-card { padding: 18px; border: 1px solid var(--strategy-border); border-radius: var(--strategy-radius-card); background: var(--strategy-surface); box-shadow: var(--strategy-shadow-soft); }
  .research-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
  .research-card__eyebrow { margin: 0 0 3px; color: var(--strategy-text-4); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
  h2, h3 { margin: 0; color: var(--strategy-text-1); }
  h2 { font-size: 18px; }
  h3 { margin-bottom: 12px; font-size: 15px; }
  .emotion-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
  .emotion-metrics article { padding: 13px; border: 1px solid var(--strategy-border); border-radius: 11px; background: var(--strategy-surface-2); }
  .emotion-metrics span, .emotion-metrics small { display: block; color: var(--strategy-text-3); }
  .emotion-metrics strong { display: block; margin: 7px 0 3px; color: var(--strategy-text-1); font-size: 21px; font-variant-numeric: tabular-nums; }
  .emotion-layout { display: grid; grid-template-columns: minmax(280px, .75fr) minmax(0, 1.25fr); gap: 14px; margin-top: 14px; }
  .emotion-panel { padding: 15px; border: 1px solid var(--strategy-border); border-radius: 12px; background: var(--strategy-surface-2); }
  .ladder-list { display: grid; gap: 12px; }
  .ladder-list > div { display: grid; grid-template-columns: 44px minmax(0, 1fr) 34px; align-items: center; gap: 9px; color: var(--strategy-text-2); }
  .ladder-track { height: 7px; overflow: hidden; border-radius: 999px; background: var(--strategy-border); }
  .ladder-track i { display: block; height: 100%; border-radius: inherit; background: var(--strategy-accent-strong); }
  .table-shell { overflow-x: auto; border: 1px solid var(--strategy-border); border-radius: 10px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 10px; border-bottom: 1px solid var(--strategy-border); color: var(--strategy-text-2); text-align: center; }
  th { background: var(--strategy-surface); color: var(--strategy-text-3); font-size: 12px; }
  tbody tr:last-child td { border-bottom: 0; }
  td strong, td small { display: block; }
  td small { margin-top: 2px; color: var(--strategy-text-4); }
  .is-left { text-align: left; }
  .is-right { text-align: right; }
  .is-positive { color: var(--strategy-up, #ef4444) !important; }
  .is-negative { color: var(--strategy-down, #10b981) !important; }
  .empty-cell, .research-empty { padding: 30px; color: var(--strategy-text-3); text-align: center; }
  @media (max-width: 1050px) { .emotion-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .emotion-layout { grid-template-columns: 1fr; } }
  @media (max-width: 640px) { .research-card__header { flex-direction: column; } .emotion-metrics { grid-template-columns: 1fr; } }
</style>
