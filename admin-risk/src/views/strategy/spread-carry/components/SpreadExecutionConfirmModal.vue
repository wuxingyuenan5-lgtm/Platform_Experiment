<template>
  <div v-if="visible" class="trade-modal" @click.self="$emit('close')">
    <div class="trade-modal__dialog">
      <div class="trade-modal__header">
        <div>
          <p class="trade-modal__eyebrow">SPREAD ORDER CONFIRM</p>
          <h3>确认价差指令</h3>
        </div>
        <button class="trade-modal__close" @click="$emit('close')">x</button>
      </div>

      <div class="trade-modal__body">
        <div class="confirm-grid">
          <div><span>交易对</span><strong>{{ leftLegSymbol }} - {{ rightLegSymbol }}</strong></div>
          <div><span>动作</span><strong>{{ summary.action }}</strong></div>
          <div><span>盎司</span><strong>{{ summary.qty }}</strong></div>
          <div><span>BYBIT / MT5</span><strong>{{ summary.legs }}</strong></div>
          <div><span>执行方式</span><strong>{{ summary.mode }}</strong></div>
          <div><span>当前执行价差</span><strong>{{ summary.marketSpread }}</strong></div>
          <div><span>触发 / 接受</span><strong>{{ summary.spreadRange }}</strong></div>
          <div><span>止盈</span><strong>{{ summary.takeProfit }}</strong></div>
          <div><span>止损</span><strong>{{ summary.stopLoss }}</strong></div>
        </div>
        <div v-if="guardMessage" class="confirm-guard">
          <span>执行前检查</span>
          <strong>{{ guardMessage }}</strong>
        </div>
      </div>

      <div class="trade-modal__footer">
        <button class="modal-btn modal-btn--ghost" @click="$emit('close')">取消</button>
        <button class="modal-btn modal-btn--primary" :disabled="submitLoading" @click="$emit('confirm')">
          {{ submitLoading ? '执行中...' : '确认执行' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  interface ConfirmSummary {
    action: string;
    qty: string;
    legs: string;
    mode: string;
    marketSpread: string;
    spreadRange: string;
    takeProfit: string;
    stopLoss: string;
  }

  defineProps<{
    visible: boolean;
    submitLoading: boolean;
    leftLegSymbol: string;
    rightLegSymbol: string;
    summary: ConfirmSummary;
    guardMessage: string;
  }>();

  defineEmits<{
    (event: 'close'): void;
    (event: 'confirm'): void;
  }>();
</script>

<style scoped lang="less">
  .trade-modal {
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(11, 21, 42, 0.3);
  }

  .trade-modal__dialog {
    width: calc(100vw - 32px);
    max-width: 620px;
    border: 1px solid var(--strategy-border);
    border-radius: 20px;
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow, 0 30px 60px rgba(23, 41, 72, 0.24));
  }

  .trade-modal__header,
  .trade-modal__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px;
  }

  .trade-modal__header {
    border-bottom: 1px solid #edf2f8;
  }

  .trade-modal__body {
    padding: 18px 20px 22px;
  }

  .trade-modal__eyebrow {
    display: none;
  }

  .trade-modal__header h3 {
    margin: 0;
    color: #172947;
    font-size: 20px;
    font-weight: 800;
  }

  .trade-modal__close {
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    color: #678;
    font-size: 20px;
    cursor: pointer;
  }

  .confirm-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .confirm-grid div {
    padding: 12px 14px;
    border: 1px solid #e3ebf6;
    border-radius: 12px;
    background: #fbfdff;
  }

  .confirm-grid span {
    display: block;
    margin-bottom: 8px;
    color: #7b8aa5;
    font-size: 12px;
    font-weight: 700;
  }

  .confirm-grid strong {
    color: #172947;
    font-size: 15px;
    font-weight: 800;
  }

  .confirm-guard {
    margin-top: 12px;
    padding: 12px 14px;
    border: 1px solid rgba(217, 43, 43, 0.22);
    border-radius: 12px;
    background: rgba(217, 43, 43, 0.06);
  }

  .confirm-guard span {
    display: block;
    margin-bottom: 6px;
    color: #9f2d2d;
    font-size: 12px;
    font-weight: 800;
  }

  .confirm-guard strong {
    color: #c52626;
    font-size: 14px;
    font-weight: 800;
  }

  .modal-btn {
    height: 40px;
    padding: 0 18px;
    border: 1px solid #dfe7f4;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 800;
    cursor: pointer;
  }

  .modal-btn--ghost {
    background: #fff;
    color: #526581;
  }

  .modal-btn--primary {
    border-color: #ff4b4b;
    background: #ff4b4b;
    color: #fff;
  }

  @media (max-width: 960px) {
    .trade-modal__dialog {
      width: calc(100vw - 24px);
    }
  }
</style>

