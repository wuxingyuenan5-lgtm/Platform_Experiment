<template>
  <section class="platform-trading-panel">
    <div class="panel-head">
      <div>
        <h3>平台批次执行</h3>
        <p>账户、策略实例与标的均来自 Platform Backend Catalog；执行仍由 Runtime 隔离。</p>
      </div>
      <span :class="['status', statusTone]">
        {{ batchStatusLabel }}
      </span>
    </div>

    <div class="catalog-meta">
      <span>研究筛选：{{ exchange }} / {{ symbol }}</span>
      <span>策略：{{ strategyInstance?.name ?? '未配置' }}</span>
      <span>账户：{{ selectedAccount?.accountCode ?? '未配置' }}</span>
      <span>模式：{{ strategyInstance?.tradingMode ?? '未知' }}</span>
    </div>

    <div class="order-grid">
      <label>
        <span>交易方向</span>
        <select v-model="direction">
          <option value="collect">正套：现货买入 + 永续卖出</option>
          <option value="pay">反套：现货卖出 + 永续买入</option>
        </select>
      </label>

      <label>
        <span>订单类型</span>
        <select v-model="orderType">
          <option value="market">市价</option>
          <option value="limit">限价</option>
        </select>
      </label>

      <label>
        <span>数量</span>
        <input v-model="quantity" inputmode="decimal" />
      </label>

      <label>
        <span>模拟价格</span>
        <input v-model="price" :disabled="orderType === 'market'" inputmode="decimal" />
      </label>
    </div>

    <div class="actions">
      <button type="button" :disabled="overallBusy || !canSubmit" @click="submitPair">
        {{ overallBusy ? '正在处理...' : `提交 ${symbol} 执行批次` }}
      </button>
      <button class="secondary" type="button" :disabled="overallBusy" @click="refreshBoth">
        刷新持仓与 PnL
      </button>
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-else-if="successMessage" class="success-message">{{ successMessage }}</p>

    <div v-if="lastBatch" class="batch-meta">
      <span>批次 ID：{{ lastBatch.batchId }}</span>
      <span>幂等键：{{ lastBatch.idempotencyKey }}</span>
      <span>状态：{{ lastBatch.status }}</span>
      <strong v-if="lastBatch.requiresManualIntervention">需要人工干预</strong>
    </div>

    <div class="snapshot-grid">
      <article>
        <div class="leg-title">
          <strong>现货腿</strong>
          <span>{{ spotSymbol }}</span>
        </div>
        <dl>
          <div
            ><dt>净持仓</dt><dd>{{ spot.snapshot.value.position?.netQuantity ?? '—' }}</dd></div
          >
          <div
            ><dt>持仓均价</dt><dd>{{ spot.snapshot.value.position?.averagePrice ?? '—' }}</dd></div
          >
          <div
            ><dt>已实现 PnL</dt><dd>{{ spot.snapshot.value.pnl?.realizedPnl ?? '—' }}</dd></div
          >
          <div
            ><dt>订单状态</dt><dd>{{ batchLegStatus('spot') }}</dd></div
          >
          <div
            ><dt>订单 ID</dt><dd class="order-id">{{ batchLegOrderId('spot') }}</dd></div
          >
        </dl>
      </article>

      <article>
        <div class="leg-title">
          <strong>永续腿</strong>
          <span>{{ perpSymbol }}</span>
        </div>
        <dl>
          <div
            ><dt>净持仓</dt><dd>{{ perp.snapshot.value.position?.netQuantity ?? '—' }}</dd></div
          >
          <div
            ><dt>持仓均价</dt><dd>{{ perp.snapshot.value.position?.averagePrice ?? '—' }}</dd></div
          >
          <div
            ><dt>已实现 PnL</dt><dd>{{ perp.snapshot.value.pnl?.realizedPnl ?? '—' }}</dd></div
          >
          <div
            ><dt>订单状态</dt><dd>{{ batchLegStatus('perp') }}</dd></div
          >
          <div
            ><dt>订单 ID</dt><dd class="order-id">{{ batchLegOrderId('perp') }}</dd></div
          >
        </dl>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';

  import {
    createExecutionBatch,
    getAccounts,
    getInstruments,
    getStrategyAccountBindings,
    getStrategyInstances,
  } from '/@/api/platform/trading';
  import type {
    AccountResult,
    ExecutionBatchResult,
    InstrumentResult,
    StrategyInstanceResult,
  } from '/@/api/platform/trading.types';
  import { usePlatformTrading } from '/@/hooks/trading/usePlatformTrading';
  import type { FundingExchange, FundingSymbol } from '../types';

  const props = defineProps<{
    exchange: FundingExchange;
    symbol: FundingSymbol;
  }>();

  const direction = ref<'collect' | 'pay'>('collect');
  const orderType = ref<'market' | 'limit'>('market');
  const quantity = ref('0.01');
  const price = ref('100');
  const successMessage = ref('');
  const localError = ref('');
  const catalogLoading = ref(false);
  const catalogError = ref('');
  const submitting = ref(false);
  const lastBatch = ref<ExecutionBatchResult | null>(null);
  const strategyInstance = ref<StrategyInstanceResult | null>(null);
  const selectedAccount = ref<AccountResult | null>(null);
  const spotInstrument = ref<InstrumentResult | null>(null);
  const perpInstrument = ref<InstrumentResult | null>(null);

  const spot = usePlatformTrading();
  const perp = usePlatformTrading();

  const spotSymbol = computed(() => spotInstrument.value?.instrumentCode ?? `${props.symbol}USDT`);
  const perpSymbol = computed(
    () => perpInstrument.value?.instrumentCode ?? `${props.symbol}USDT-PERP`,
  );
  const catalogReady = computed(
    () =>
      strategyInstance.value?.status === 'active' &&
      strategyInstance.value.tradingMode === 'simulation' &&
      selectedAccount.value?.status === 'active' &&
      selectedAccount.value.environment === 'simulation' &&
      Boolean(spotInstrument.value?.contract) &&
      Boolean(perpInstrument.value?.contract),
  );
  const overallBusy = computed(
    () =>
      catalogLoading.value || submitting.value || spot.refreshing.value || perp.refreshing.value,
  );
  const errorMessage = computed(
    () =>
      catalogError.value ||
      localError.value ||
      spot.errorMessage.value ||
      perp.errorMessage.value ||
      '',
  );
  const canSubmit = computed(
    () =>
      catalogReady.value &&
      Number(quantity.value) > 0 &&
      (orderType.value === 'market' || Number(price.value) > 0),
  );
  const batchStatusLabel = computed(() => {
    if (catalogLoading.value) return '加载 Catalog';
    if (!catalogReady.value) return 'Catalog 未配置';
    if (overallBusy.value) return '处理中';
    if (!lastBatch.value) return 'Simulation 可执行';
    if (lastBatch.value.status === 'hedged') return '已对冲';
    if (lastBatch.value.status === 'manual_intervention') return '需人工干预';
    if (lastBatch.value.status === 'failed') return '执行失败';
    return lastBatch.value.status;
  });
  const statusTone = computed(() => {
    if (catalogLoading.value || submitting.value) return 'is-busy';
    if (
      !catalogReady.value ||
      lastBatch.value?.requiresManualIntervention ||
      lastBatch.value?.status === 'failed'
    ) {
      return 'is-danger';
    }
    return 'is-ready';
  });

  function batchLeg(role: 'spot' | 'perp') {
    return lastBatch.value?.legs.find((leg) => leg.role === role);
  }

  function batchLegStatus(role: 'spot' | 'perp') {
    return batchLeg(role)?.status ?? '—';
  }

  function batchLegOrderId(role: 'spot' | 'perp') {
    return batchLeg(role)?.orderId ?? '—';
  }

  function buildIdempotencyKey(): string {
    const entropy =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return `funding:${strategyInstance.value?.strategyInstanceId}:${props.symbol}:${direction.value}:${entropy}`.slice(
      0,
      128,
    );
  }

  async function loadCatalog(): Promise<void> {
    catalogLoading.value = true;
    catalogError.value = '';
    localError.value = '';
    lastBatch.value = null;
    strategyInstance.value = null;
    selectedAccount.value = null;
    spotInstrument.value = null;
    perpInstrument.value = null;

    try {
      const [instances, accounts, instruments] = await Promise.all([
        getStrategyInstances(),
        getAccounts(),
        getInstruments(),
      ]);
      const strategy = instances.find(
        (item) =>
          item.strategyKey === 'funding_arbitrage' &&
          item.status === 'active' &&
          item.tradingMode === 'simulation',
      );
      if (!strategy) {
        throw new Error('未找到可用的资费套利 Simulation 策略实例。');
      }

      const bindings = await getStrategyAccountBindings(strategy.strategyInstanceId);
      const activeBindingIds = new Set(
        bindings.filter((item) => item.status === 'active').map((item) => item.accountId),
      );
      const account = accounts.find(
        (item) =>
          activeBindingIds.has(item.accountId) &&
          item.status === 'active' &&
          item.environment === 'simulation',
      );
      if (!account) {
        throw new Error('资费套利策略没有绑定 active Simulation 账户。');
      }

      const spotCode = `${props.symbol}USDT`;
      const perpCode = `${props.symbol}USDT-PERP`;
      const spotMatch = instruments.find(
        (item) => item.instrumentCode === spotCode && Boolean(item.contract),
      );
      const perpMatch = instruments.find(
        (item) => item.instrumentCode === perpCode && Boolean(item.contract),
      );
      if (!spotMatch || !perpMatch) {
        throw new Error(`${props.symbol} 尚未在后端 Catalog 同时配置现货与永续合约，已禁止提交。`);
      }

      strategyInstance.value = strategy;
      selectedAccount.value = account;
      spotInstrument.value = spotMatch;
      perpInstrument.value = perpMatch;
      await refreshSnapshots();
    } catch (error) {
      catalogError.value = error instanceof Error ? error.message : 'Catalog 加载失败。';
    } finally {
      catalogLoading.value = false;
    }
  }

  async function refreshSnapshots(): Promise<void> {
    if (!selectedAccount.value || !spotInstrument.value || !perpInstrument.value) return;
    await Promise.all([
      spot.refresh(selectedAccount.value.accountId, spotInstrument.value.instrumentId),
      perp.refresh(selectedAccount.value.accountId, perpInstrument.value.instrumentId),
    ]);
  }

  async function refreshBoth(): Promise<void> {
    localError.value = '';
    successMessage.value = '';
    if (!catalogReady.value) {
      await loadCatalog();
      return;
    }
    try {
      await refreshSnapshots();
    } catch {
      localError.value = '刷新失败，请确认 Platform Backend 已启动。';
    }
  }

  async function submitPair(): Promise<void> {
    if (
      !canSubmit.value ||
      !strategyInstance.value ||
      !selectedAccount.value ||
      !spotInstrument.value ||
      !perpInstrument.value
    ) {
      return;
    }

    localError.value = '';
    successMessage.value = '';
    submitting.value = true;
    const spotSide = direction.value === 'collect' ? 'buy' : 'sell';
    const perpSide = direction.value === 'collect' ? 'sell' : 'buy';
    const limitPrice = orderType.value === 'limit' ? price.value : undefined;

    try {
      const batch = await createExecutionBatch({
        idempotencyKey: buildIdempotencyKey(),
        strategyInstanceId: strategyInstance.value.strategyInstanceId,
        accountId: selectedAccount.value.accountId,
        strategyKey: strategyInstance.value.strategyKey,
        direction: direction.value,
        legs: [
          {
            role: 'spot',
            instrumentId: spotInstrument.value.instrumentId,
            symbol: spotInstrument.value.instrumentCode,
            side: spotSide,
            orderType: orderType.value,
            quantity: quantity.value,
            price: limitPrice,
          },
          {
            role: 'perp',
            instrumentId: perpInstrument.value.instrumentId,
            symbol: perpInstrument.value.instrumentCode,
            side: perpSide,
            orderType: orderType.value,
            quantity: quantity.value,
            price: limitPrice,
          },
        ],
      });
      lastBatch.value = batch;
      await refreshSnapshots();

      if (batch.status === 'hedged') {
        successMessage.value = '双腿均已成交，批次已进入已对冲状态。';
      } else if (batch.requiresManualIntervention) {
        localError.value = `批次未完整对冲，需要人工干预：${
          batch.failureReason || '请检查两腿状态'
        }`;
      } else {
        localError.value = `批次执行失败：${batch.failureReason || batch.status}`;
      }
    } catch (error) {
      localError.value =
        error instanceof Error ? error.message : '批次请求失败，请确认 Platform Backend 已启动。';
    } finally {
      submitting.value = false;
    }
  }

  watch(
    () => [props.exchange, props.symbol],
    () => {
      void loadCatalog();
    },
    { immediate: true },
  );
