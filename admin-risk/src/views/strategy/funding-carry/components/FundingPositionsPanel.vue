<template>
  <section class="panel positions-panel">
    <div class="panel-title">
      <h3>当前持仓总览</h3>
    </div>

    <div class="positions-metrics">
      <div class="positions-metric"
        ><span>累计资金费收益</span><strong class="green">+1,156.60 USDT</strong></div
      >
      <div class="positions-metric"
        ><span>未实现盈亏</span><strong class="green">+1,036.20 USDT</strong></div
      >
      <div class="positions-metric"
        ><span>当前基差 (现货-永续)</span><strong class="green">+10.5 USDT (+0.0102%)</strong></div
      >
      <div class="positions-metric"><span>保证金率</span><strong class="green">35.00%</strong></div>
      <div class="positions-metric"><span>Delta 偏离</span><strong>0.00%</strong></div>
      <div class="positions-metric"><span>强平距离</span><strong class="green">28.00%</strong></div>
    </div>

    <div class="positions-table-wrap">
      <table class="positions-table">
        <thead>
          <tr>
            <th>组合 / 方向</th>
            <th>交易所</th>
            <th>品种</th>
            <th>数量 (BTC)</th>
            <th>开仓价格 (USDT)</th>
            <th>当前价格 (USDT)</th>
            <th>当前资金费率</th>
            <th>入场价差 (USDT)</th>
            <th>当前基差 (USDT)</th>
            <th>累计资金费收益 (USDT)</th>
            <th>未实现盈亏 (USDT)</th>
            <th>保证金 (USDT)</th>
            <th>保证金率</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in positionRows" :key="row.name + row.leg">
            <td>
              <strong>{{ row.name }}</strong>
              <p>{{ row.leg }}</p>
            </td>
            <td>{{ row.exchange }}</td>
            <td>{{ row.symbol }}</td>
            <td>{{ row.qty }}</td>
            <td>{{ row.entry }}</td>
            <td>{{ row.mark }}</td>
            <td>{{ row.funding }}</td>
            <td>{{ row.entryBasis }}</td>
            <td class="green">{{ row.currentBasis }}</td>
            <td class="green">{{ row.carry }}</td>
            <td class="green">{{ row.pnl }}</td>
            <td>{{ row.margin }}</td>
            <td>{{ row.marginRatio }}</td>
            <td class="green">{{ row.status }}</td>
            <td><button class="flat-action" type="button">平仓</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="positions-footer">
      <span>名义本金: 100,000.00 USDT</span>
      <span>总保证金: 40,300.00 USDT</span>
      <span>整体保证金率: 35.00%</span>
      <span class="green">预计年化综合净收益率: +22.31%</span>
    </div>
  </section>
</template>

<script setup lang="ts">
  const positionRows = [
    {
      name: '套利组合 #1',
      leg: '现货买入',
      exchange: 'Binance',
      symbol: 'BTC/USDT',
      qty: '0.5000',
      entry: '102,200.0',
      mark: '102,350.0',
      funding: '--',
      entryBasis: '+12.0',
      currentBasis: '+10.5',
      carry: '+285.40',
      pnl: '+75.00',
      margin: '10,250.00',
      marginRatio: '35.10%',
      status: '正常',
    },
    {
      name: '套利组合 #1',
      leg: '永续卖出',
      exchange: 'Binance',
      symbol: 'BTCUSDT 永续',
      qty: '0.5000',
      entry: '102,212.0',
      mark: '102,341.2',
      funding: '+0.0810%',
      entryBasis: '+12.0',
      currentBasis: '+10.5',
      carry: '+285.40',
      pnl: '+64.60',
      margin: '10,250.00',
      marginRatio: '35.10%',
      status: '正常',
    },
    {
      name: '套利组合 #2',
      leg: '现货买入',
      exchange: 'Binance',
      symbol: 'BTC/USDT',
      qty: '0.4791',
      entry: '101,980.0',
      mark: '102,350.0',
      funding: '--',
      entryBasis: '+8.5',
      currentBasis: '+10.5',
      carry: '+195.30',
      pnl: '+177.30',
      margin: '9,800.00',
      marginRatio: '34.80%',
      status: '正常',
    },
    {
      name: '套利组合 #2',
      leg: '永续卖出',
      exchange: 'Binance',
      symbol: 'BTCUSDT 永续',
      qty: '0.4791',
      entry: '101,988.5',
      mark: '102,341.2',
      funding: '+0.0810%',
      entryBasis: '+8.5',
      currentBasis: '+10.5',
      carry: '+195.30',
      pnl: '+169.30',
      margin: '9,800.00',
      marginRatio: '34.80%',
      status: '正常',
    },
  ] as const;
</script>

<style scoped lang="less">
  .panel {
    min-width: 0;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 18px;
    background: linear-gradient(
      180deg,
      var(--strategy-surface) 0%,
      var(--strategy-surface-soft) 100%
    );
    box-shadow: var(--strategy-shadow);
  }

  .panel-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .panel-title h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 800;
  }

  .positions-panel {
    padding-bottom: 10px;
  }

  .positions-metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;
  }

  .positions-metric {
    display: flex;
    min-height: 64px;
    padding: 10px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
  }

  .positions-metric span {
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .positions-metric strong {
    margin-top: 6px;
    color: var(--strategy-text-1);
    font-size: 15px;
    font-weight: 800;
  }

  .positions-table-wrap {
    overflow: auto;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow);
  }

  .positions-table {
    width: 100%;
    min-width: 1600px;
    border-collapse: collapse;
  }

  .positions-table th,
  .positions-table td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--strategy-border-soft);
    text-align: left;
    font-size: var(--strategy-font-sm);
  }

  .positions-table th {
    color: var(--strategy-text-3);
    background: var(--strategy-table-head-bg);
    font-weight: 700;
  }

  .positions-table td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .positions-table td strong {
    color: var(--strategy-text-1);
    font-size: 13px;
  }

  .positions-table td p {
    margin: 4px 0 0;
    color: #16a34a;
    font-size: 12px;
    font-weight: 700;
  }

  .flat-action {
    min-width: 104px;
    height: 40px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 800;
    cursor: pointer;
  }

  .positions-footer {
    display: flex;
    flex-wrap: wrap;
    gap: 28px;
    margin-top: 12px;
    color: var(--strategy-text-3);
    font-size: 13px;
    font-weight: 700;
  }

  .green {
    color: #16a34a !important;
  }

  @media (max-width: 1400px) {
    .positions-metrics {
      grid-template-columns: 1fr;
    }

    .positions-footer {
      flex-direction: column;
      align-items: flex-start;
    }
  }

  @media (max-width: 1024px) {
    .positions-table-wrap {
      width: 100%;
    }
  }
</style>
