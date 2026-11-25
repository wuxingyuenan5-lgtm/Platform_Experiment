<template>
  <section class="hk-observation" aria-label="港股观察">
    <header class="hk-heading"><h2>港股观察</h2><span>指数强弱 · A/H联动</span></header>
    <div class="hk-index-grid" aria-label="港股指数概览">
      <button
        v-for="row in indices"
        :key="row.id"
        type="button"
        :aria-pressed="selected?.id === row.id"
        @click="selectedId = row.id"
      >
        <span class="index-name"
          >{{ name(row.id, row.name) }}
          <small
            >{{ row.date || '暂无数据'
            }}{{ row.status && row.status !== 'ready' ? ' · 待更新' : '' }}</small
          ></span
        >
        <strong>{{ format(row.value) }}</strong>
        <span class="index-returns"
          ><span
            >当日 <b :class="tone(row.returnPct)">{{ signed(row.returnPct) }}</b></span
          ><span
            >5日 <b :class="tone(row.return5)">{{ signed(row.return5) }}</b></span
          ><span
            >20日 <b :class="tone(row.return20)">{{ signed(row.return20) }}</b></span
          ></span
        >
      </button>
    </div>
    <p v-if="!indices.length" role="status">暂无港股指数数据</p>
    <template v-if="selected">
      <div class="hk-chart-grid">
        <div>
          <WidgetErrorBoundary widget-title="港股指数走势">
            <FinancingChart
              :key="selected.id"
              :title="`${selectedName} · 价格走势`"
              :rows="selected.history.map((p) => ({ date: p.date, value: p.value }))"
              :lines="[{ key: 'value', name: selectedName, unit: '点', color: '#171717' }]"
              :range-days="priceDays"
              @range="priceDays = $event"
              allow-table
              note="价格指数收盘点位，不含股息。"
            />
          </WidgetErrorBoundary>
          <p class="source"
            ><a
              v-if="selected.sourceUrl"
              :href="selected.sourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              >{{ selected.name }} ↗</a
            >
            · {{ selected.date || '暂无数据' }}</p
          >
        </div>
        <div>
          <WidgetErrorBoundary widget-title="A/H同期表现">
            <FinancingChart
              :title="`${selectedName} / 沪深300 · 同期表现`"
              :rows="comparison.rows"
              :lines="comparisonLines"
              :range-days="comparisonDays"
              @range="comparisonDays = $event"
              allow-table
              :note="`共同交易日、本币价格回报，不含股息或汇兑；非AH溢价。${
                comparison.baseDate ? '基准：' + comparison.baseDate + ' = 100。' : ''
              }`"
            />
          </WidgetErrorBoundary>
          <p class="source"
            >共同区间截至 {{ comparison.rows.at(-1)?.date || '—' }} ·
            <a
              v-if="data.benchmark?.sourceUrl"
              :href="data.benchmark.sourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              >沪深300 ↗</a
            ><span v-if="data.benchmark?.status !== 'ready'"> · 沪深300数据待补齐</span></p
          >
        </div>
      </div>
      <div class="trend-table" role="region" aria-label="港股趋势位置" tabindex="0">
        <table
          ><thead
            ><tr
              ><th scope="col">指数</th><th scope="col">距20日均线</th
              ><th scope="col">距252日收盘高点</th><th scope="col">观测日期</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in indices" :key="row.id"
              ><th scope="row">{{ name(row.id, row.name) }}</th
              ><td :class="tone(row.deviation20)">{{ signed(row.deviation20) }}</td
              ><td>{{ signed(row.drawdown252) }}</td
              ><td>{{ row.date || '—' }}</td></tr
            ></tbody
          ></table
        >
      </div>
      <p class="definition"
        >5日、20日按各指数实际交易日计算累计涨跌；均线与高点使用完整窗口，历史不足或缺值显示“—”。同期表现仅对齐两地共同交易日期，不补休市报价。</p
      >
    </template>
    <section class="macro-reference" aria-label="月度宏观参考">
      <h3>月度宏观参考</h3>
      <div class="composite"
        ><span>港股宏观四因子</span><strong>{{ format(data.value) }}</strong
        ><span
          >{{ data.date || '四项同月历史不足'
          }}{{ data.status !== 'ready' ? ' · 数据待更新' : '' }}</span
        ></div
      >
      <div class="trend-table" tabindex="0" role="region" aria-label="港股宏观四因子明细"
        ><table
          ><thead
            ><tr
              ><th>因子</th><th>最新原值</th><th>统计期间</th><th>有效期数</th><th>权重</th
              ><th>合成当月贡献</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in data.components" :key="row.id"
              ><th
                ><a :href="row.sourceUrl" target="_blank" rel="noopener noreferrer">{{
                  row.name
                }}</a></th
              ><td
                >{{ format(row.value)
                }}{{ row.value != null ? (row.id === 'credit' ? ' pp' : '%') : '' }}</td
              ><td>{{ row.date || '—' }}{{ row.status !== 'ready' ? ' · 待更新' : '' }}</td
              ><td>{{ row.count }}</td
              ><td>25%</td
              ><td
                >{{ format(row.contribution) }} <small>{{ row.compositeDate || '' }}</small></td
              ></tr
            ></tbody
          ></table
        ></div
      >
      <p class="definition"
        >每项按过去60个月标准化，至少36期，同月四项齐全才等权合成。信用脉冲为滚动12月新增社融/名义GDP比例的同比变化；社零2月为1—2月合计。使用当前可得修订值，不代表已验证的领先预测指标。</p
      >
      <WidgetErrorBoundary widget-title="港股宏观四因子"
        ><VibeTimeChart
          v-if="data.history.length"
          title="港股宏观四因子"
          frequency="monthly"
          y-label="标准分"
          :dates="data.history.map((p) => p.date)"
          :series="[
            {
              name: '等权标准分',
              type: 'line',
              color: '#38827c',
              values: data.history.map((p) => (p.value == null ? null : Number(p.value))),
            },
          ]"
      /></WidgetErrorBoundary>
    </section>
  </section>
</template>
<script setup lang="ts">
  import { computed, defineAsyncComponent, ref } from 'vue';
  import type { EquityObservatory, EquityValue } from '@/api/equityObservatory';
  import FinancingChart from './FinancingChart.vue';
  import WidgetErrorBoundary from '../../components/WidgetErrorBoundary';
  import { compareHongKong } from './hongKongAnalysis';

  const VibeTimeChart = defineAsyncComponent(() => import('./VibeTimeChart.vue'));
  const props = defineProps<{ data: NonNullable<EquityObservatory['hongKong']> }>();
  const selectedId = ref('hk_hsi'),
    priceDays = ref(365),
    comparisonDays = ref(365);
  const indices = computed(() => props.data.indices || []);
  const selected = computed(
    () => indices.value.find((row) => row.id === selectedId.value) || indices.value[0],
  );
  const name = (id: string, fallback: string) =>
    ({ hk_hsi: '恒生指数', hk_hscei: '恒生国企', hk_hstech: '恒生科技', hk_hsiii: '恒生互联网' }[
      id
    ] || fallback);
  const selectedName = computed(() =>
    selected.value ? name(selected.value.id, selected.value.name) : '港股指数',
  );
  const comparison = computed(() =>
    compareHongKong(
      selected.value?.history || [],
      props.data.benchmark?.history || [],
      comparisonDays.value,
    ),
  );
  const comparisonLines = computed(() => [
    { key: 'hongKong', name: selectedName.value, unit: '基准100', color: '#171717' },
    { key: 'mainland', name: '沪深300', unit: '基准100', color: '#2563eb' },
  ]);
  const numeric = (v: unknown) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const format = (v: EquityValue | undefined) =>
    numeric(v) == null
      ? '—'
      : numeric(v)!.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const signed = (v: EquityValue | undefined) =>
    numeric(v) == null ? '—' : `${numeric(v)! > 0 ? '+' : ''}${format(v)}%`;
  const tone = (v: EquityValue | undefined) =>
    numeric(v) == null || numeric(v) === 0 ? '' : numeric(v)! > 0 ? 'up' : 'down';
</script>
<style scoped>
  .hk-observation {
    min-width: 0;
    color: var(--strategy-text-2);
  }

  .hk-heading {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  h2 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 20px;
  }

  .hk-heading > span,
  small,
  .source,
  .definition {
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.7;
  }

  .hk-index-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .hk-index-grid button {
    display: flex;
    flex-direction: column;
    min-width: 0;
    padding: 16px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
    gap: 10px;
  }

  .hk-index-grid button[aria-pressed='true'] {
    border-color: var(--strategy-accent);
    background: var(--strategy-accent-soft);
  }

  .index-name {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 4px 8px;
    font-size: 14px;
    font-weight: 600;
  }

  .index-name small {
    font-weight: 400;
  }

  strong {
    color: var(--strategy-text-1);
    font-size: 24px;
    font-variant-numeric: tabular-nums;
  }

  .index-returns {
    display: flex;
    flex-wrap: wrap;
    color: var(--strategy-text-3);
    font-size: 12px;
    gap: 6px 16px;
  }

  b {
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }

  .up {
    color: #cc504a;
  }

  .down {
    color: #13866b;
  }

  .hk-chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .hk-chart-grid > div {
    min-width: 0;
  }

  .hk-chart-grid :deep(.financing-chart .definition) {
    min-height: 40px;
  }

  .source {
    margin: 0 0 14px;
    overflow-wrap: anywhere;
  }

  a {
    color: var(--strategy-accent);
  }

  .trend-table {
    overflow-x: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 12px;
    border-bottom: 1px solid var(--strategy-border);
    text-align: right;
  }

  th:first-child {
    text-align: left;
  }

  th {
    font-weight: 500;
  }

  thead {
    background: var(--strategy-surface-2);
  }

  .definition {
    margin: 10px 0 18px;
  }

  .macro-reference {
    margin-top: 24px;
  }

  .macro-reference h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
  }

  .composite {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    padding: 18px 0;
    font-size: 13px;
  }

  button:focus-visible,
  a:focus-visible,
  .trend-table:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 2px;
  }

  @media (max-width: 1250px) {
    .hk-index-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .hk-chart-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 600px) {
    .hk-index-grid button {
      padding: 12px;
    }

    strong {
      font-size: 20px;
    }

    .index-returns {
      flex-direction: column;
      gap: 4px;
    }
  }
</style>
