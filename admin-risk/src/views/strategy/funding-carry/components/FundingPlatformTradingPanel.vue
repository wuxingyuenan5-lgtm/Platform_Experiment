<template>
  <section class="platform-trading-panel">
    <div class="panel-head">
      <div>
        <h3>平台模拟执行</h3>
        <p>当前仅连接内部 Platform Backend 与 Fake Gateway，不依赖交易所 API。</p>
      </div>
      <span :class="['status', overallBusy ? 'is-busy' : 'is-ready']">
        {{ overallBusy ? '处理中' : '可执行' }}
      </span>
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
        {{ overallBusy ? '正在执行...' : `提交 ${exchange} ${symbol} 双腿订单` }}
      </button>
      <button class="secondary" type="button" :disabled="overallBusy" @click="refreshBoth">刷新持仓与 PnL</button>
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-else-if="successMessage" class="success-message">{{ successMessage }}</p>

    <div class="snapshot-grid">
      <article>
        <div class="leg-title">
          <strong>现货腿</strong>
          <span>{{ spotSymbol }}</span>
        </div>
        <dl>
          <div><dt>净持仓</dt><dd>{{ spot.snapshot.value.position?.netQuantity ?? '0' }}</dd></div>
          <div><dt>持仓均价</dt><dd>{{ spot.snapshot.value.position?.averagePrice ?? '—' }}</dd></div>
          <div><dt>已实现 PnL</dt><dd>{{ spot.snapshot.value.pnl?.realizedPnl ?? '0' }}</dd></div>
          <div><dt>订单状态</dt><dd>{{ spot.lastOrder.value?.status ?? '—' }}</dd></div>
        </dl>
      </article>

      <article>
        <div class="leg-title">
          <strong>永续腿</strong>
          <span>{{ perpSymbol }}</span>
        </div>
        <dl>
          <div><dt>净持仓</dt><dd>{{ perp.snapshot.value.position?.netQuantity ?? '0' }}</dd></div>
          <div><dt>持仓均价</dt><dd>{{ perp.snapshot.value.position?.averagePrice ?? '—' }}</dd></div>
          <div><dt>已实现 PnL</dt><dd>{{ perp.snapshot.value.pnl?.realizedPnl ?? '0' }}</dd></div>
          <div><dt>订单状态</dt><dd>{{ perp.lastOrder.value?.status ?? '—' }}</dd></div>
        </dl>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';

  import { usePlatformTrading } from '/@/hooks/trading/usePlatformTrading';
  import type { FundingExchange, FundingSymbol } from '../types';

  const props = defineProps<{
    exchange: FundingExchange;
    symbol: FundingSymbol;
  }>();

  const accountId = import.meta.env.VITE_PLATFORM_DEMO_ACCOUNT_ID || '10000000-0000-4000-8000-000000000001';

  const instrumentIds: Record<FundingSymbol, { spot: string; perp: string }> = {
    BTC: { spot: '20000000-0000-4000-8000-000000000001', perp: '30000000-0000-4000-8000-000000000001' },
    ETH: { spot: '20000000-0000-4000-8000-000000000002', perp: '30000000-0000-4000-8000-000000000002' },
    SOL: { spot: '20000000-0000-4000-8000-000000000003', perp: '30000000-0000-4000-8000-000000000003' },
    DOGE: { spot: '20000000-0000-4000-8000-000000000004', perp: '30000000-0000-4000-8000-000000000004' },
    XRP: { spot: '20000000-0000-4000-8000-000000000005', perp: '30000000-0000-4000-8000-000000000005' },
    XAUT: { spot: '20000000-0000-4000-8000-000000000006', perp: '30000000-0000-4000-8000-000000000006' },
  };

  const direction = ref<'collect' | 'pay'>('collect');
  const orderType = ref<'market' | 'limit'>('market');
  const quantity = ref('0.01');
  const price = ref('100');
  const successMessage = ref('');
  const localError = ref('');

  const spot = usePlatformTrading();
  const perp = usePlatformTrading();

  const spotSymbol = computed(() => `${props.symbol}USDT`);
  const perpSymbol = computed(() => `${props.symbol}USDT-PERP`);
  const instruments = computed(() => instrumentIds[props.symbol]);
  const overallBusy = computed(() => spot.busy.value || perp.busy.value);
  const errorMessage = computed(() => localError.value || spot.errorMessage.value || perp.errorMessage.value || '');
  const canSubmit = computed(() => Number(quantity.value) > 0 && (orderType.value === 'market' || Number(price.value) > 0));

  async function refreshBoth() {
    localError.value = '';
    successMessage.value = '';
    try {
      await Promise.all([
        spot.refresh(accountId, instruments.value.spot),
        perp.refresh(accountId, instruments.value.perp),
      ]);
    } catch {
      localError.value = '刷新失败，请确认 Platform Backend 已启动。';
    }
  }

  async function submitPair() {
    if (!canSubmit.value) return;

    localError.value = '';
    successMessage.value = '';
    const spotSide = direction.value === 'collect' ? 'buy' : 'sell';
    const perpSide = direction.value === 'collect' ? 'sell' : 'buy';
    const limitPrice = orderType.value === 'limit' ? price.value : undefined;

    try {
      await spot.submit({
        accountId,
        instrumentId: instruments.value.spot,
        symbol: spotSymbol.value,
        side: spotSide,
        orderType: orderType.value,
        quantity: quantity.value,
        price: limitPrice,
      });
      await perp.submit({
        accountId,
        instrumentId: instruments.value.perp,
        symbol: perpSymbol.value,
        side: perpSide,
        orderType: orderType.value,
        quantity: quantity.value,
        price: limitPrice,
      });
      successMessage.value = `双腿订单已执行：${spotSide} ${spotSymbol.value}，${perpSide} ${perpSymbol.value}。`;
    } catch {
      localError.value = '双腿订单未完整执行，请根据两腿订单状态检查结果。';
    }
  }

  watch(
    () => [props.exchange, props.symbol],
    () => {
      void refreshBoth();
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

  h3 { color: #162845; font-size: 18px; }
  .panel-head p { margin-top: 4px; color: #718096; font-size: 13px; }
  .status { padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
  .is-ready { color: #138a52; background: #eaf8f1; }
  .is-busy { color: #9a6700; background: #fff7df; }

  .order-grid,
  .snapshot-grid {
    display: grid;
    gap: 12px;
    margin-top: 16px;
  }

  .order-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .snapshot-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  label { display: grid; gap: 6px; color: #5d6d80; font-size: 12px; font-weight: 700; }
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

  .actions { justify-content: flex-start; margin-top: 16px; }
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
  button.secondary { color: #32445d; background: #edf2f7; }
  button:disabled { cursor: not-allowed; opacity: 0.55; }

  .error-message,
  .success-message { margin-top: 12px; font-size: 13px; font-weight: 700; }
  .error-message { color: #d4380d; }
  .success-message { color: #138a52; }

  article { padding: 14px; border: 1px solid #e6ebf2; border-radius: 12px; background: #fbfdff; }
  .leg-title span { color: #718096; font-size: 12px; }
  dl { display: grid; gap: 8px; margin-top: 12px; }
  dt { color: #718096; }
  dd { margin: 0; color: #162845; font-weight: 800; }

  @media (max-width: 1000px) {
    .order-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }

  @media (max-width: 680px) {
    .order-grid,
    .snapshot-grid { grid-template-columns: 1fr; }
    .panel-head { align-items: flex-start; }
  }
</style>
