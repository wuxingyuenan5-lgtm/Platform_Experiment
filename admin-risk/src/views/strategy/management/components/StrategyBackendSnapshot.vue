<template>
  <section class="backend-snapshot">
    <div class="snapshot-header">
      <div>
        <div class="snapshot-title">后端实况</div>
        <div class="snapshot-subtitle">{{ readinessText }}</div>
      </div>
      <button class="refresh-button" type="button" @click="loadSnapshot" :disabled="loading">
        {{ loading ? '刷新中' : '刷新' }}
      </button>
    </div>

    <div v-if="error" class="snapshot-error">{{ error }}</div>

    <div class="metric-grid">
      <div class="metric-cell">
        <span class="metric-label">策略实例</span>
        <strong>{{ instances.length }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">V1闭环</span>
        <strong>{{ closedLoopCount }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">账户</span>
        <strong>{{ accounts.length }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">标的</span>
        <strong>{{ instruments.length }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">策略运行</span>
        <strong>{{ runs.length }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">V1可运行</span>
        <strong>{{ runnableReadinessCount }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">执行批次</span>
        <strong>{{ batches.length }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">订单</span>
        <strong>{{ orders.length }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">Runtime</span>
        <strong>{{ readiness?.runtimeStatus || '未知' }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">对账状态</span>
        <strong>{{ reconciliation?.status || '未知' }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">待处理异常</span>
        <strong>{{ reconciliation?.issues.length || 0 }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">实盘开关</span>
        <strong>{{ safety?.liveTradingEnabled ? '开启' : '关闭' }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">凭证引用</span>
        <strong>{{ credentials.length }}</strong>
      </div>
      <div class="metric-cell">
        <span class="metric-label">API Config</span>
        <strong>
          {{ exchangeConnectivity?.configuredCredentialCount || 0 }}/{{
            exchangeConnectivity?.credentialCount || 0
          }}
        </strong>
      </div>
    </div>

    <div class="snapshot-grid">
      <div class="snapshot-panel">
        <div class="panel-title">策略实例</div>
        <div class="row-list">
          <div v-for="item in instances" :key="item.strategyInstanceId" class="data-row">
            <span>{{ item.strategyName }}</span>
            <span class="row-meta">{{ item.tradingMode }} / {{ item.status }}</span>
          </div>
        </div>
      </div>

      <div class="snapshot-panel">
        <div class="panel-title">最近策略运行</div>
        <div v-if="!runs.length" class="empty-row">暂无运行</div>
        <div v-else class="row-list">
          <div v-for="item in runs.slice(0, 4)" :key="item.strategyRunId" class="data-row">
            <span>{{ item.strategyKey }} / {{ item.direction }}</span>
            <span class="row-meta">{{ item.status }}</span>
          </div>
        </div>
      </div>

      <div class="snapshot-panel">
        <div class="panel-title">最近执行批次</div>
        <div v-if="!batches.length" class="empty-row">暂无批次</div>
        <div v-else class="row-list">
          <div v-for="item in batches.slice(0, 4)" :key="item.batchId" class="data-row">
            <span>{{ item.strategyKey }} / {{ item.direction }}</span>
            <span class="row-meta">{{ item.status }}</span>
          </div>
        </div>
      </div>

      <div class="snapshot-panel">
        <div class="panel-title">账户</div>
        <div class="row-list">
          <div v-for="item in accounts" :key="item.accountId" class="data-row">
            <span>{{ item.accountCode }}</span>
            <span class="row-meta">{{ item.environment }} / {{ item.status }}</span>
          </div>
        </div>
      </div>

      <div class="snapshot-panel">
        <div class="panel-title">对账问题</div>
        <div v-if="!reconciliation?.issues.length" class="empty-row">暂无异常</div>
        <div v-else class="row-list">
          <div
            v-for="item in reconciliation.issues.slice(0, 4)"
            :key="`${item.issueType}-${item.subjectId}`"
            class="data-row"
          >
            <span>{{ item.issueType }}</span>
            <span class="row-meta">{{ item.subjectType }}</span>
          </div>
        </div>
      </div>

      <div class="snapshot-panel">
        <div class="panel-title">最近订单</div>
        <div v-if="!orders.length" class="empty-row">暂无订单</div>
        <div v-else class="row-list">
          <div v-for="item in orders.slice(0, 4)" :key="item.orderId" class="data-row">
            <span>{{ item.symbol }} {{ item.side }} {{ item.quantity }}</span>
            <span class="row-meta">{{ item.status }}</span>
          </div>
        </div>
      </div>

      <div class="snapshot-panel">
        <div class="panel-title">Gateway API</div>
        <div v-if="!exchangeConnectivity" class="empty-row">Waiting</div>
        <div v-else class="row-list">
          <div class="data-row">
            <span>{{ exchangeConnectivity.gateway || 'runtime' }}</span>
            <span class="row-meta">{{ exchangeConnectivity.status }}</span>
          </div>
          <div
            v-for="item in exchangeConnectivity.credentials"
            :key="item.credentialRef"
            class="data-row"
          >
            <span>{{ item.credentialRef }}</span>
            <span class="row-meta">
              {{ item.configured ? 'configured' : item.missingFields.join(',') }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    getAccounts,
    getExecutionBatches,
    getCredentialReferences,
    getExchangeConnectivity,
    getInstruments,
    getOrders,
    getReconciliationSummary,
    getRuntimeReadiness,
    getStrategyDefinitions,
    getStrategyInstances,
    getStrategyRuns,
    getStrategyV1Readiness,
    getTradingSafety,
  } from '@/api/platform/trading';
  import type {
    AccountResult,
    CredentialReferenceResult,
    ExchangeConnectivityResult,
    ExecutionBatchResult,
    InstrumentResult,
    OrderDetailResult,
    ReconciliationSummaryResult,
    RuntimeReadinessResult,
    StrategyDefinitionResult,
    StrategyInstanceResult,
    StrategyRunResult,
    StrategyV1ReadinessResult,
    TradingSafetyResult,
  } from '@/api/platform/trading.types';

  const loading = ref(false);
  const error = ref('');
  const readiness = ref<RuntimeReadinessResult | null>(null);
  const definitions = ref<StrategyDefinitionResult[]>([]);
  const instances = ref<StrategyInstanceResult[]>([]);
  const accounts = ref<AccountResult[]>([]);
  const instruments = ref<InstrumentResult[]>([]);
  const orders = ref<OrderDetailResult[]>([]);
  const batches = ref<ExecutionBatchResult[]>([]);
  const runs = ref<StrategyRunResult[]>([]);
  const readinessRows = ref<StrategyV1ReadinessResult[]>([]);
  const reconciliation = ref<ReconciliationSummaryResult | null>(null);
  const safety = ref<TradingSafetyResult | null>(null);
  const credentials = ref<CredentialReferenceResult[]>([]);
  const exchangeConnectivity = ref<ExchangeConnectivityResult | null>(null);

  const closedLoopCount = computed(
    () => definitions.value.filter((item) => item.v1Scope === 'closed_loop').length,
  );
  const runnableReadinessCount = computed(
    () => readinessRows.value.filter((item) => item.runnable).length,
  );

  const readinessText = computed(() => {
    if (!readiness.value) return '等待后端响应';
    return `Backend ${readiness.value.backendStatus} / Database ${readiness.value.databaseStatus} / Mode ${readiness.value.defaultTradingMode}`;
  });

  async function loadSnapshot() {
    loading.value = true;
    error.value = '';
    try {
      const [
        runtime,
        reconciliationSummary,
        tradingSafety,
        credentialRows,
        exchangeStatus,
        strategyDefinitions,
        strategyInstances,
        accountRows,
        instrumentRows,
        orderRows,
      ] = await Promise.all([
          getRuntimeReadiness(),
          getReconciliationSummary(),
          getTradingSafety(),
          getCredentialReferences(),
          getExchangeConnectivity(),
          getStrategyDefinitions(),
          getStrategyInstances(),
          getAccounts(),
          getInstruments(),
          getOrders(),
        ]);

      const [batchRows, runGroups] = await Promise.all([
        getExecutionBatches(),
        Promise.all(
          strategyInstances
            .filter((item) => item.status === 'active')
            .map((item) => getStrategyRuns(item.strategyInstanceId)),
        ),
      ]);
      const v1ReadinessRows = await Promise.all(
        strategyInstances.map((item) => getStrategyV1Readiness(item.strategyInstanceId)),
      );

      readiness.value = runtime;
      reconciliation.value = reconciliationSummary;
      safety.value = tradingSafety;
      credentials.value = credentialRows;
      exchangeConnectivity.value = exchangeStatus;
      definitions.value = strategyDefinitions;
      instances.value = strategyInstances;
      accounts.value = accountRows;
      instruments.value = instrumentRows;
      orders.value = orderRows;
      batches.value = batchRows;
      runs.value = runGroups.flat().sort((left, right) => right.createdAt.localeCompare(left.createdAt));
      readinessRows.value = v1ReadinessRows;
    } catch (err) {
      error.value = err instanceof Error ? err.message : '后端实况加载失败';
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    loadSnapshot();
  });
</script>

<style scoped lang="less">
  .backend-snapshot {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 14px;
    border: 1px solid rgba(148, 163, 184, 0.28);
    background: rgba(255, 255, 255, 0.86);
  }

  .snapshot-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .snapshot-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--strategy-text-1);
  }

  .snapshot-subtitle {
    margin-top: 2px;
    font-size: 12px;
    color: var(--strategy-text-3);
  }

  .refresh-button {
    height: 30px;
    padding: 0 12px;
    border: 1px solid rgba(148, 163, 184, 0.42);
    background: #fff;
    color: var(--strategy-text-1);
    cursor: pointer;
  }

  .refresh-button:disabled {
    cursor: wait;
    opacity: 0.6;
  }

  .snapshot-error {
    padding: 8px 10px;
    background: rgba(239, 68, 68, 0.08);
    color: #b42318;
    font-size: 12px;
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(8, minmax(86px, 1fr));
    gap: 8px;
  }

  .metric-cell {
    display: flex;
    min-height: 58px;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    padding: 10px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: rgba(248, 250, 252, 0.82);
  }

  .metric-label {
    font-size: 12px;
    color: var(--strategy-text-3);
  }

  .metric-cell strong {
    font-size: 18px;
    color: var(--strategy-text-1);
  }

  .snapshot-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(180px, 1fr));
    gap: 10px;
  }

  .snapshot-panel {
    min-height: 134px;
    padding: 10px;
    border: 1px solid rgba(148, 163, 184, 0.22);
    background: #fff;
  }

  .panel-title {
    margin-bottom: 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--strategy-text-1);
  }

  .row-list {
    display: flex;
    flex-direction: column;
    gap: 7px;
  }

  .data-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    font-size: 12px;
    color: var(--strategy-text-1);
  }

  .row-meta,
  .empty-row {
    color: var(--strategy-text-3);
    white-space: nowrap;
  }

  @media (max-width: 1440px) {
    .metric-grid {
      grid-template-columns: repeat(4, minmax(96px, 1fr));
    }

    .snapshot-grid {
      grid-template-columns: repeat(2, minmax(180px, 1fr));
    }
  }

  @media (max-width: 760px) {
    .metric-grid,
    .snapshot-grid {
      grid-template-columns: 1fr;
    }

    .snapshot-header {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
