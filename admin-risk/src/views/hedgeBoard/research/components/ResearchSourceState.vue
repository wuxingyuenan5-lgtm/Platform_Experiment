<template>
  <div
    class="research-source-state"
    :class="`is-${meta.status}`"
    :title="detailTitle"
    :aria-label="detailTitle"
  >
    <span class="research-source-state__dot"></span>
    <span>{{ statusLabel }}</span>
    <span class="research-source-state__source">{{ meta.source || '未知来源' }}</span>
    <span class="research-source-state__time">{{ displayedTime }}</span>
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

  function formatTimestamp(value?: string | null) {
    if (!value) return '—';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '—';
    return parsed.toLocaleString('zh-CN', { hour12: false });
  }

  const sourceTime = computed(() => formatTimestamp(props.meta.sourceTimestamp));
  const fetchedTime = computed(() => formatTimestamp(props.meta.fetchedAt));
  const displayedTime = computed(() =>
    props.meta.sourceTimestamp ? `源 ${sourceTime.value}` : `抓取 ${fetchedTime.value}`,
  );
  const detailTitle = computed(() => {
    const details = [
      `状态：${statusLabel.value}`,
      `来源：${props.meta.source || '未知来源'}`,
      `源数据时间：${sourceTime.value}`,
      `平台抓取时间：${fetchedTime.value}`,
    ];
    if (props.meta.message) details.push(`说明：${props.meta.message}`);
    if (props.meta.errorCode) details.push(`错误码：${props.meta.errorCode}`);
    return details.join('；');
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

  .research-source-state.is-loading .research-source-state__dot {
    background: #3b82f6;
    animation: source-state-pulse 1s infinite alternate;
  }

  .research-source-state.is-stale .research-source-state__dot,
  .research-source-state.is-partial .research-source-state__dot {
    background: #f59e0b;
  }

  .research-source-state.is-error .research-source-state__dot {
    background: #ef4444;
  }

  .research-source-state.is-no_data .research-source-state__dot {
    background: var(--strategy-text-4);
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

  @keyframes source-state-pulse {
    from {
      opacity: 0.35;
    }
    to {
      opacity: 1;
    }
  }

  @media (max-width: 900px) {
    .research-source-state__source {
      display: none;
    }
  }
</style>
