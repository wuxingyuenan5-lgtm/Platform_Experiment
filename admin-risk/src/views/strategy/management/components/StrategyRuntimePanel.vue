<template>
  <section class="runtime-grid" v-if="cards.length">
    <article v-for="item in cards" :key="item.title" class="runtime-card">
      <header>
        <div>
          <h3>{{ item.title }}</h3>
        </div>
        <strong>{{ item.centerValue }}</strong>
      </header>

      <div
        class="runtime-ring"
        :style="{
          background: `conic-gradient(${item.startColor || '#3f7cff'} 0 ${item.progress}%, ${item.endColor || '#d9e5f7'} ${item.progress}% 100%)`,
        }"
      >
        <div class="runtime-ring__inner">
          <span>当前对照</span>
          <strong>{{ item.progress }}%</strong>
        </div>
      </div>

      <div class="runtime-ends">
        <article>
          <label>{{ item.leftLabel }}</label>
          <strong>{{ item.leftValue }}</strong>
          <span v-if="item.leftNote">{{ item.leftNote }}</span>
        </article>
        <article>
          <label>{{ item.rightLabel }}</label>
          <strong>{{ item.rightValue }}</strong>
          <span v-if="item.rightNote">{{ item.rightNote }}</span>
        </article>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyCapitalComparisonCard } from '../types';

  withDefaults(
    defineProps<{
      cards?: StrategyCapitalComparisonCard[];
    }>(),
    {
      cards: () => [],
    },
  );
</script>

<style scoped lang="less">
  .runtime-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .runtime-card {
    padding: 20px 22px;
    border-radius: 22px;
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
    border: 1px solid var(--strategy-border);
  }

  .runtime-card header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
  }

  .runtime-card h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 18px;
    font-weight: 700;
  }

  .runtime-card header strong {
    color: var(--strategy-text-1);
    font-size: 22px;
    line-height: 1.1;
    font-weight: 700;
    text-align: right;
  }

  .runtime-ring {
    display: grid;
    place-items: center;
    width: 184px;
    height: 184px;
    margin: 0 auto 18px;
    border-radius: 50%;
  }

  .runtime-ring__inner {
    display: grid;
    place-items: center;
    width: 132px;
    height: 132px;
    border-radius: 50%;
    background: var(--strategy-surface);
    text-align: center;
    box-shadow: inset 0 0 0 1px rgba(221, 229, 241, 0.85);
  }

  .runtime-ring__inner span {
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 600;
  }

  .runtime-ring__inner strong {
    margin-top: 6px;
    color: var(--strategy-text-1);
    font-size: 28px;
    line-height: 1.1;
    font-weight: 800;
  }

  .runtime-ends {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .runtime-ends article {
    padding: 14px 16px;
    border-radius: 16px;
    background: var(--strategy-surface-muted);
    border: 1px solid rgba(219, 228, 240, 0.9);
  }

  .runtime-ends label {
    display: block;
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .runtime-ends strong {
    display: block;
    margin-top: 10px;
    color: var(--strategy-text-1);
    font-size: 20px;
    line-height: 1.12;
    font-weight: 700;
  }

  .runtime-ends span {
    display: block;
    margin-top: 6px;
    color: var(--strategy-text-3);
    font-size: 13px;
    font-weight: 700;
  }

  @media (max-width: 1180px) {
    .runtime-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 860px) {
    .runtime-ends {
      grid-template-columns: 1fr;
    }
  }
</style>
