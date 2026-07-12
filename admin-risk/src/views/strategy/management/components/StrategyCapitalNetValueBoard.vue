<template>
  <section class="capital-net-value-board">
    <header class="board-header">
      <div>
        <h3>账户净值统计</h3>
        <p>同步展示账户净值曲线与账户数据快照。</p>
      </div>
      <button class="board-refresh" type="button" @click="reloadAll">刷新</button>
    </header>

    <AccountNetValueChart
      ref="chartRef"
      :accounts="accounts"
      title="账户净值统计"
      height="420px"
    />

    <article class="snapshot-card">
      <header>
        <h4>账户数据快照</h4>
        <span>{{ health.service || 'data-service' }} / {{ health.update_frequency || '-' }}</span>
      </header>

      <div class="snapshot-table">
        <div class="snapshot-head snapshot-row">
          <span>账户</span>
          <span>类型</span>
          <span>资产</span>
          <span>状态</span>
          <span>更新时间</span>
        </div>
        <div v-for="item in accounts" :key="item.id" class="snapshot-row">
          <div>
            <strong>{{ item.name }}</strong>
            <p>{{ item.account_address }}</p>
          </div>
          <span>{{ item.account_type }}</span>
          <div>
            <strong>{{ formatMoney(item.total_asset) }} USD</strong>
            <p>可用 {{ formatMoney(item.available_fund) }}</p>
          </div>
          <span :class="item.status === 'active' ? 'is-active' : 'is-inactive'">{{ item.status }}</span>
          <span>{{ formatDateTime(item.asset_updated_at) }}</span>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import AccountNetValueChart from '@/views/data/components/AccountNetValueChart.vue';
  import { DataAccount, DataServiceHealth, getAccounts, getDataHealth } from '@/api/riskControl';
  import { formateNumStr } from '@/utils/formate';
  import { formatToDateTime } from '@/utils/dateUtil';

  const chartRef = ref<InstanceType<typeof AccountNetValueChart> | null>(null);
  const accounts = ref<DataAccount[]>([]);
  const health = ref<DataServiceHealth>({ status: 'unknown', service: 'data-service', update_frequency: '-' });

  function formatMoney(value: any) {
    return formateNumStr(value || 0, { decimals: 2, keepZero: true });
  }

  function formatDateTime(value?: string) {
    return value ? formatToDateTime(value) : '-';
  }

  async function loadData() {
    const [accountRes, healthRes] = await Promise.all([getAccounts(), getDataHealth()]);
    accounts.value = accountRes;
    health.value = healthRes;
  }

  async function reloadAll() {
    await loadData();
    chartRef.value?.reload?.();
  }

  onMounted(loadData);
</script>

<style scoped lang="less">
  .capital-net-value-board {
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

  .snapshot-card {
    padding: 16px 18px;
    border-radius: 18px;
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow);
    border: 1px solid var(--strategy-border);
  }

  .snapshot-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .snapshot-card h4 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--strategy-text-1);
  }

  .snapshot-card header span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .snapshot-table {
    display: grid;
    gap: 10px;
  }

  .snapshot-row {
    display: grid;
    grid-template-columns: 1.4fr .7fr 1fr .5fr .9fr;
    align-items: center;
    gap: 12px;
  }

  .snapshot-head {
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .snapshot-row strong {
    display: block;
    color: var(--strategy-text-1);
    font-size: 13px;
    font-weight: 700;
  }

  .snapshot-row p {
    margin: 4px 0 0;
    color: var(--strategy-text-3);
    font-size: 11px;
    word-break: break-all;
  }

  .is-active {
    color: var(--strategy-success);
    font-weight: 700;
  }

  .is-inactive {
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  @media (max-width: 980px) {
    .snapshot-row {
      grid-template-columns: 1fr;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--strategy-border);
    }

    .snapshot-head {
      display: none;
    }

    .board-header,
    .snapshot-card header {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
