<template>
  <section class="net-value-board" data-testid="strategy-capital-net-value-board">
    <header>
      <div>
        <span>账户资金</span>
        <h2>{{ curve.title }}</h2>
      </div>
      <em>Sample</em>
    </header>
    <svg viewBox="0 0 640 180" preserveAspectRatio="none" role="img" :aria-label="curve.title">
      <polyline :points="points" fill="none" stroke="currentColor" stroke-width="4" />
    </svg>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  const props = defineProps<{
    curve: { title: string; points: number[] };
  }>();

  const points = computed(() => {
    const values = props.curve.points;
    if (!values.length) return '';
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = Math.max(max - min, 1);
    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * 640;
        const y = 160 - ((value - min) / range) * 130;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  });
</script>

<style scoped lang="less">
  .net-value-board {
    display: grid;
    gap: 14px;
    padding: 18px;
    border: 1px solid var(--strategy-border, #e4e9ef);
    border-radius: var(--strategy-radius-card, 14px);
    background: var(--strategy-surface, #fff);
    color: #3a70b8;
  }

  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

  header span {
    color: var(--strategy-text-3, #778396);
  }

  h2 {
    margin: 4px 0 0;
    color: var(--strategy-text-1, #1d2b3a);
    font-size: 17px;
  }

  em {
    color: #8a6210;
    font-size: 11px;
    font-style: normal;
  }

  svg {
    width: 100%;
    height: 180px;
    border-radius: 12px;
    background:
      linear-gradient(to bottom, transparent 24%, #edf1f5 25%, transparent 26%) 0 0 / 100% 45px,
      #fafbfd;
  }
</style>
