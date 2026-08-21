<template>
  <section class="cross-card cross-card--overview">
    <div class="card-head">
      <div class="overview-title">
        <h3>价差持仓总览</h3>
      </div>
    </div>

    <div v-if="overviewRows.length" class="overview-range">
      <div class="overview-range__meta">
        <span class="green">多 {{ formatPercent(longExposureRatio) }}</span>
        <span class="red">{{ formatPercent(shortExposureRatio) }} 空</span>
      </div>
      <div class="overview-range__track">
        <div
          class="overview-range__green"
          :style="{ width: formatPercent(longExposureRatio) }"
        ></div>
        <div
          class="overview-range__red"
          :style="{ width: formatPercent(shortExposureRatio) }"
        ></div>
      </div>
    </div>

    <div v-if="overviewRows.length" class="overview-summary overview-summary--top">
      <div class="overview-summary__item">
        <span>双边总损益</span>
        <strong :class="totalPnlTone">{{ formatSignedNumber(totalPnlUsdt) }} USDT</strong>
      </div>
      <div class="overview-summary__item">
        <span>单边总损益</span>
        <strong :class="legPnlTone"
          >BY: {{ formatSignedNumber(legPnlByUsdt) }} | MT5:
          {{ formatSignedNumber(legPnlMt5Usdt) }}</strong
        >
      </div>
      <div class="overview-summary__item">
        <span>单边爆仓价</span>
        <strong class="red">BY: {{ liquidationByText }} | MT5: {{ liquidationMt5Text }}</strong>
      </div>
    </div>

    <table class="overview-table">
      <thead>
        <tr>
          <th>方向</th>
          <th>盎司</th>
          <th>持仓价差（滑点）</th>
          <th>当前价差</th>
          <th>开仓明细</th>
          <th>未实现PnL (USDT)</th>
          <th>单边盈亏</th>
          <th>止盈价差</th>
          <th>止损价差</th>
          <th>爆仓价</th>
          <th>占用保证金</th>
          <th>开仓时间</th>
          <th>权益 / 可用</th>
          <th>持仓时长</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="overviewRows.length === 0">
          <td colspan="15">{{ emptyText }}</td>
        </tr>
        <tr v-for="row in overviewRows" :key="row.id">
          <td :class="row.direction === '多头' ? 'green' : 'red'">{{ row.direction }}</td>
          <td>{{ formatNumber(row.qty, 2) }}</td>
          <td>{{ row.entrySpread }}</td>
          <td :class="spreadTone(longSpread)">{{ row.currentSpread }}</td>
          <td>{{ row.detail }}</td>
          <td>{{ row.pnl }}</td>
          <td>{{ row.legPnl }}</td>
          <td>{{ row.takeProfit }}</td>
          <td>{{ row.stopLoss }}</td>
          <td>{{ row.liquidation }}</td>
          <td>{{ row.margin }}</td>
          <td>{{ row.openTime }}</td>
          <td>{{ row.accountRisk }}</td>
          <td>{{ row.holdingTime }}</td>
          <td>{{ row.status }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  interface OverviewRow {
    id: string;
    direction: string;
    qty: number;
    entrySpread: string;
    currentSpread: string;
    detail: string;
    accountStatus: string;
    accountRisk: string;
    pnl: string;
    legPnl: string;
    takeProfit: string;
    stopLoss: string;
    liquidation: string;
    margin: string;
    openTime: string;
    holdingTime: string;
    status: string;
  }

  const props = defineProps<{
    overviewRows: OverviewRow[];
    emptyText: string;
    longSpread: string | number | null | undefined;
  }>();

  function parseOptionalNumber(value: string | number | null | undefined) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatNumber(value: number, digits = 2) {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function formatSignedNumber(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return '--';
    return formatNumber(value, 2);
  }

  function parseLegPart(text: string, prefix: 'BY' | 'MT5'): number | null {
    if (!text) return null;
    const parts = text.split(' | ');
    for (const part of parts) {
      const t = part.trim();
      if (t.startsWith(prefix + ': ')) {
        const num = parseFloat(t.slice((prefix + ': ').length).replace(/,/g, ''));
        return Number.isFinite(num) ? num : null;
      }
    }
    return null;
  }

  function extractLegText(text: string, prefix: 'BY' | 'MT5'): string {
    if (!text) return '--';
    const parts = text.split(' | ');
    for (const part of parts) {
      const t = part.trim();
      if (t.startsWith(prefix + ': ')) return t.slice((prefix + ': ').length);
    }
    return '--';
  }

  const totalPnlUsdt = computed<number | null>(() => {
    let sum = 0;
    let hasAny = false;
    for (const row of props.overviewRows) {
      const v = parseOptionalNumber(row.pnl);
      if (v !== null) {
        sum += v;
        hasAny = true;
      }
    }
    return hasAny ? sum : null;
  });

  const legPnlByUsdt = computed<number | null>(() => {
    let sum = 0;
    let hasAny = false;
    for (const row of props.overviewRows) {
      const v = parseLegPart(row.legPnl, 'BY');
      if (v !== null) {
        sum += v;
        hasAny = true;
      }
    }
    return hasAny ? sum : null;
  });

  const legPnlMt5Usdt = computed<number | null>(() => {
    let sum = 0;
    let hasAny = false;
    for (const row of props.overviewRows) {
      const v = parseLegPart(row.legPnl, 'MT5');
      if (v !== null) {
        sum += v;
        hasAny = true;
      }
    }
    return hasAny ? sum : null;
  });

  const liquidationByText = computed<string>(() => {
    const row = props.overviewRows[0];
    return row ? extractLegText(row.liquidation, 'BY') : '--';
  });

  const liquidationMt5Text = computed<string>(() => {
    const row = props.overviewRows[0];
    return row ? extractLegText(row.liquidation, 'MT5') : '--';
  });

  const totalPnlTone = computed<string>(() => {
    const v = totalPnlUsdt.value;
    if (v === null) return '';
    return v >= 0 ? 'green' : 'red';
  });

  const legPnlTone = computed<string>(() => {
    const by = legPnlByUsdt.value ?? 0;
    const mt5 = legPnlMt5Usdt.value ?? 0;
    if (legPnlByUsdt.value === null && legPnlMt5Usdt.value === null) return '';
    return by >= 0 || mt5 >= 0 ? 'green' : 'red';
  });

  function spreadTone(value: string | number | null | undefined) {
    const parsed = parseOptionalNumber(value);
    if (parsed === null) return '';
    return parsed <= 0 ? 'green' : 'red';
  }

  const totalExposure = computed(() =>
    props.overviewRows.reduce((sum, row) => sum + Math.max(row.qty, 0), 0),
  );

  const longExposure = computed(() =>
    props.overviewRows.reduce(
      (sum, row) => sum + (row.direction === '多头' ? Math.max(row.qty, 0) : 0),
      0,
    ),
  );

  const longExposureRatio = computed(() => {
    if (!totalExposure.value) return 0;
    return (longExposure.value / totalExposure.value) * 100;
  });

  const shortExposureRatio = computed(() => {
    if (!totalExposure.value) return 0;
    return 100 - longExposureRatio.value;
  });

  function formatPercent(value: number) {
    return `${Math.max(0, Math.min(100, value)).toFixed(2)}%`;
  }
</script>

<style scoped lang="less">
  .cross-card {
    padding: 16px 18px 18px;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #fff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgb(94 109 133 / 4%);
  }

  .cross-card--overview {
    padding-bottom: 14px;
  }

  .card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .overview-title {
    display: flex;
    align-items: center;
  }

  .overview-title h3 {
    color: #162845;
    font-size: 21px;
    font-weight: 800;
  }

  .overview-range {
    display: grid;
    gap: 6px;
    max-width: 540px;
    margin-bottom: 12px;
  }

  .overview-range__meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    font-weight: 800;
    line-height: 1;
  }

  .overview-range__track {
    display: flex;
    position: relative;
    height: 6px;
    overflow: hidden;
    border-radius: 999px;
    background: #eef2f8;
  }

  .overview-range__green {
    height: 100%;
    background: linear-gradient(90deg, #19a34b 0%, #16b257 100%);
  }

  .overview-range__red {
    height: 100%;
    background: linear-gradient(90deg, #ff6868 0%, #ff3d3d 100%);
  }

  .overview-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid #edf2f8;
  }

  .overview-summary--top {
    margin-bottom: 12px;
  }

  .overview-summary__item {
    display: flex;
    align-items: baseline;
    gap: 10px;
    min-width: 0;
  }

  .overview-summary__item span {
    color: #61728e;
    font-size: 24px;
    font-weight: 600;
    line-height: 1.1;
    white-space: nowrap;
  }

  .overview-summary__item strong {
    font-size: 24px;
    font-weight: 600;
    line-height: 1.1;
    white-space: nowrap;
  }

  .overview-table {
    display: block;
    width: 100%;
    max-width: 100%;
    overflow-x: auto;
    border-collapse: collapse;
  }

  .overview-table th,
  .overview-table td {
    padding: 13px 10px;
    border-bottom: 1px solid #d8e2ec;
    font-size: 13px;
    text-align: left;
    white-space: nowrap;
  }

  .overview-table th {
    color: #2f3640;
    font-size: 14px;
    font-weight: 800;
  }

  .overview-table td {
    color: #22324d;
    font-family: var(--strategy-font-data);
    font-size: 13px;
    font-weight: 500;
  }

  .green {
    color: #179b4b !important;
  }

  .red {
    color: #ef3232 !important;
  }

  @media (max-width: 1480px) {
    .overview-summary {
      grid-template-columns: 1fr;
      flex-direction: column;
    }
  }
</style>
