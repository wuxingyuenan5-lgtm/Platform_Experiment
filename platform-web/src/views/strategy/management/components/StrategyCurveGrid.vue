<template>
  <section class="curve-grid" data-testid="strategy-curve-grid">
    <article v-for="curve in curves" :key="curve.title">
      <header><h2>{{ curve.title }}</h2><span>Sample</span></header>
      <svg viewBox="0 0 320 120" preserveAspectRatio="none" role="img" :aria-label="curve.title">
        <polyline :points="toPoints(curve.points)" fill="none" stroke="currentColor" stroke-width="3" />
      </svg>
    </article>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    curves: Array<{ title: string; points: number[] }>;
  }>();

  function toPoints(values: number[]): string {
    if (!values.length) return '';
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = Math.max(max - min, 1);
    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * 320;
        const y = 105 - ((value - min) / range) * 90;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }
</script>

<style scoped lang="less">
  .curve-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  article {
    display: grid;
    gap: 12px;
    padding: 18px;
    border: 1px solid var(--strategy-border, #e4e9ef);
    border-radius: var(--strategy-radius-card, 14px);
    background: var(--strategy-surface, #fff);
    color: #6f83aa;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  h2 {
    margin: 0;
    color: var(--strategy-text-1, #1d2b3a);
    font-size: 16px;
  }

  header span {
    color: var(--strategy-text-3, #778396);
    font-size: 11px;
  }

  svg {
    width: 100%;
    height: 120px;
    border-radius: 10px;
    background: #fafbfd;
  }

  @media (max-width: 720px) {
    .curve-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
