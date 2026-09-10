<template>
  <Drawer
    :open="Boolean(code)"
    :title="detail?.stock.name || code"
    width="min(560px, 100vw)"
    :destroy-on-close="true"
    @close="emit('close')"
  >
    <div
      class="stock-detail"
      role="dialog"
      aria-modal="true"
      :aria-label="`${detail?.stock.name || code}行情详情`"
    >
      <p class="stock-meta"
        >{{ code }}<span v-if="detail?.stock.industry"> · {{ detail.stock.industry }}</span></p
      >
      <div v-if="loading" role="status">正在读取行情与日线…</div>
      <div v-else-if="error" role="alert"
        >{{ error }} <Button size="small" @click="load">重试</Button></div
      >
      <template v-else-if="detail">
        <p class="stock-meta"
          >{{ observedLabel }} · {{ detail.stock.currency === 'HKD' ? '港币' : '人民币' }}</p
        >
        <div class="stock-metrics">
          <div v-for="metric in metrics" :key="metric.label"
            ><span>{{ metric.label }}</span
            ><strong>{{ metric.value }}</strong></div
          >
        </div>
        <div class="history-heading"
          ><h3>复权收盘价</h3
          ><select v-model="range" aria-label="个股日线范围"
            ><option :value="20">近20日</option
            ><option :value="60">近60日</option
            ><option :value="300">全部历史</option></select
          ></div
        >
        <template v-if="points.length > 1">
          <svg
            viewBox="0 0 480 190"
            role="img"
            :aria-label="`${code}复权收盘价，${points.length}个交易日`"
          >
            <line x1="32" y1="150" x2="464" y2="150" class="chart-axis" />
            <line x1="32" y1="24" x2="464" y2="24" class="chart-axis" />
            <polyline :points="polyline" class="price-line" />
            <text x="32" y="18">{{ number(domain[1]) }}</text>
            <text x="32" y="167">{{ number(domain[0]) }}</text>
            <text x="32" y="187">{{ points[0].observedAt }}</text>
            <text x="464" y="187" text-anchor="end">{{ points.at(-1)?.observedAt }}</text>
          </svg>
          <p class="stock-meta"
            >{{ points[0].observedAt }} 至 {{ points.at(-1)?.observedAt }} ·
            {{ points.length }}个交易日</p
          >
          <details
            ><summary>查看日线数据</summary
            ><table
              ><thead
                ><tr><th>日期</th><th>复权收盘</th></tr></thead
              ><tbody
                ><tr v-for="point in [...points].reverse()" :key="point.observedAt"
                  ><td>{{ point.observedAt }}</td
                  ><td>{{ number(point.close) }}</td></tr
                ></tbody
              ></table
            ></details
          >
        </template>
        <p v-else class="empty">暂无完整历史日线，收盘数据更新后可查看。</p>
      </template>
    </div>
  </Drawer>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { Button, Drawer } from 'ant-design-vue';
  import { getPoolStockDetail, type StockDetail } from '@/api/platform/aShareStockPool';

  const props = defineProps<{ code: string }>();
  const emit = defineEmits<{ (event: 'close'): void }>();
  const detail = ref<StockDetail | null>(null);
  const loading = ref(false);
  const error = ref('');
  const range = ref(60);
  let requestId = 0;
  async function load() {
    const current = ++requestId;
    if (!props.code) return;
    loading.value = true;
    error.value = '';
    detail.value = null;
    try {
      const result = await getPoolStockDetail(props.code);
      if (current === requestId) detail.value = result;
    } catch (cause) {
      if (current === requestId)
        error.value = cause instanceof Error ? cause.message : '行情加载失败';
    } finally {
      if (current === requestId) loading.value = false;
    }
  }
  watch(
    () => props.code,
    () => {
      range.value = 60;
      void load();
    },
  );
  const number = (value: unknown) =>
    value == null || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  const pct = (value: unknown) =>
    value == null ? '—' : `${Number(value) > 0 ? '+' : ''}${(Number(value) * 100).toFixed(2)}%`;
  const observedLabel = computed(() => {
    const stock = detail.value?.stock;
    const date = stock?.observed_at
      ? new Date(stock.observed_at).toLocaleString('zh-CN', {
          hour12: false,
          timeZone: 'Asia/Shanghai',
        })
      : '';
    return `${
      stock?.status === 'stale'
        ? '上一份有效数据'
        : stock?.status === 'no_data'
        ? '行情待更新'
        : stock?.status === 'partial'
        ? '部分行情可用'
        : '行情'
    }${date ? ` · ${date}` : ''}`;
  });
  const metrics = computed(() => {
    const s = detail.value?.stock;
    return [
      { label: '现价', value: number(s?.price) },
      { label: '今日', value: pct(s?.change) },
      { label: '5日', value: pct(s?.change_5d) },
      { label: '20日', value: pct(s?.change_20d) },
      { label: '年初至今', value: pct(s?.ytd) },
      { label: '成交额（亿）', value: number(s?.amount_yi) },
    ];
  });
  const points = computed(() =>
    (detail.value?.history || [])
      .filter((p) => Number.isFinite(Number(p.close)))
      .slice(-range.value),
  );
  const domain = computed(() => {
    const values = points.value.map((p) => Number(p.close));
    return [Math.min(...values), Math.max(...values)];
  });
  const polyline = computed(() =>
    points.value
      .map(
        (point, i) =>
          `${32 + (i / Math.max(1, points.value.length - 1)) * 432},${
            150 -
            ((Number(point.close) - domain.value[0]) / (domain.value[1] - domain.value[0] || 1)) *
              126
          }`,
      )
      .join(' '),
  );
</script>

<style scoped lang="less">
  .stock-detail {
    color: #354d68;
    font-variant-numeric: tabular-nums;
  }
  .stock-meta {
    color: #60758f;
    font-size: 12px;
  }
  .stock-metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin: 20px 0;
  }
  .stock-metrics div {
    padding: 14px;
    background: #f3f7fb;
    border: 1px solid #d9e3ee;
    border-radius: 10px;
  }
  .stock-metrics span {
    display: block;
    color: #60758f;
    font-size: 12px;
  }
  .stock-metrics strong {
    display: block;
    margin-top: 6px;
    font-size: 19px;
    color: #10233d;
  }
  .history-heading {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 24px;
  }
  .history-heading h3 {
    font-size: 15px;
    color: #10233d;
  }
  select {
    padding: 5px 8px;
    border: 1px solid #d9e3ee;
    border-radius: 6px;
    background: white;
  }
  svg {
    width: 100%;
    margin: 12px 0;
    overflow: visible;
  }
  svg text {
    font-size: 10px;
    fill: #60758f;
  }
  .chart-axis {
    stroke: #d9e3ee;
    stroke-dasharray: 3;
  }
  .price-line {
    stroke: #1d4ed8;
    stroke-width: 2;
    fill: none;
  }
  .empty {
    padding: 30px 0;
    text-align: center;
    color: #60758f;
  }
  table {
    width: 100%;
    margin-top: 12px;
    text-align: right;
  }
  td,
  th {
    padding: 6px 10px;
    border-bottom: 1px solid #e7edf4;
  }
  summary {
    cursor: pointer;
  }
  @media (max-width: 480px) {
    .stock-metrics {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
