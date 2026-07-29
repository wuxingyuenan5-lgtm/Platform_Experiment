<template>
  <section class="cross-card cross-card--status">
    <div class="card-head">
      <div>
        <h3>交易规则</h3>
      </div>
    </div>

    <div class="rule-list">
      <div v-for="item in tradingRuleRows" :key="item.label" class="rule-list__row">
        <span class="rule-list__label">{{ item.label }}</span>
        <span class="rule-list__value">{{ item.value }}</span>
      </div>
    </div>

    <div class="status-mini-log">
      <div class="status-mini-log__head">
        <strong>执行反馈</strong>
      </div>

      <div class="status-mini-log__list">
        <p v-for="item in executionLogs.slice(0, 4)" :key="item.id">
          <i :class="['status-mini-log__dot', item.status === '成功' ? 'is-success' : item.status === '待确认' ? 'is-warn' : 'is-info']"></i>
          <span>{{ item.time }}: {{ item.direction }} {{ item.type }}</span>
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  interface TradingRuleRow {
    label: string;
    value: string;
  }

  interface ExecutionLogRow {
    id: string;
    time: string;
    direction: string;
    type: string;
    status: string;
  }

  defineProps<{
    tradingRuleRows: readonly TradingRuleRow[];
    executionLogs: readonly ExecutionLogRow[];
  }>();
</script>

<style scoped lang="less">
  .cross-card {
    padding: 16px 18px 18px;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .cross-card--status {
    padding: 14px;
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .card-head h3 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.012em;
    color: #162845;
  }

  .rule-list {
    display: grid;
    gap: 10px;
  }

  .rule-list__row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    min-height: 40px;
    padding: 0 12px;
    border: 1px solid #e6ebf2;
    border-radius: 10px;
    background: #fff;
  }

  .rule-list__label {
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
  }

  .rule-list__value {
    color: #475467;
    font-size: 13px;
    font-weight: 800;
    text-align: right;
  }

  .status-mini-log {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #eef2f7;
  }

  .status-mini-log__head {
    margin-bottom: 10px;
  }

  .status-mini-log__head strong {
    color: #111827;
    font-size: 16px;
    font-weight: 800;
  }

  .status-mini-log__list {
    display: grid;
    gap: 10px;
  }

  .status-mini-log__list p {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 0;
    color: #475467;
    font-size: 13px;
    line-height: 1.55;
  }

  .status-mini-log__dot {
    width: 8px;
    height: 8px;
    margin-top: 5px;
    border-radius: 999px;
    flex: none;
  }

  .status-mini-log__dot.is-success {
    background: #22c55e;
  }

  .status-mini-log__dot.is-warn {
    background: #f59e0b;
  }

  .status-mini-log__dot.is-info {
    background: #60a5fa;
  }
</style>
