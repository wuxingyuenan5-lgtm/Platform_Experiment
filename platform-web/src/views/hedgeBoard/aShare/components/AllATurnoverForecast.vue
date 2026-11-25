<template>
  <section class="all-a-forecast" aria-label="全A当日成交额预测">
    <header
      ><h3>全A当日成交额预测</h3><span>{{ statusLabel }}</span></header
    >
    <p class="source"
      >{{ data?.source || '沪深北A股' }} ·
      {{ data?.latest?.asOf?.replace('T', ' ').slice(0, 19) || '暂无行情时间' }}</p
    >
    <p v-if="error" role="alert">读取失败 <button @click="load">重试</button></p>
    <p v-else-if="loading && !data" role="status">正在读取全A成交额…</p>
    <div class="metrics">
      <div
        ><span>{{ data?.status === 'closed' ? '收盘成交额' : '已累计成交' }}</span
        ><strong>{{ amount(data?.latest?.amountYi) }}<small>亿元</small></strong></div
      >
      <div
        ><span>近5日推测今日成交额</span><strong>{{ estimate(5) }}<small>亿元</small></strong></div
      >
      <div
        ><span>近20日推测今日成交额</span
        ><strong>{{ estimate(20) }}<small>亿元</small></strong></div
      >
    </div>
    <p v-if="data?.status === 'stale'" role="status"
      >行情已延迟或属于历史交易日，当前预测暂停展示。</p
    >
    <p v-else-if="data?.status === 'closed'">已取得收盘数据，使用实际成交额。</p>
    <p v-else-if="data?.status === 'failed'" role="status">全A成交额来源暂不可用，暂不输出预测。</p>
    <p
      v-if="data?.status !== 'closed' && (!data?.latest || data.latest.estimate5Yi == null)"
      role="status"
      >同时间可比历史：近5日 {{ data?.latest?.samples5 || 0 }}/5，近20日
      {{ data?.latest?.samples20 || 0 }}/20。样本未齐的窗口暂不输出预测。</p
    >
    <div ref="plot" class="forecast-plot" role="img" aria-label="全A累计成交额及全天预测走势"></div>
    <p class="definition"
      >实线为当日累计实际成交额；虚线从最新实绩出发，按近5／20个交易日的平均日内成交进度推演至收盘。沪深北A股，含ST与新股；按行情时点对齐，缺数不填补，预测不等于实际成交额。</p
    >
  </section>
</template>
<script setup lang="ts">
  import {
    computed,
    nextTick,
    onActivated,
    onBeforeUnmount,
    onDeactivated,
    ref,
    shallowRef,
    watch,
    type Ref,
  } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { researchRequest } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';
  import { useDashboardRefresh } from '../../useDashboardRefresh';

  interface Point {
    slot: string;
    asOf: string;
    amountYi: string;
    estimate5Yi: string | null;
    estimate20Yi: string | null;
    samples5: number;
    samples20: number;
  }
  interface Forecast {
    date: string | null;
    status: string;
    source: string;
    latest: Point | null;
    rows: Point[];
    paths: Array<{
      slot: string;
      amountYi: string | null;
      forecast5Yi: string | null;
      forecast20Yi: string | null;
    }>;
  }
  const props = defineProps<{ refreshKey?: number }>();
  const data = shallowRef<Forecast>();
  const error = ref(false),
    loading = ref(false),
    plot = ref<HTMLDivElement>();
  const chart = useECharts(plot as Ref<HTMLDivElement>, 'light');
  const amount = (v?: string | null) =>
    v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 });
  const estimate = (n: number) =>
    ['ready', 'partial'].includes(data.value?.status || '') && !error.value
      ? amount(n === 5 ? data.value?.latest?.estimate5Yi : data.value?.latest?.estimate20Yi)
      : '—';
  const labels: Record<string, string> = {
    ready: '盘中估计（延迟行情）',
    partial: '历史积累中',
    no_data: '等待采集',
    stale: '行情已过期',
    closed: '收盘实绩',
    failed: '采集异常',
  };
  const statusLabel = computed(() =>
    error.value ? '读取异常' : labels[data.value?.status || 'no_data'],
  );
  let active = true,
    controller: AbortController | undefined;
  async function load() {
    if (!active || document.hidden || loading.value) return;
    const request = (controller = new AbortController());
    loading.value = true;
    try {
      const result = await researchRequest<Forecast>({
        method: 'GET',
        url: '/research/a-share/turnover-forecast',
        signal: request.signal,
      });
      if (!request.signal.aborted) {
        data.value = result;
        error.value = false;
      }
    } catch {
      if (!request.signal.aborted) error.value = true;
    } finally {
      if (controller === request) loading.value = false;
    }
  }
  watch([data, plot], async () => {
    await nextTick();
    const rows = data.value?.paths || [];
    chart.setOptions(
      {
        animation: false,
        legend: { top: 8, type: 'scroll' },
        tooltip: { trigger: 'axis', confine: true },
        grid: { top: 65, left: 65, right: 20, bottom: 40 },
        xAxis: { type: 'category', data: rows.map((r) => (r.slot === 'close' ? '收盘' : r.slot)) },
        yAxis: { type: 'value', name: '亿元' },
        series: [
          ['amountYi', '累计实际', '#7c8fa3'],
          ['forecast5Yi', '近5日推算', '#d36b55'],
          ['forecast20Yi', '近20日推算', '#527fbd'],
        ].map(([key, name, color]) => ({
          name,
          type: 'line',
          connectNulls: false,
          showSymbol: rows.length < 2,
          data: rows.map((r) =>
            r[key as keyof typeof r] == null ? null : Number(r[key as keyof typeof r]),
          ),
          lineStyle: { color, type: key === 'amountYi' ? 'solid' : 'dashed' },
          itemStyle: { color },
        })),
      } as EChartsOption,
      true,
    );
  });
  watch(() => props.refreshKey, load, { immediate: true });
  useDashboardRefresh(load, { immediate: false, enabled: () => !loading.value });
  onDeactivated(() => {
    active = false;
    controller?.abort();
    loading.value = false;
  });
  onActivated(() => {
    active = true;
    void load();
  });
  onBeforeUnmount(() => {
    active = false;
    controller?.abort();
  });
</script>
<style scoped>
  .all-a-forecast {
    margin: 14px 0;
    padding: 16px;
    border: 1px solid #e2e8f0;
    border-radius: 9px;
    background: #fff;
    color: #233950;
  }

  header {
    display: flex;
    justify-content: space-between;
    gap: 10px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
  }

  header span,
  p {
    color: #708096;
    font-size: 12px;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin: 18px 0;
  }

  .metrics span {
    color: #65758a;
    font-size: 12px;
  }

  strong {
    display: block;
    font-size: 25px;
    font-variant-numeric: tabular-nums;
  }

  small {
    margin-left: 5px;
    font-size: 11px;
    font-weight: 400;
  }

  .forecast-plot {
    width: 100%;
    height: 320px;
  }

  .definition {
    line-height: 1.7;
  }

  @media (max-width: 600px) {
    .metrics {
      gap: 6px;
    }

    strong {
      font-size: 18px;
    }

    small {
      display: block;
      margin: 0;
    }
  }
</style>
