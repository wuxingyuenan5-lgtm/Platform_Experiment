<template>
  <section class="research-supplement">
    <div class="research-controls"
      ><h3>{{ title }}</h3
      ><label
        >历史区间
        <select v-model.number="days"
          ><option :value="252">近一年</option
          ><option :value="756">近三年</option></select
        ></label
      ></div
    >
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <ResearchScatter
      :title="title"
      :subtitle="`${points[0]?.name || '—'} 至 ${points.at(-1)?.name || '—'} · ${
        points.length
      }组同日配对`"
      :points="points"
      x-label="沪深300日涨跌（%）"
      :y-label="mode === 'etf' ? '样本ETF申赎估算（亿元）' : '融资余额日变化（亿元）'"
      :fit="fit?.line"
      >相关系数 {{ fmt(fit?.correlation, 3) }} · R² {{ fmt(fit?.r2, 3) }}</ResearchScatter
    >
    <p class="research-note"
      >{{
        mode === 'etf'
          ? 'ETF为平台25只观察池，包含跨境与非股票产品，不代表全市场股票ETF。'
          : '融资使用沪深融资余额日变化，不等于融资买入额。'
      }}市场使用沪深300收盘；按同日有效值配对，不填补缺口。相关关系不代表因果。</p
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef, onMounted, onBeforeUnmount } from 'vue';
  import type { CapitalDashboard } from '@/api/platform/aShareCapital';
  import { researchRequest } from '@/api/hedgeResearch';
  import ResearchScatter from './ResearchScatter.vue';
  import {
    capitalComparison,
    pairedCapitalPoints,
    linearFit,
    formatResearch as fmt,
  } from './researchFrameworkAnalysis';

  const props = defineProps<{ data: CapitalDashboard; mode: 'etf' | 'financing' }>();
  const days = ref(756),
    error = ref('');
  const prices = shallowRef<Array<{ date: string; value: unknown }>>([]);
  let abort: AbortController | undefined;
  async function load() {
    abort?.abort();
    const current = (abort = new AbortController());
    error.value = '';
    try {
      const d = await researchRequest<{
        sources: { turnover?: { data: Array<{ date: string; close: unknown }> } };
      }>({ method: 'GET', url: '/research/a-share/crowding-research', signal: current.signal });
      if (!current.signal.aborted)
        prices.value = (d.sources.turnover?.data || []).map((r) => ({
          date: r.date,
          value: r.close,
        }));
    } catch {
      if (!current.signal.aborted) error.value = '市场价格读取失败';
    }
  }
  onMounted(load);
  onBeforeUnmount(() => abort?.abort());
  const title = computed(() => (props.mode === 'etf' ? 'ETF申赎与市场涨跌' : '融资变化与市场涨跌'));
  const points = computed(() =>
    pairedCapitalPoints(capitalComparison(props.data, 20).rows, prices.value)
      .slice(-days.value)
      .flatMap((r) => {
        const y = props.mode === 'etf' ? r.etf : r.financing;
        return r.marketReturn != null && y != null
          ? [{ id: r.date, name: r.date, x: r.marketReturn, y }]
          : [];
      }),
  );
  const fit = computed(() => linearFit(points.value));
</script>
<style scoped src="./researchSupplement.css"></style>
