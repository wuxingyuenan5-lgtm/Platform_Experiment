<template>
  <div class="research-source-state" :class="`is-${meta.status}`">
    <span class="research-source-state__dot" />
    <span>{{ statusLabel }}</span>
    <span class="research-source-state__source">{{ meta.source }}</span>
    <span class="research-source-state__time">{{ formattedTime }}</span>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { ResearchSourceMeta } from '@/api/hedgeResearch';

  const props = defineProps<{ meta: ResearchSourceMeta }>();

  const statusLabel = computed(() => {
    const labels: Record<ResearchSourceMeta['status'], string> = {
      loading: '加载中',
      ready: '可用',
      partial: '部分可用',
      no_data: '暂无数据',
      stale: '上一份有效数据',
      error: '暂不可用',
    };
    return labels[props.meta.status];
  });

  const formattedTime = computed(() => {
    if (!props.meta.fetchedAt) return '—';
    const value = new Date(props.meta.fetchedAt);
    if (Number.isNaN(value.getTime())) return '—';
    return value.toLocaleString('zh-CN', { hour12: false });
  });
</script>

<style scoped lang="less">
  .research-source-state {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .research-source-state__dot {
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: #10b981;
    flex: 0 0 auto;
  }

  .research-source-state.is-stale .research-source-state__dot,
  .research-source-state.is-partial .research-source-state__dot {
    background: #f59e0b;
  }

  .research-source-state.is-error .research-source-state__dot,
  .research-source-state.is-no_data .research-source-state__dot {
    background: #ef4444;
  }

  .research-source-state__source,
  .research-source-state__time {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .research-source-state__source::before {
    content: '·';
    margin-right: 6px;
  }

  .research-source-state__time {
    color: var(--strategy-text-4);
  }

  @media (max-width: 900px) {
    .research-source-state__source {
      display: none;
    }
  }
</style>
