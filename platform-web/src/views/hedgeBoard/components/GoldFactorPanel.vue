<template>
  <div class="gold-research">
    <p v-if="error" class="gold-warning">{{ error }}</p>
    <div v-show="rows.length">
      <div class="gold-controls">
        <button :class="{ active: !contribution }" @click="contribution = false">四因子走势</button>
        <button :class="{ active: contribution }" @click="contribution = true">区间贡献</button>
        <label>开始 <input v-model="start" type="date" :min="rows[0]?.date" :max="end" /></label>
        <label
          >结束 <input v-model="end" type="date" :min="start" :max="rows.at(-1)?.date"
        /></label>
        <button @click="table = !table">{{ table ? '查看图表' : '查看数据' }}</button>
      </div>
      <template v-if="latest">
        <p class="factor-equation"
          >${{ n(latest.gold, 2) }} = ${{ n(latest.mid, 2) }} × {{ n(latest.tips, 4) }} ×
          {{ n(latest.yieldFactor, 4) }} × {{ n(latest.premium, 4) }}</p
        >
        <p class="gold-meta"
          >{{ latest.date }} · 货币基准 × 盈亏平衡通胀因子 × 名义利率因子 × 剩余溢价{{
            data?.status === 'stale' ? ' · 数据待更新' : ''
          }}</p
        >
      </template>
      <p v-if="contribution && latest" class="gold-meta"
        >贡献起点 {{ selected.find((r) => r.available)?.date }} ·
        各因子及金价相对起点的百分比变化。</p
      >
      <p v-if="!selected.length">此区间没有数据。</p>
      <div
        v-show="!table && selected.length"
        ref="chartRef"
        :class="['factor-chart', { 'factor-chart--contribution': contribution }]"
        role="img"
        aria-label="金价四因子分解"
      ></div>
      <div v-if="table" class="gold-table"
        ><table
          ><thead
            ><tr
              ><th>日期</th><th>黄金 USD/oz</th><th>货币基准</th><th>通胀因子</th><th>利率因子</th
              ><th>剩余溢价</th><th>M2观察月</th></tr
            ></thead
          ><tbody
            ><tr v-for="r in selected" :key="r.date"
              ><td>{{ r.date }}</td
              ><td>{{ n(r.gold, 2) }}</td
              ><td>{{ n(r.mid, 2) }}</td
              ><td>{{ n(r.tips, 4) }}</td
              ><td>{{ n(r.yieldFactor, 4) }}</td
              ><td>{{ n(r.premium, 4) }}</td
              ><td>{{ r.monetaryObservation || '—' }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <GoldReferenceSnapshots group="factors" />
      <details
        ><summary>计算口径</summary
        ><p
          >货币基准按美国 M2 增长、黄金供给年增 1.5% 缩放；M2 按两个月滞后对齐。利率因子为 exp(−D ×
          10年名义利率)，通胀因子为 exp(D × 10年盈亏平衡通胀率)，利率使用小数。</p
        ><p
          >D = {{ n(data?.calibration?.duration, 4) }}，用 {{ data?.calibration?.start }} 至
          {{ data?.calibration?.end }}
          的日度金价对数变化与实际利率变化估计后固定。剩余溢价是金价除以前三项，涵盖未解释因素，不等同于纯通胀预期。历史输入为当前修订数据。因子曲线按共同观测日绘制，缺失日不补值；超过七天的缺口保留断线。百分比变化不作加总。</p
        ></details
      >
      <div class="gold-controls gold-meta"
        ><a
          v-for="(s, i) in data?.sources"
          :key="i"
          :href="s.sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          >{{ s.source }} · {{ s.observationDate }} ↗</a
        ></div
      >
    </div>
    <p v-if="!rows.length && !error">{{ data ? '四因子数据暂不可用。' : '正在读取四因子数据…' }}</p>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef, watch, nextTick, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import { goldRequest } from './goldResearch';
  import GoldReferenceSnapshots from './GoldReferenceSnapshots.vue';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { useResearchViewState } from '../composables/researchWorkspace';
  import { goldFactorOptions, type GoldFactorData } from '../charts/goldFactorOptions';

  const data = shallowRef<GoldFactorData>();
  const error = ref('');
  const contribution = useResearchViewState('gold-factor-contribution', false);
  const start = useResearchViewState('gold-factor-start', '');
  const end = useResearchViewState('gold-factor-end', '');
  const table = ref(false);
  const rows = computed(() => data.value?.rows || []);
  const selected = computed(() =>
    rows.value.filter((r) => r.date >= start.value && r.date <= end.value),
  );
  const latest = computed(() => [...selected.value].reverse().find((r) => r.available));
  const n = (v: number | undefined | null, digits: number) =>
    v == null
      ? '—'
      : v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  watch([selected, contribution, table, chartRef], async () => {
    await nextTick();
    if (selected.value.length && !table.value) {
      chart.setOptions(goldFactorOptions(selected.value, contribution.value), true);
      chart.getInstance()?.resize();
    }
  });
  useDashboardRefresh(async () => {
    try {
      data.value = await goldRequest<GoldFactorData>('gold-factor-model');
      if (!end.value) end.value = rows.value.at(-1)?.date || '';
      if (!start.value) start.value = rows.value[0]?.date || '';
      error.value = '';
    } catch {
      error.value = '四因子数据暂不可用，请稍后重试。';
    }
  });
</script>
<style scoped src="./goldResearch.css"></style>
<style scoped>
  .factor-chart {
    width: 100%;
    height: 960px;
  }

  .factor-chart--contribution {
    height: 900px;
  }

  .factor-equation {
    color: #8a682d;
    font-size: clamp(16px, 2vw, 24px);
    font-variant-numeric: tabular-nums;
  }
</style>
