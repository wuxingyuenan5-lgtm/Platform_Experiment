<template>
  <section id="a-share-breadth" class="research-card">
    <header class="research-card__header">
      <div>
        <p class="research-card__eyebrow">MARKET BREADTH</p>
        <h2>大盘广度</h2>
      </div>
      <ResearchSourceState v-if="module" :meta="module.meta" />
    </header>

    <div v-if="data" class="breadth-grid">
      <article v-for="item in cards" :key="item.label" class="breadth-card">
        <span>{{ item.label }}</span>
        <strong :class="item.tone">{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </article>
    </div>
    <div v-else class="research-empty">{{ module?.meta.message || '暂无市场广度数据' }}</div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { AShareBreadthSnapshot, ResearchModuleResult } from '@/api/hedgeResearch';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';

  const props = defineProps<{ module?: ResearchModuleResult<AShareBreadthSnapshot> | null }>();
  const data = computed(() => props.module?.data || null);
  const cards = computed(() => {
    const value = data.value;
    if (!value) return [];
    return [
      { label: '上涨', value: value.up, note: '当日上涨家数', tone: 'is-positive' },
      { label: '下跌', value: value.down, note: '当日下跌家数', tone: 'is-negative' },
      { label: '平盘', value: value.flat, note: '当日平盘家数', tone: '' },
      { label: '涨停 / 真实涨停', value: `${value.limitUp} / ${value.realLimitUp}`, note: '来源原始口径', tone: 'is-positive' },
      { label: '跌停 / 真实跌停', value: `${value.limitDown} / ${value.realLimitDown}`, note: '来源原始口径', tone: 'is-negative' },
      { label: '活跃度', value: value.activityPct == null ? '—' : `${value.activityPct}%`, note: '赚钱效应活跃度', tone: '' },
      { label: '市场宽度', value: value.breadthState, note: value.tradeDate || '最新交易日', tone: '' },
      { label: '题材投机', value: value.speculationState, note: '按真实涨停数量分类', tone: '' },
    ];
  });
</script>

<style scoped lang="less">
  .research-card {
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .research-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;
  }

  .research-card__eyebrow {
    margin: 0 0 3px;
    color: var(--strategy-text-4);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  h2 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 18px;
  }

  .breadth-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .breadth-card {
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface-2);
  }

  .breadth-card span,
  .breadth-card small {
    display: block;
    color: var(--strategy-text-3);
  }

  .breadth-card strong {
    display: block;
    margin: 8px 0 4px;
    color: var(--strategy-text-1);
    font-size: 22px;
    font-variant-numeric: tabular-nums;
  }

  .is-positive { color: var(--strategy-up, #ef4444) !important; }
  .is-negative { color: var(--strategy-down, #10b981) !important; }

  .research-empty {
    padding: 30px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  @media (max-width: 1100px) {
    .breadth-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }

  @media (max-width: 640px) {
    .research-card__header { flex-direction: column; }
    .breadth-grid { grid-template-columns: 1fr; }
  }
</style>
