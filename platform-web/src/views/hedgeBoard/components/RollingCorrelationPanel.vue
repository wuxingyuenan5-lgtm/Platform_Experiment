<template>
  <section class="correlation-panel">
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="loading" role="status">正在计算…</p>
    <FinancingChart
      embedded
      independent-dates
      :bounds="[-1, 1]"
      title="BTC / 纳指、XAU · 滚动相关性"
      :rows="rows"
      :lines="lines"
    >
      <template #toolbar>
        <div class="controls">
          <label
            >滚动窗口 N<input v-model.number="window" type="number" min="10" max="252" step="1"
          /></label>
          <button :disabled="loading" @click="load">应用</button>
          <span>共同交易区间 · 当前 N={{ windowUsed }}</span>
        </div>
      </template>
    </FinancingChart>
    <p v-if="lines.length && !rows.some((row) => row.ndx != null || row.xau != null)">
      共同有效样本不足，暂不能计算该窗口。
    </p>
    <div class="sources">
      <a
        v-for="source in sources"
        :key="source.url"
        :href="source.url"
        target="_blank"
        rel="noopener noreferrer"
        >{{ source.label }} ↗</a
      >
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
  import FinancingChart, { type FinanceRow } from '../aShare/components/FinancingChart.vue';
  import { researchRequest } from '@/api/hedgeResearch';

  type Benchmark = 'ndx' | 'xau';
  interface CorrelationData {
    rows: Array<{ date: string; correlation: string | null }>;
    note: string;
    sources: Array<string | null>;
  }
  const benchmarks = [
    {
      key: 'ndx' as const,
      name: 'BTC / 纳指',
      sourceLabel: '纳指价格来源',
      color: '#2864ec',
      unit: '相关系数',
    },
    {
      key: 'xau' as const,
      name: 'BTC / XAUUSD',
      sourceLabel: 'XAUUSD价格来源',
      color: '#c7931a',
      unit: '相关系数',
    },
  ];
  const window = ref(20),
    windowUsed = ref(20),
    loading = ref(false),
    error = ref('');
  const data = ref<Partial<Record<Benchmark, CorrelationData>>>({});
  const lines = computed(() => benchmarks.filter((item) => data.value[item.key]));
  const rows = computed(() => {
    const byDate = new Map<string, FinanceRow>();
    for (const benchmark of benchmarks) {
      for (const point of data.value[benchmark.key]?.rows ?? []) {
        const row = byDate.get(point.date) ?? { date: point.date };
        row[benchmark.key] = point.correlation;
        byDate.set(point.date, row);
      }
    }
    return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
  });
  const sources = computed(() => {
    const urls = new Map<string, string>();
    for (const benchmark of benchmarks) {
      (data.value[benchmark.key]?.sources ?? []).forEach((url, index) => {
        if (url) urls.set(url, index === 0 ? 'BTC价格来源' : benchmark.sourceLabel);
      });
    }
    return [...urls].map(([url, label]) => ({ url, label }));
  });
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
    const results = await Promise.allSettled(
      benchmarks.map((benchmark) =>
        researchRequest<CorrelationData>({
          url: '/research/crypto/rolling-correlation',
          method: 'GET',
          params: { n: requestedWindow, benchmark: benchmark.key },
          signal: active.signal,
        }),
      ),
    );
    if (active.signal.aborted) return;
    const next: Partial<Record<Benchmark, CorrelationData>> = {};
    const failed: string[] = [];
    results.forEach((result, index) => {
      if (result.status === 'fulfilled') next[benchmarks[index].key] = result.value;
      else failed.push(benchmarks[index].name);
    });
    data.value = next;
    windowUsed.value = requestedWindow;
    error.value = failed.length ? `${failed.join('、')}相关性暂不可用。` : '';
    loading.value = false;
  }
  onMounted(load);
  onBeforeUnmount(() => controller?.abort());
</script>

<style scoped>
  .correlation-panel {
    min-width: 0;
    padding: 0 20px 16px;
  }

  .controls,
  .controls label {
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
    flex-wrap: wrap;
    gap: 14px;
    font-size: 12px;
  }

  .controls span {
    color: #708397;
  }
</style>
