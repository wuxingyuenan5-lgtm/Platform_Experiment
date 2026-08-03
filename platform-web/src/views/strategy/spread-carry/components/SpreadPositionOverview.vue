<template>
  <section class="cross-card cross-card--overview">
    <div class="card-head">
      <div class="overview-title">
        <h3>价差持仓总览</h3>
      </div>
    </div>

    <div v-if="overviewRows.length" class="overview-range">
      <div class="overview-range__meta">
        <span class="green">多 50.03%</span>
        <span class="red">49.97% 空</span>
      </div>
      <div class="overview-range__track">
        <div class="overview-range__green" style="width: 50.03%"></div>
        <div class="overview-range__red" style="width: 49.97%"></div>
      </div>
    </div>

    <div v-if="overviewRows.length" class="overview-summary overview-summary--top">
      <div class="overview-summary__item">
        <span>双边总损益</span>
        <strong class="green">-21.00</strong>
      </div>
      <div class="overview-summary__item">
        <span>单边总损益</span>
        <strong class="green">BY: -10 | MT5: -11</strong>
      </div>
      <div class="overview-summary__item">
        <span>单边爆仓价</span>
        <strong class="red">BY: 2,285 | MT5: 2,382</strong>
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
          <th>账户 / 状态</th>
          <th>权益 / 可用</th>
          <th>未实现PnL (USDT)</th>
          <th>单边盈亏</th>
          <th>止盈价差</th>
          <th>止损价差</th>
          <th>爆仓价</th>
          <th>占用保证金</th>
          <th>开仓时间</th>
          <th>持仓时长</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="overviewRows.length === 0">
          <td colspan="16">{{ emptyText }}</td>
        </tr>
        <tr v-for="row in overviewRows" :key="row.id">
          <td :class="row.direction === '多头' ? 'green' : 'red'">{{ row.direction }}</td>
          <td>{{ formatNumber(row.qty, 2) }}</td>
          <td>{{ row.entrySpread }}</td>
          <td :class="spreadTone(longSpread)">{{ row.currentSpread }}</td>
          <td>{{ row.detail }}</td>
          <td>{{ row.accountStatus }}</td>
          <td>{{ row.accountRisk }}</td>
          <td>{{ row.pnl }}</td>
          <td>{{ row.legPnl }}</td>
          <td>{{ row.takeProfit }}</td>
          <td>{{ row.stopLoss }}</td>
          <td>{{ row.liquidation }}</td>
          <td>{{ row.margin }}</td>
          <td>{{ row.openTime }}</td>
          <td>{{ row.holdingTime }}</td>
          <td>{{ row.status }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<script setup lang="ts">
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

  defineProps<{
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

  function spreadTone(value: string | number | null | undefined) {
    const parsed = parseOptionalNumber(value);
    if (parsed === null) return '';
    return parsed <= 0 ? 'green' : 'red';
  }
</script>

<style scoped lang="less">
  .cross-card {
    padding: 16px 18px 18px;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .cross-card--overview {
    padding-bottom: 14px;
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
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
    position: relative;
    display: flex;
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
    width: 100%;
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

  @media (max-width: 960px) {
    .overview-table {
      display: block;
      overflow-x: auto;
    }
  }
</style>
