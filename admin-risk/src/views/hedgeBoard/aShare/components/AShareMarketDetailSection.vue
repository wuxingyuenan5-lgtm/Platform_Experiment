<template>
  <section id="a-share-market-detail" class="research-card">
    <header class="research-card__header">
      <div>
        <p class="research-card__eyebrow">MARKET DETAIL</p>
        <h2>A股市场明细</h2>
      </div>
      <ResearchSourceState v-if="module" :meta="module.meta" />
    </header>

    <div v-if="rows.length" class="table-shell">
      <table class="market-table">
        <thead>
          <tr>
            <th class="is-left">名称 / 代码</th>
            <th>30日走势</th>
            <th class="is-right">收盘价</th>
            <th class="is-right">成交额</th>
            <th>20日波动率</th>
            <th>1D</th>
            <th>YTD</th>
            <th>QTD</th>
            <th>1周</th>
            <th>1月</th>
            <th>1年</th>
            <th>52周高</th>
            <th>1H</th>
            <th>日线</th>
            <th>3日线</th>
            <th>周线</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.code">
            <td class="name-cell">
              <strong>{{ row.name }}</strong>
              <span>{{ row.code }}</span>
            </td>
            <td class="spark-cell">
              <svg viewBox="0 0 96 26" preserveAspectRatio="none">
                <polyline :points="sparkPoints(row.spark)" :class="toneClass(row.return1dPct)" />
              </svg>
            </td>
            <td class="is-right">{{ formatNumber(row.close, 2) }}</td>
            <td class="is-right">{{ formatMoney(row.turnoverYuan) }}</td>
            <td><span :class="toneClass(row.volatility20Pct, true)">{{ formatPct(row.volatility20Pct) }}</span></td>
            <td><span :class="toneClass(row.return1dPct)">{{ formatPct(row.return1dPct) }}</span></td>
            <td><span :class="toneClass(row.returnYtdPct)">{{ formatPct(row.returnYtdPct) }}</span></td>
            <td><span :class="toneClass(row.returnQtdPct)">{{ formatPct(row.returnQtdPct) }}</span></td>
            <td><span :class="toneClass(row.return1wPct)">{{ formatPct(row.return1wPct) }}</span></td>
            <td><span :class="toneClass(row.return1mPct)">{{ formatPct(row.return1mPct) }}</span></td>
            <td><span :class="toneClass(row.return1yPct)">{{ formatPct(row.return1yPct) }}</span></td>
            <td><span :class="toneClass(row.distance52wHighPct)">{{ formatPct(row.distance52wHighPct) }}</span></td>
            <td :class="signalClass(row.signal1h)">{{ row.signal1h || '—' }}</td>
            <td :class="signalClass(row.signalDaily)">{{ row.signalDaily || '—' }}</td>
            <td :class="signalClass(row.signal3d)">{{ row.signal3d || '—' }}</td>
            <td :class="signalClass(row.signalWeekly)">{{ row.signalWeekly || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="research-empty">{{ module?.meta.message || '暂无指数明细数据' }}</div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { AShareIndexSnapshot, ResearchModuleResult } from '@/api/hedgeResearch';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';

  const props = defineProps<{ module?: ResearchModuleResult<AShareIndexSnapshot[]> | null }>();
  const rows = computed(() => props.module?.data || []);

  function numeric(value: string | number | null | undefined) {
    const result = Number(value);
    return Number.isFinite(result) ? result : null;
  }

  function formatNumber(value: string | number | null | undefined, digits = 2) {
    const result = numeric(value);
    return result == null ? '—' : result.toLocaleString('zh-CN', { maximumFractionDigits: digits });
  }

  function formatMoney(value: string | number | null | undefined) {
    const result = numeric(value);
    if (result == null) return '—';
    if (Math.abs(result) >= 1_000_000_000_000) return `${(result / 1_000_000_000_000).toFixed(2)}万亿`;
    if (Math.abs(result) >= 100_000_000) return `${(result / 100_000_000).toFixed(2)}亿`;
    if (Math.abs(result) >= 10_000) return `${(result / 10_000).toFixed(2)}万`;
    return result.toLocaleString('zh-CN');
  }

  function formatPct(value: string | number | null | undefined) {
    const result = numeric(value);
    if (result == null) return '—';
    return `${result > 0 ? '+' : ''}${result.toFixed(2)}%`;
  }

  function toneClass(value: string | number | null | undefined, neutralPositive = false) {
    const result = numeric(value);
    if (result == null) return '';
    if (neutralPositive) return 'is-neutral';
    return result > 0 ? 'is-positive' : result < 0 ? 'is-negative' : '';
  }

  function signalClass(value: string | null | undefined) {
    return value === '▲' ? 'is-positive' : value === '▼' ? 'is-negative' : '';
  }

  function sparkPoints(values: Array<string | number>) {
    const series = values.map(Number).filter(Number.isFinite);
    if (!series.length) return '';
    const min = Math.min(...series);
    const max = Math.max(...series);
    const range = max - min || 1;
    return series
      .map((value, index) => {
        const x = (index / Math.max(series.length - 1, 1)) * 96;
        const y = 24 - ((value - min) / range) * 20;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
  }
</script>

<style scoped lang="less">
  .research-card { padding: 18px; border: 1px solid var(--strategy-border); border-radius: var(--strategy-radius-card); background: var(--strategy-surface); box-shadow: var(--strategy-shadow-soft); }
  .research-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
  .research-card__eyebrow { margin: 0 0 3px; color: var(--strategy-text-4); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
  h2 { margin: 0; color: var(--strategy-text-1); font-size: 18px; }
  .table-shell { overflow-x: auto; border: 1px solid var(--strategy-border); border-radius: 12px; }
  .market-table { width: 100%; min-width: 1540px; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { padding: 11px 10px; border-bottom: 1px solid var(--strategy-border); color: var(--strategy-text-2); text-align: center; white-space: nowrap; }
  th { position: sticky; top: 0; z-index: 1; background: var(--strategy-surface-2); color: var(--strategy-text-3); font-size: 12px; }
  tbody tr:last-child td { border-bottom: 0; }
  tbody tr:hover { background: var(--strategy-accent-soft); }
  .is-left, .name-cell { text-align: left; }
  .is-right { text-align: right; }
  .name-cell strong, .name-cell span { display: block; }
  .name-cell strong { color: var(--strategy-text-1); }
  .name-cell span { margin-top: 3px; color: var(--strategy-text-4); font-size: 12px; }
  .spark-cell svg { width: 96px; height: 26px; }
  .spark-cell polyline { fill: none; stroke: #64748b; stroke-width: 2; vector-effect: non-scaling-stroke; }
  .spark-cell polyline.is-positive { stroke: var(--strategy-up, #ef4444); }
  .spark-cell polyline.is-negative { stroke: var(--strategy-down, #10b981); }
  .is-positive { color: var(--strategy-up, #ef4444) !important; font-weight: 700; }
  .is-negative { color: var(--strategy-down, #10b981) !important; font-weight: 700; }
  .is-neutral { color: var(--strategy-text-2); }
  .research-empty { padding: 30px; color: var(--strategy-text-3); text-align: center; }
  @media (max-width: 640px) { .research-card__header { flex-direction: column; } }
</style>
