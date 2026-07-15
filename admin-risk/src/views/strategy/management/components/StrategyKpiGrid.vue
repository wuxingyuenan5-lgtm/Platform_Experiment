<template>
  <section class="kpi-grid">
    <article v-for="item in items" :key="item.label" class="kpi-card">
      <label>{{ item.label }}</label>
      <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">
        {{ item.value }}
        <span v-if="item.unit">{{ item.unit }}</span>
      </strong>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyKpiCard } from '../types';
  defineProps<{ items: StrategyKpiCard[] }>();
</script>

<style scoped lang="less">
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: var(--strategy-space-2);
  }
  .kpi-card {
    padding: 14px 16px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }
  .kpi-card label {
    display: block;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }
  .kpi-card strong {
    display: block;
    margin: 8px 0 0;
    font-size: 24px;
    line-height: 1.1;
    font-weight: 800;
  }
  .kpi-card strong span {
    margin-left: 4px;
    font-size: var(--strategy-font-xs);
    font-weight: 600;
    color: var(--strategy-text-3);
  }
  .is-positive { color: #1d9f6e; }
  .is-negative { color: #d8585f; }
  .is-neutral { color: #1f2e3d; }
  @media (max-width: 1480px) {
    .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  }
  @media (max-width: 860px) {
    .kpi-grid { grid-template-columns: 1fr; }
  }
</style>
