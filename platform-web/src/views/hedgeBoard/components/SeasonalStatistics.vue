<template>
  <section class="cycle-analysis" aria-label="月度季节性分布">
    <p class="definition"
      >{{ start }}—{{ end }} · 仅统计已结束月份，最新观测月不参与。上涨概率分母含零收益月份。</p
    >
    <div ref="host" class="cycle-plot" role="img" aria-label="各月收益均值与中位数"></div>
    <div class="cycle-table" tabindex="0" role="region" aria-label="季节性统计明细">
      <table
        ><thead
          ><tr
            ><th>月份</th><th>样本数</th><th>上涨概率</th><th>平均收益</th><th>中位数</th
            ><th>25%分位</th><th>75%分位</th><th>最低</th><th>最高</th></tr
          ></thead
        >
        <tbody
          ><tr v-for="r in data" :key="r.month"
            ><th>{{ r.month }}月</th><td>{{ r.n }}</td
            ><td>{{ pct(r.win) }}</td
            ><td>{{ pct(r.mean) }}</td
            ><td>{{ pct(r.median) }}</td
            ><td>{{ pct(r.low) }}</td
            ><td>{{ pct(r.high) }}</td
            ><td>{{ pct(r.min) }}</td
            ><td>{{ pct(r.max) }}</td></tr
          ></tbody
        ></table
      >
    </div>
    <p class="definition"
      >近5年、近10年和全历史可在上方切换；样本少于5个时宜谨慎比较。分位区间展示历史离散程度。</p
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { SeasonalPoint } from '../charts/seasonality';
  import { monthlyDistributions } from '../charts/cycleAnalysis';

  const props = defineProps<{ observations: SeasonalPoint[]; start: number; end: number }>();
  const data = computed(() => monthlyDistributions(props.observations, props.start, props.end));
  const pct = (v: number | null) => (v == null ? '—' : `${v.toFixed(2)}%`);
  const host = ref<HTMLDivElement | null>(null),
    chart = useECharts(host as Ref<HTMLDivElement>);
  watch(
    data,
    async (rows) => {
      await nextTick();
      chart.setOptions(
        {
          tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v == null ? null : Number(v)) },
          legend: { data: ['平均收益', '中位数'] },
          grid: { left: 60, right: 24, top: 42, bottom: 35 },
          xAxis: { type: 'category', data: rows.map((r) => `${r.month}月`) },
          yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
          series: [
            {
              name: '平均收益',
              type: 'bar',
              data: rows.map((r) => r.mean),
              itemStyle: { color: '#5574cc' },
              barMaxWidth: 35,
            },
            {
              name: '中位数',
              type: 'line',
              data: rows.map((r) => r.median),
              itemStyle: { color: '#cc9b39' },
            },
          ],
        },
        true,
      );
    },
    { immediate: true },
  );
</script>
<style scoped lang="less" src="./cyclePanels.less"></style>
