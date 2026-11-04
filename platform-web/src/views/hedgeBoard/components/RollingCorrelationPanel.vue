<template
  ><section
    ><div class="controls"
      ><label
        >滚动窗口 N
        <input v-model.number="window" type="number" min="10" max="252" step="1" /></label
      ><button @click="load" :disabled="loading">应用</button><span>共同交易区间</span></div
    ><p v-if="error" role="alert">{{ error }}</p
    ><p v-if="loading">正在计算…</p
    ><FinancingChart
      embedded
      :bounds="[-1, 1]"
      v-if="data"
      :title="title"
      :rows="data.rows"
      :lines="[
        { key: 'correlation', name: `${windowUsed}区间相关性`, color: '#2864ec', unit: '相关系数' },
      ]"
      :note="data.note"
    /><p v-if="data && !data.rows.some((r) => r.correlation != null)"
      >共同有效样本不足，暂不能计算该窗口。</p
    ><div class="sources"
      ><a
        v-for="(url, i) in data?.sources || []"
        :key="i"
        :href="url || undefined"
        target="_blank"
        rel="noopener noreferrer"
        >{{ i === 0 ? 'BTC价格来源' : '对手价格来源' }} ↗</a
      ></div
    ></section
  ></template
>
<script setup lang="ts">
  import { ref, onMounted, onBeforeUnmount } from 'vue';
  import FinancingChart from '../aShare/components/FinancingChart.vue';
  import { researchRequest } from '@/api/hedgeResearch';

  const props = defineProps<{ benchmark: 'ndx' | 'xau' }>();
  const title =
    props.benchmark === 'ndx' ? 'BTC / 纳斯达克100 · 滚动相关性' : 'BTC / XAUUSD · 滚动相关性';
  const window = ref(20),
    windowUsed = ref(20),
    loading = ref(false),
    error = ref('');
  const data = ref<{
    rows: Array<{ date: string; correlation: string | null }>;
    note: string;
    sources: Array<string | null>;
  } | null>(null);
  let controller: AbortController | undefined;
  async function load() {
    if (!Number.isInteger(window.value) || window.value < 10 || window.value > 252) {
      error.value = 'N请输入10至252的整数';
      return;
    }
    controller?.abort();
    const requestedWindow = window.value;
    const active = new AbortController();
    controller = active;
    loading.value = true;
    error.value = '';
    try {
      const r = await researchRequest<NonNullable<typeof data.value>>({
        url: '/research/crypto/rolling-correlation',
        method: 'GET',
        params: { n: requestedWindow, benchmark: props.benchmark },
        signal: active.signal,
      });
      if (!active.signal.aborted) {
        data.value = r;
        windowUsed.value = requestedWindow;
      }
    } catch (e) {
      if (!active.signal.aborted) error.value = String(e);
    } finally {
      if (!active.signal.aborted) loading.value = false;
    }
  }
  onMounted(load);
  onBeforeUnmount(() => controller?.abort());</script
><style scoped>
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    font-size: 13px;
    gap: 10px;
  }

  .controls input {
    width: 85px;
  }

  input,
  button {
    padding: 6px 10px;
    border: 1px solid #dbe4ed;
    border-radius: 6px;
    background: #fff;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  .sources {
    display: flex;
    gap: 14px;
    font-size: 12px;
  }

  .controls span {
    color: #708397;
  }
</style>
