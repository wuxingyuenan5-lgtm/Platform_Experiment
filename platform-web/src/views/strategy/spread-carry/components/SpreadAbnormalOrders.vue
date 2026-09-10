<template>
  <section v-if="orders.length" class="abnormal-orders">
    <header
      ><h3>跨所价差异常订单</h3><span>{{ orders.length }} 项待处理</span></header
    >
    <p>以下仓位单独核对，不计入正常组合持仓。数量来自已确认成交；未知结果须先对账。</p>
    <article v-for="row in orders" :key="row.batchId">
      <div class="abnormal-orders__title">
        <strong>{{ row.label }}</strong>
        <span>{{ row.direction === 'LONG_SPREAD' ? '多价差' : '空价差' }}</span>
        <span v-if="row.mt5PositionId">MT5 Ticket {{ row.mt5PositionId }}</span>
      </div>
      <div class="abnormal-orders__legs">
        <div
          ><b>Bybit</b><span>已平 {{ row.bybitCloseFilledQuantity }} XAUT</span>
          <strong>剩余 {{ row.bybitRemainingQuantity ?? '待核对' }} XAUT</strong></div
        >
        <div
          ><b>MT5</b><span>已平 {{ row.mt5CloseFilledQuantity }} 手</span>
          <strong>剩余 {{ row.mt5RemainingQuantity ?? '待核对' }} 手</strong></div
        >
      </div>
      <p v-if="row.reason" class="abnormal-orders__reason">上次失败：{{ row.reason }}</p>
      <div class="abnormal-orders__action">
        <span v-if="row.action === 'finish_mt5'"
          >Bybit 已成交，本次只处理原 MT5 Ticket 的剩余平仓。</span
        >
        <span v-else-if="row.action === 'reconcile'">存在未决执行，请先核对原订单与成交。</span>
        <button
          v-if="row.planId && row.action !== 'reconcile'"
          type="button"
          :disabled="busy || submitting || !canTrade"
          @click="$emit('close-plan', row.planId)"
        >
          {{ row.action === 'finish_mt5' ? '处理剩余 MT5 平仓' : '处理该组合平仓' }}
        </button>
        <button
          v-else-if="row.action === 'flatten_open'"
          type="button"
          :disabled="busy || submitting || !canTrade"
          @click="pendingBatch = row.batchId"
          >平掉已成交单腿</button
        >
      </div>
      <div v-if="pendingBatch === row.batchId" class="abnormal-orders__action">
        <strong>确认市价平掉此异常开仓的 Bybit {{ row.bybitRemainingQuantity }} XAUT？</strong>
        <button type="button" :disabled="submitting" @click="pendingBatch = null">取消</button>
        <button type="button" :disabled="submitting" @click="confirmFlatten(row.batchId)"
          >确认平仓</button
        >
      </div>
    </article>
    <p v-if="message" role="status">{{ message }}</p>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useUserStore } from '@/store/modules/user';
  import { closeAbnormalOpen } from '@/api/platform/crossSpreadLifecycle';
  import type { CrossSpreadPositionOverviewResult } from '@/api/platform/trading.types';
  defineProps<{
    orders: CrossSpreadPositionOverviewResult['abnormalOrders'];
    busy: boolean;
  }>();
  const emit = defineEmits<{
    (event: 'close-plan', planId: string): void;
    (event: 'settled'): void;
  }>();
  const user = useUserStore();
  const canTrade = computed(() => user.authentication?.user.role === 'ceo');
  const pendingBatch = ref<string | null>(null);
  const submitting = ref(false);
  const message = ref('');
  async function confirmFlatten(batchId: string) {
    if (submitting.value || !canTrade.value) return;
    submitting.value = true;
    try {
      const result = await closeAbnormalOpen(batchId, user.authentication!.user.userId);
      message.value =
        result.status === 'completed'
          ? '异常单腿已平仓'
          : `平仓尚未完成：${result.failureReason || result.status}`;
    } catch (error) {
      message.value =
        '平仓回执尚未确认，请核对原风险处理记录；重复点击沿用同一请求，不会另建订单。';
    } finally {
      submitting.value = false;
      pendingBatch.value = null;
      emit('settled');
    }
  }
</script>

<style scoped>
  .abnormal-orders {
    margin: 16px 0;
    padding: 20px;
    border: 1px solid #e9bcb6;
    border-radius: 14px;
    background: #fffaf8;
    color: #25344a;
  }
  header,
  .abnormal-orders__title,
  .abnormal-orders__action {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 14px;
  }
  header {
    justify-content: space-between;
  }
  h3 {
    margin: 0;
    font-size: 18px;
  }
  p {
    margin: 10px 0;
    font-size: 13px;
    color: #697586;
  }
  article {
    margin-top: 14px;
    padding: 16px;
    border: 1px solid #ecd7d2;
    border-radius: 10px;
    background: white;
  }
  .abnormal-orders__title > strong {
    color: #ae342b;
  }
  .abnormal-orders__title > span {
    font-size: 12px;
  }
  .abnormal-orders__legs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin: 14px 0;
  }
  .abnormal-orders__legs > div {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 18px;
    padding: 12px;
    background: #f8fafc;
    border-radius: 6px;
    font-size: 13px;
  }
  .abnormal-orders__legs b {
    width: 100%;
  }
  .abnormal-orders__reason {
    overflow-wrap: anywhere;
    color: #9c443a;
  }
  .abnormal-orders__action {
    justify-content: space-between;
    font-size: 13px;
  }
  button {
    padding: 9px 16px;
    border: 1px solid #b54a3d;
    border-radius: 6px;
    background: white;
    color: #a23127;
    cursor: pointer;
  }
  button:disabled {
    opacity: 0.5;
    cursor: wait;
  }
  button:focus-visible {
    outline: 2px solid #a23127;
    outline-offset: 3px;
  }
  @media (max-width: 680px) {
    .abnormal-orders__legs {
      grid-template-columns: 1fr;
    }
  }
</style>
