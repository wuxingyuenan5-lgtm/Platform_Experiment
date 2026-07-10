<template>
  <section class="kpi-grid">
    <article v-for="item in items" :key="item.label" class="kpi-card">
      <label>{{ item.label }}</label>
      <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">
        {{ item.value }}
        <span v-if="item.unit">{{ item.unit }}</span>
      </strong>
      <p>{{ item.note }}</p>
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
    gap: 10px;
  }
  .kpi-card {
    padding: 14px 16px 12px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.88);
    box-shadow: inset 0 0 0 1px rgba(229, 235, 243, 0.92);
  }
  .kpi-card label,
  .kpi-card p {
    display: block;
  }
  .kpi-card label {
    color: var(--strategy-text-3);
    font-size: 11px;
    font-weight: 700;
  }
  .kpi-card strong {
    display: block;
    margin: 8px 0 4px;
    font-size: 24px;
    line-height: 1.1;
  }
  .kpi-card strong span {
    margin-left: 4px;
    font-size: 11px;
    font-weight: 600;
    color: var(--strategy-text-3);
  }
  .kpi-card p {
    margin: 0;
    color: var(--strategy-text-3);
    font-size: 11px;
    line-height: 1.45;
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
