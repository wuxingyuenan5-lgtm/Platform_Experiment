<template>
  <section class="member-analysis">
    <p v-if="loading" role="status">正在读取单只 ETF…</p>
    <p v-else-if="error" role="alert">基金明细读取失败 <button @click="load">重试</button></p>
    <template v-if="detail">
      <p
        ><strong>{{ detail.meta.name }} · {{ detail.meta.code }}</strong> ·
        {{ detail.series.at(-1)?.date || '暂无行情日期' }} ·
        {{
          detail.sources.market?.status === 'ready'
            ? '已采集'
            : detail.series.length
            ? '历史观测'
            : '暂无数据'
        }}</p
      >
      <p v-if="detail.shareBasis === 'native'"
        >交易所公布份额 · {{ detail.sources.market.shareDate || '暂无份额日期' }}；复权收盘 ·
        {{ detail.sources.market.priceDate || '暂无价格日期' }}。份额变化可能包含折算。</p
      >
      <template v-if="detail.series.length">
        <FinancingChart
          title="复权收盘价与份额"
          :rows="detail.series"
          :lines="lines"
          :range-days="range"
          @range="$emit('range', $event)"
          allow-table
        />
        <details>
          <summary>份额变化与价格收益的相关性</summary>
          <p>{{ start }} 至 {{ end }} · Pearson 相关系数</p>
          <table
            ><thead
              ><tr><th>时间关系</th><th>相关系数</th><th>配对交易日</th></tr></thead
            >
            <tbody
              ><tr v-for="row in stats" :key="row.lag">
                <td>{{
                  row.lag > 0
                    ? '份额领先' + row.lag + '日'
                    : row.lag < 0
                    ? '价格领先' + -row.lag + '日'
                    : '同日'
                }}</td>
                <td>{{ row.correlation?.toFixed(3) ?? '—' }}</td
                ><td>{{ row.n }}</td>
              </tr></tbody
            >
          </table>
          <p
            >比较日份额变化率与复权收盘收益率。仅使用相邻交易日数据；少于20对样本或序列无波动时留空。领先指观测日顺序，披露可能更晚。</p
          >
        </details>
      </template>
      <p v-else>该基金暂无可用的日线与份额历史。</p>
    </template>
  </section>
</template>
<script setup lang="ts">
  import { ref, shallowRef, computed, watch, onBeforeUnmount } from 'vue';
  import { getEtfDetail, type EtfDetail } from '@/api/etfTracking';
  import FinancingChart from './FinancingChart.vue';
  import { etfLeadLag } from './etfLeadLag';

  const props = defineProps<{ code: string; range: number; refreshKey?: number }>();
  defineEmits<{ range: [days: number] }>();
  const detail = shallowRef<EtfDetail>();
  const error = ref(false),
    loading = ref(false);
  const lines = computed(() => [
    { key: 'etf_qfq_close', name: '复权收盘', unit: '元', color: '#2864ec' },
    {
      key: detail.value?.shareBasis === 'native' ? 'native_units_yi' : 'qfq_total_units_yi',
      name: '份额',
      unit: '亿份',
      right: true,
      color: '#986723',
    },
  ]);
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    detail.value = undefined;
    error.value = false;
    loading.value = Boolean(props.code);
    if (!props.code) return;
    const request = (controller = new AbortController());
    try {
      const result = await getEtfDetail(props.code, request.signal);
      if (!request.signal.aborted) detail.value = result;
    } catch {
      if (!request.signal.aborted) error.value = true;
    } finally {
      if (!request.signal.aborted) loading.value = false;
    }
  }
  watch([() => props.code, () => props.refreshKey], load, { immediate: true });
  onBeforeUnmount(() => controller?.abort());
  const end = computed(() => detail.value?.series.at(-1)?.date || '');
  const start = computed(() => {
    const first = detail.value?.series[0]?.date || '';
    if (!end.value || !props.range) return first;
    const from = new Date(end.value + 'T00:00:00Z');
    from.setUTCDate(from.getUTCDate() - props.range);
    return [first, from.toISOString().slice(0, 10)].sort()[1];
  });
  const stats = computed(() =>
    etfLeadLag(detail.value?.series || [], detail.value?.sessions || [], start.value, end.value),
  );
</script>
<style scoped>
  .member-analysis {
    padding: 14px;
    border: 1px solid #dde4ee;
    border-radius: 10px;
    background: #fff;
  }

  label,
  summary {
    font-weight: 600;
  }

  select {
    max-width: 100%;
    margin-left: 8px;
  }

  p {
    margin: 8px 0;
    color: #57687c;
  }

  table {
    width: 100%;
    max-width: 640px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 4px 10px;
    border-bottom: 1px solid #e6eaf0;
    text-align: left;
  }
</style>
