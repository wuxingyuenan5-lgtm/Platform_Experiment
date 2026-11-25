<template>
  <section class="cycle-analysis" aria-label="回撤与修复周期">
    <div class="cycle-controls"
      ><label
        >最低回撤
        <select v-model.number="threshold" aria-label="周期最低回撤"
          ><option :value="10">10%</option
          ><option :value="20">20%</option
          ><option :value="30">30%</option></select
        ></label
      ></div
    >
    <div class="cycle-cards"
      ><article
        ><span>当前距样本高点</span><strong>{{ pct(data.current) }}</strong
        ><small>截至 {{ data.latest || '—' }}</small></article
      ><article
        ><span>符合阈值的周期</span><strong>{{ data.episodes.length }} 次</strong
        ><small>未修复周期保留在内</small></article
      ><article
        ><span>已修复周期耗时中位数</span
        ><strong>{{
          data.recoveryMedian == null ? '—' : data.recoveryMedian.toFixed(0) + ' 天'
        }}</strong
        ><small>高点至修复 · 排除含长观测间隔周期</small></article
      ></div
    >
    <p v-if="!data.episodes.length" class="definition">当前历史范围内暂无达到阈值的回撤周期。</p>
    <template v-else>
      <p class="definition"
        >对齐各次高点：横轴为经过的日历天，纵轴为相对高点收益。图中展示所选周期，最多5条。</p
      >
      <div ref="host" class="cycle-plot" role="img" aria-label="历史回撤周期对齐比较"></div>
      <div class="cycle-table" tabindex="0" role="region" aria-label="回撤周期登记">
        <table
          ><thead
            ><tr
              ><th>对比</th><th>高点日</th><th>低点日</th><th>最大回撤</th><th>下跌天数</th
              ><th>低点至修复</th><th>水下天数</th><th>修复日 / 状态</th></tr
            ></thead
          ><tbody>
            <tr v-for="e in paged" :key="e.peak"
              ><td
                ><input
                  type="checkbox"
                  :aria-label="'对比周期 ' + e.peak"
                  :checked="selected.includes(e.peak)"
                  :disabled="!selected.includes(e.peak) && selected.length >= 5"
                  @change="toggle(e.peak)" /></td
              ><th>{{ e.peak }}</th
              ><td>{{ e.trough }}</td
              ><td>{{ pct(e.depth) }}</td
              ><td>{{ e.fallingDays }}</td
              ><td>{{ e.recoveryDays ?? '—' }}</td
              ><td>{{ e.underwaterDays }}{{ e.recovered ? '' : '+' }}</td
              ><td
                >{{ e.recovered ? e.end : '尚未修复' }}{{ e.gap ? ' · 含长观测间隔' : '' }}</td
              ></tr
            >
          </tbody></table
        >
      </div>
      <div class="cycle-controls"
        ><button :disabled="page === 0" @click="page--">上一页</button
        ><span>{{ page + 1 }} / {{ pages }}</span
        ><button :disabled="page + 1 >= pages" @click="page++">下一页</button></div
      >
    </template>
    <p class="definition"
      >按可用历史的收盘高点识别，可能截断更早的周期；高点和低点为事后确认。未修复周期不计入修复耗时中位数，长于7日的观测间隔断线（可能包含市场长假）。此处不使用上方季节性年份筛选。</p
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { SeasonalPoint } from '../charts/seasonality';
  import { drawdownCycles } from '../charts/cycleAnalysis';

  const props = defineProps<{ observations: SeasonalPoint[] }>();
  const threshold = ref(20),
    selected = ref<string[]>([]),
    page = ref(0);
  const data = computed(() => drawdownCycles(props.observations, threshold.value));
  const ordered = computed(() => [...data.value.episodes].reverse());
  const pages = computed(() => Math.max(1, Math.ceil(ordered.value.length / 10)));
  const paged = computed(() => ordered.value.slice(page.value * 10, (page.value + 1) * 10));
  watch(
    [data, threshold],
    ([d, value], old) => {
      if (!old?.[0] || value !== old[1]) {
        selected.value = [...d.episodes]
          .reverse()
          .slice(0, 5)
          .map((e) => e.peak);
        page.value = 0;
      } else {
        selected.value = selected.value.filter((key) => d.episodes.some((e) => e.peak === key));
        page.value = Math.min(page.value, pages.value - 1);
      }
    },
    { immediate: true },
  );
  function toggle(key: string) {
    selected.value = selected.value.includes(key)
      ? selected.value.filter((k) => k !== key)
      : [...selected.value, key].slice(0, 5);
  }
  const pct = (v: number | null) => (v == null ? '—' : `${v.toFixed(2)}%`);
  const host = ref<HTMLDivElement | null>(null),
    chart = useECharts(host as Ref<HTMLDivElement>);
  watch(
    [data, selected],
    async () => {
      await nextTick();
      chart.setOptions(
        {
          tooltip: {
            trigger: 'axis',
            valueFormatter: (v) => {
              const value = Array.isArray(v) ? v.at(-1) : v;
              return pct(value == null ? null : Number(value));
            },
          },
          legend: { type: 'scroll' },
          grid: { left: 60, right: 25, top: 45, bottom: 75 },
          xAxis: { type: 'value', name: '日历天', min: 0 },
          yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
          dataZoom: [{ type: 'inside' }, { type: 'slider', bottom: 12, height: 20 }],
          series: data.value.episodes
            .filter((e) => selected.value.includes(e.peak))
            .map((e) => ({
              name: e.peak + (e.recovered ? '' : ' · 未修复'),
              type: 'line',
              showSymbol: false,
              connectNulls: false,
              data: e.curve.map((p) => [p.day, p.value]),
              lineStyle: { width: e.recovered ? 1.6 : 3 },
            })),
        },
        true,
      );
    },
    { immediate: true, deep: true },
  );
</script>
<style scoped lang="less" src="./cyclePanels.less"></style>
