<template>
  <section class="capital-finance-board">
    <header class="board-header">
      <div>
        <h3>财务总览</h3>
        <p>同步展示总资产、可用资金、资产结构与汇率接口状态。</p>
      </div>
      <button class="board-refresh" type="button" @click="loadData">刷新</button>
    </header>

    <section class="summary-grid">
      <article class="summary-card">
        <label>总资产</label>
        <strong>{{ formatMoney(totalAsset) }} <span>USD</span></strong>
      </article>
      <article class="summary-card">
        <label>可用资金</label>
        <strong>{{ formatMoney(availableFund) }} <span>USD</span></strong>
      </article>
      <article class="summary-card">
        <label>资金占用</label>
        <strong>{{ formatMoney(usedFund) }} <span>USD</span></strong>
      </article>
      <article class="summary-card">
        <label>资产项</label>
        <strong>{{ ratioItems.length }}</strong>
      </article>
    </section>

    <section class="content-grid">
      <article class="panel-card">
        <header class="panel-card__header">
          <h4>资产占比</h4>
          <span>实时结构</span>
        </header>
        <div class="ratio-table">
          <div class="ratio-head ratio-row">
            <span>资产项</span>
            <span>金额 USD</span>
            <span>占比</span>
          </div>
          <div v-for="item in ratioItems" :key="item.name" class="ratio-row">
            <span>{{ item.name }}</span>
            <strong>{{ formatMoney(item.valueUSD ?? item.value) }}</strong>
            <div class="ratio-meter">
              <div class="ratio-meter__track">
                <div class="ratio-meter__fill" :style="{ width: `${percentNumber(item.percent)}%` }"></div>
              </div>
              <em>{{ percentNumber(item.percent) }}%</em>
            </div>
          </div>
        </div>
      </article>

      <article class="panel-card info-card">
        <header class="panel-card__header">
          <h4>接口状态</h4>
          <span>资金与汇率</span>
        </header>
        <dl>
          <div>
            <dt>汇率标的</dt>
            <dd>{{ exchangeInfo.symbol || 'USD' }}</dd>
          </div>
          <div>
            <dt>汇率</dt>
            <dd>{{ exchangeInfo.rate ?? '-' }}</dd>
          </div>
          <div>
            <dt>最新更新时间</dt>
            <dd>{{ latestUpdateText }}</dd>
          </div>
          <div>
            <dt>数据来源</dt>
            <dd>data-service</dd>
          </div>
        </dl>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    DataAccount,
    ExchangeInfo,
    getAccounts,
    getExchangeInfo,
    getProductRatio,
    getTotalAssetSummary,
    ProductRatioItem,
    TotalAssetSummary,
  } from '@/api/riskControl';
  import { formateNumStr } from '@/utils/formate';
  import { formatToDateTime } from '@/utils/dateUtil';

  const accounts = ref<DataAccount[]>([]);
  const ratioItems = ref<ProductRatioItem[]>([]);
  const totalSummary = ref<TotalAssetSummary>({});
  const exchangeInfo = ref<ExchangeInfo>({});

  const totalAsset = computed(() => {
    const fromApi = totalSummary.value.total_asset ?? totalSummary.value.total;
    if (typeof fromApi === 'number') return fromApi;
    return accounts.value.reduce((sum, item) => sum + Number(item.total_asset || 0), 0);
  });

  const availableFund = computed(() =>
    accounts.value.reduce((sum, item) => sum + Number(item.available_fund || 0), 0),
  );

  const usedFund = computed(() => Math.max(totalAsset.value - availableFund.value, 0));

  const latestUpdateText = computed(() => {
    const times = accounts.value.map((item) => item.asset_updated_at).filter(Boolean).sort();
    const latest = times[times.length - 1] || totalSummary.value.updated_at || exchangeInfo.value.updated_at;
    return latest ? formatToDateTime(latest) : '-';
  });

  function formatMoney(value: any) {
    return formateNumStr(value || 0, { decimals: 2, keepZero: true });
  }

  function percentNumber(value: any) {
    return Number((Number(value || 0) * 100).toFixed(2));
  }

  async function loadData() {
    const [accountRes, ratioRes, totalRes, exchangeRes] = await Promise.all([
      getAccounts(),
      getProductRatio(),
      getTotalAssetSummary(),
      getExchangeInfo(),
    ]);
    accounts.value = accountRes;
    ratioItems.value = ratioRes;
    totalSummary.value = totalRes;
    exchangeInfo.value = exchangeRes;
  }

  onMounted(loadData);
</script>

<style scoped lang="less">
  .capital-finance-board {
    display: grid;
    gap: 12px;
  }

  .board-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
  }

  .board-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: var(--strategy-text-1);
  }

  .board-header p {
    display: none;
  }

  .board-refresh {
    height: 36px;
    padding: 0 16px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 12px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-weight: 600;
    cursor: pointer;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .summary-card,
  .panel-card {
    padding: 16px 18px;
    border-radius: 18px;
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow);
    border: 1px solid var(--strategy-border);
  }

  .summary-card label {
    display: block;
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .summary-card strong {
    display: block;
    margin-top: 10px;
    color: var(--strategy-text-1);
    font-size: 28px;
    line-height: 1.1;
    font-weight: 700;
  }

  .summary-card span {
    margin-left: 4px;
    font-size: 12px;
    font-weight: 600;
    color: var(--strategy-text-3);
  }

  .content-grid {
    display: grid;
    grid-template-columns: 1.3fr 0.9fr;
    gap: 12px;
  }

  .panel-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .panel-card__header h4 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--strategy-text-1);
  }

  .panel-card__header span {
    font-size: 12px;
    color: var(--strategy-text-3);
  }

  .ratio-table {
    display: grid;
    gap: 10px;
  }

  .ratio-row {
    display: grid;
    grid-template-columns: 1.1fr 0.8fr 1fr;
    align-items: center;
    gap: 12px;
  }

  .ratio-head {
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .ratio-row strong {
    color: var(--strategy-text-1);
    font-size: 13px;
    font-weight: 700;
  }

  .ratio-meter {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: center;
    gap: 10px;
  }

  .ratio-meter__track {
    overflow: hidden;
    height: 8px;
    border-radius: 999px;
    background: var(--strategy-surface-muted);
  }

  .ratio-meter__fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #7ba2e5, #4f7fd3);
  }

  .ratio-meter em {
    color: var(--strategy-text-2);
    font-size: 12px;
    font-style: normal;
    font-weight: 600;
  }

  .info-card dl {
    display: grid;
    gap: 12px;
    margin: 0;
  }

  .info-card div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--strategy-border);
  }

  .info-card div:last-child {
    padding-bottom: 0;
    border-bottom: none;
  }

  .info-card dt {
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .info-card dd {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 14px;
    font-weight: 600;
  }

  @media (max-width: 1280px) {
    .summary-grid,
    .content-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  @media (max-width: 860px) {
    .summary-grid,
    .content-grid {
      grid-template-columns: 1fr;
    }

    .board-header {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