</script>

<style scoped lang="less">
  .platform-trading-panel {
    padding: 18px;
    border: 1px solid #dfe7f1;
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .panel-head,
  .actions,
  .leg-title,
  .batch-meta,
  dl div {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h3,
  p,
  dl {
    margin: 0;
  }

  h3 {
    color: #162845;
    font-size: 18px;
  }

  .panel-head p {
    margin-top: 4px;
    color: #718096;
    font-size: 13px;
  }

  .catalog-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin-top: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    background: #f6f8fb;
    color: #5d6d80;
    font-size: 12px;
  }

  .status {
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }

  .is-ready {
    color: #138a52;
    background: #eaf8f1;
  }

  .is-busy {
    color: #9a6700;
    background: #fff7df;
  }

  .is-danger {
    color: #c62828;
    background: #fff0f0;
  }

  .order-grid,
  .snapshot-grid {
    display: grid;
    gap: 12px;
    margin-top: 16px;
  }

  .order-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .snapshot-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  label {
    display: grid;
    gap: 6px;
    color: #5d6d80;
    font-size: 12px;
    font-weight: 700;
  }

  input,
  select {
    width: 100%;
    min-height: 38px;
    padding: 0 10px;
    border: 1px solid #dfe5ed;
    border-radius: 9px;
    background: #fff;
    color: #1f2937;
  }

  .actions {
    justify-content: flex-start;
    margin-top: 16px;
  }

  button {
    min-height: 40px;
    padding: 0 16px;
    border: 0;
    border-radius: 10px;
    background: #1677ff;
    color: #fff;
    cursor: pointer;
    font-weight: 700;
  }

  button.secondary {
    color: #32445d;
    background: #edf2f7;
  }

  button:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  .error-message,
  .success-message {
    margin-top: 12px;
    font-size: 13px;
    font-weight: 700;
  }

  .error-message {
    color: #d4380d;
  }

  .success-message {
    color: #138a52;
  }

  .batch-meta {
    justify-content: flex-start;
    flex-wrap: wrap;
    margin-top: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    background: #f6f8fb;
    color: #5d6d80;
    font-size: 12px;
  }

  .batch-meta strong {
    color: #c62828;
  }

  article {
    padding: 14px;
    border: 1px solid #e6ebf2;
    border-radius: 12px;
    background: #fbfdff;
  }

  .leg-title span {
    color: #718096;
    font-size: 12px;
  }

  dl {
    display: grid;
    gap: 8px;
    margin-top: 12px;
  }

  dt {
    color: #718096;
  }

  dd {
    margin: 0;
    color: #162845;
    font-weight: 800;
  }

  .order-id {
    max-width: 65%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 11px;
  }

  @media (max-width: 1000px) {
    .order-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 680px) {
    .order-grid,
    .snapshot-grid {
      grid-template-columns: 1fr;
    }

    .panel-head {
      align-items: flex-start;
    }
  }
</style>
