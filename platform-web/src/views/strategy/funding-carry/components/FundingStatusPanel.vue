<template>
  <section class="panel status-panel">
    <div class="panel-title">
      <h3>交易规则</h3>
    </div>

    <div class="rule-list">
      <div v-for="item in tradingRules" :key="item.label" class="rule-list__row">
        <span class="rule-list__label">{{ item.label }}</span>
        <span class="rule-list__value">{{ item.value }}</span>
      </div>
    </div>

    <div class="status-feedback">
      <div class="status-feedback__head">
        <strong>执行反馈</strong>
        <button type="button" @click="$emit('clear')">清空</button>
      </div>

      <div class="status-feedback__list">
        <p v-for="item in feedbackRows" :key="item.id">
          <i :class="['status-feedback__dot', item.tone]"></i>
          <span>{{ item.time }}: {{ item.text }}</span>
        </p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    tradingRules: readonly {
      label: string;
      value: string;
    }[];
    feedbackRows: readonly {
      id: string;
      tone: 'is-success' | 'is-info';
      time: string;
      text: string;
    }[];
  }>();

  defineEmits<{
    (event: 'clear'): void;
  }>();
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

  .rule-list {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
  }

  .rule-list__row {
    min-height: 74px;
    padding: 12px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
  }

  .rule-list__label {
    display: block;
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .rule-list__value {
    display: block;
    margin-top: 8px;
    color: var(--strategy-text-1);
    font-size: 15px;
    font-weight: 800;
  }

  .status-feedback {
    margin-top: 14px;
    padding: 14px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
  }

  .status-feedback__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .status-feedback__head strong {
    color: var(--strategy-text-1);
    font-size: 14px;
    font-weight: 800;
  }

  .status-feedback__head button {
    border: none;
    background: transparent;
    color: var(--strategy-accent-strong);
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
  }

  .status-feedback__list {
    display: grid;
    gap: 8px;
    margin-top: 12px;
  }

  .status-feedback__list p {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .status-feedback__dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--strategy-text-3);
  }

  .status-feedback__dot.is-success {
    background: var(--strategy-success);
  }

  .status-feedback__dot.is-info {
    background: var(--strategy-accent);
  }

  @media (max-width: 1400px) {
    .rule-list {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 1024px) {
    .rule-list {
      gap: 10px;
    }
  }
</style>
