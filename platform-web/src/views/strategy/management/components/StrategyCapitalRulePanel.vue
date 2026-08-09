<template>
  <section class="rule-panel">
    <header class="rule-panel__header">
      <div>
        <h3>{{ panel.title }}</h3>
      </div>
      <div class="rule-status" :class="panel.tone ? `is-${panel.tone}` : 'is-neutral'">
        <strong>{{ panel.status }}</strong>
      </div>
    </header>

    <div class="rule-metrics">
      <article v-for="item in panel.metrics" :key="item.label" class="rule-metric">
        <label>{{ item.label }}</label>
        <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
      </article>
    </div>

    <article class="rule-alerts">
      <header>
        <h4>最近提醒</h4>
      </header>
      <ul>
        <li v-for="item in panel.alerts" :key="`${item.time}-${item.text}`">
          <time>{{ item.time }}</time>
          <p :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.text }}</p>
        </li>
      </ul>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyCapitalRulePanel } from '@/data/sample/strategy';

  defineProps<{
    panel: StrategyCapitalRulePanel;
  }>();
</script>

<style scoped lang="less">
  .rule-panel {
    display: grid;
    gap: var(--strategy-space-2);
    padding: 18px 20px;
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    border: 1px solid var(--strategy-border);
    box-shadow: var(--strategy-shadow-card);
  }

  .rule-panel__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .rule-panel__header h3,
  .rule-alerts h4 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .rule-status {
    min-width: 220px;
    padding: 14px 16px;
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface-muted);
    border: 1px solid var(--strategy-border-strong);
    box-shadow: var(--strategy-shadow-soft);
  }

  .rule-status strong {
    display: block;
    font-size: 20px;
    line-height: 1.1;
  }

  .rule-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--strategy-space-2);
  }

  .rule-metric {
    padding: 14px 16px;
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    border: 1px solid var(--strategy-border);
    box-shadow: var(--strategy-shadow-soft);
  }

  .rule-metric label {
    display: block;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .rule-metric strong {
    display: block;
    margin-top: 10px;
    font-size: 20px;
    line-height: 1.12;
    color: var(--strategy-text-1);
  }

  .rule-alerts {
    padding: 14px 16px;
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    border: 1px solid var(--strategy-border);
    box-shadow: var(--strategy-shadow-soft);
  }

  .rule-alerts header {
    margin-bottom: 12px;
  }

  .rule-alerts ul {
    display: grid;
    gap: 12px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .rule-alerts li {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--strategy-border-soft);
  }

  .rule-alerts li:last-child {
    padding-bottom: 0;
    border-bottom: none;
  }

  .rule-alerts time {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 600;
  }

  .rule-alerts p {
    margin: 0;
    font-size: var(--strategy-font-base);
    line-height: 1.5;
  }

  .is-positive {
    color: var(--strategy-success) !important;
  }

  .is-negative {
    color: var(--strategy-danger) !important;
  }

  .is-neutral {
    color: var(--strategy-text-1) !important;
  }

  @media (max-width: 1180px) {
    .rule-metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 860px) {
    .rule-panel__header,
    .rule-alerts li {
      grid-template-columns: 1fr;
      flex-direction: column;
    }

    .rule-metrics {
      grid-template-columns: 1fr;
    }

    .rule-status {
      min-width: 0;
    }
  }
</style>
