<template>
  <section class="breadth-summary" aria-label="观察池参与度">
    <p>{{ config.breadthSubtitle }}。仅使用已结束日期的日线。</p>
    <div class="breadth-summary__cards">
      <article v-for="card in display.breadthCards" :key="card.id">
        <span>{{ card.title }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.tag }} · {{ card.delta }}</small>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { MarketDetailRow } from '@/api/hedgeResearch';
  import type { MarketTerminalPageConfig } from '../nativeData/marketTerminal';
  import { mergeTerminalMarket } from '../nativeData/marketDetailAdapter';

  const props = defineProps<{ config: MarketTerminalPageConfig; rows: MarketDetailRow[] }>();
  const display = computed(() => mergeTerminalMarket(props.config, props.rows));
</script>

<style scoped>
  .breadth-summary {
    margin: 12px 0 18px;
  }

  .breadth-summary p {
    color: var(--text-color-secondary, #64748b);
    font-size: 12px;
  }

  .breadth-summary__cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  article {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    border: 1px solid var(--border-color-base, #e2e8f0);
    border-radius: 8px;
  }

  strong {
    font-size: 22px;
    font-variant-numeric: tabular-nums;
  }

  small {
    color: var(--text-color-secondary, #64748b);
  }

  @media (max-width: 560px) {
    .breadth-summary__cards {
      grid-template-columns: 1fr;
    }
  }
</style>
