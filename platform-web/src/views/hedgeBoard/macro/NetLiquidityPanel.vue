<template>
  <section class="net-liquidity" aria-label="美元净流动性图表">
    <nav aria-label="美元净流动性视图">
      <button :aria-pressed="view === 'level'" @click="view = 'level'">净流动性走势</button>
      <button :aria-pressed="view === 'contributions'" @click="showContributions">
        分项贡献
      </button>
    </nav>
    <MacroSeriesChart v-if="view === 'level'" group-id="netLiquidity" unit-label="USD million" />
    <template v-else>
      <p v-if="loading" role="status">正在读取分项贡献…</p>
      <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
      <FinancingChart
        v-if="data?.history.length"
        title="净流动性变动 · 分项贡献"
        :rows="data.history"
        :lines="[
          {
            key: 'fedChange',
            name: 'Fed资产变动',
            color: '#2864ec',
            unit: '十亿美元',
            bar: true,
            stack: 'changes',
          },
          {
            key: 'tgaEffect',
            name: '−TGA变动',
            color: '#d09a14',
            unit: '十亿美元',
            bar: true,
            stack: 'changes',
          },
          {
            key: 'rrpEffect',
            name: '−ON RRP变动',
            color: '#00976f',
            unit: '十亿美元',
            bar: true,
            stack: 'changes',
          },
          { key: 'netChange', name: '净变动', color: '#171717', unit: '十亿美元' },
        ]"
      />
      <p v-else-if="!loading && !error">暂无有效分项贡献数据。</p>
    </template>
  </section>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, ref, shallowRef } from 'vue';
  import MacroSeriesChart from '../charts/MacroSeriesChart';
  import FinancingChart from '../aShare/components/FinancingChart.vue';
  import { getLiquidityLens, type LiquidityLens } from '@/api/marketAnalytics';

  const view = ref<'level' | 'contributions'>('level');
  const data = shallowRef<LiquidityLens>();
  const loading = ref(false),
    error = ref('');
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    try {
      const result = await getLiquidityLens(current.signal);
      if (!current.signal.aborted) data.value = result;
    } catch {
      if (!current.signal.aborted) error.value = '分项贡献读取失败，可切回净流动性走势。';
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  function showContributions() {
    view.value = 'contributions';
    if (!data.value && !loading.value) void load();
  }
  onBeforeUnmount(() => controller?.abort());
</script>

<style scoped>
  .net-liquidity {
    min-width: 0;
  }

  nav {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }

  button {
    padding: 6px 12px;
    border: 1px solid #dbe4ee;
    border-radius: 7px;
    background: #fff;
    color: #40546b;
    font: inherit;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #a5bfff;
    background: #edf3ff;
    color: #2864ec;
  }
</style>
