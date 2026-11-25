<template>
  <div class="analysis-stack" data-testid="event-path-research">
    <section class="analysis-panel"
      ><header class="analysis-head"
        ><div
          ><h2>修复之前，会先承受什么</h2><p>按同一批独立偏离事件比较目标、风险线与时间先后</p></div
        ><div class="analysis-controls"
          ><label
            >最长观察<select v-model.number="maxHours" aria-label="事件最长观察"
              ><option :value="2">2 小时</option
              ><option :value="8">8 小时</option
              ><option :value="24">24 小时</option></select
            ></label
          ><label
            >不利偏离线<select v-model.number="riskLine" aria-label="事件风险线"
              ><option :value="1">1 点</option
              ><option :value="2">2 点</option
              ><option :value="4">4 点</option
              ><option :value="8">8 点</option></select
            ></label
          ></div
        ></header
      ><div class="analysis-metrics"
        ><div v-for="status in statuses" :key="status.key"
          ><span>{{ status.label }}</span
          ><strong>{{ counts[status.key] }} <small>次</small></strong
          ><small>{{ status.note }}</small></div
        ></div
      ><p class="analysis-caption"
        >30
        分钟中间价观测只能确定采样时点的先后，不知道区间内是否先碰止损。已观察到目标或风险线即归类；未触及且后续不完整保留为观察中断。这不是实际成交回测。</p
      ><div v-if="events.length < 20" class="small-sample"
        >当前仅 {{ events.length }} 个事件，优先看逐次路径，不把比例当作稳定胜率。</div
      ></section
    >
    <div class="analysis-two"
      ><section class="analysis-panel"
        ><header class="analysis-head"
          ><div><h2>单次事件路径</h2><p>向有利方向为正；目标冻结在事件起点</p></div></header
        ><div class="analysis-controls"
          ><label
            >事件<select v-model.number="selectedTime" aria-label="查看事件路径"
              ><option v-for="event in [...events].reverse()" :key="event.time" :value="event.time"
                >{{ date(event.time) }} ·
                {{ event.direction === 'long' ? '多价差' : '空价差' }}</option
              ></select
            ></label
          ></div
        ><DemoChart :option="pathOption" label="事件后有利价差变化、修复目标和不利偏离线" /><p
          class="analysis-caption"
          >{{
            selected
              ? `${date(selected.time)} · 入场中间价差 ${fmt(selected.entry)}，目标 ${fmt(
                  selected.target,
                )} 点`
              : '此窗口没有事件，扩大窗口后再研究。'
          }}。缺口之后不连线。</p
        ></section
      ><section class="analysis-panel"
        ><header class="analysis-head"
          ><div
            ><h2>等多久，空间还在不在</h2><p>固定观察期限，不以最终回归筛选成功样本</p></div
          ></header
        ><DemoChart :option="horizonOption" label="各期限有利变化P10中位数P90" /><p
          class="analysis-caption"
          >图示完整连续路径的 P10 / P50 /
          P90；右表与下表同时保留每档被排除的不完整路径数。事件起点去重，但不同事件的远期窗口仍可能重叠，不做独立显著性推断。</p
        ></section
      ></div
    >
    <section class="analysis-panel"
      ><header class="analysis-head"
        ><div
          ><h2>期限与方向的条件表现</h2
          ><p>点数口径 · 有利变动为正 · 未扣报价、手续费和 Carry</p></div
        ></header
      ><div class="analysis-table-wrap"
        ><table class="analysis-table"
          ><thead
            ><tr
              ><th>方向 / 期限</th><th>完整 / 全部</th><th>不完整</th><th>有利变化 P10</th
              ><th>中位数</th><th>P90</th><th>有利变化占比</th><th>不利偏离 P90</th
              ><th>有利偏离 P50</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in horizonRows" :key="row.key"
              ><td>{{ row.label }} · {{ row.hours }}h</td><td>{{ row.n }} / {{ row.total }}</td
              ><td>{{ row.censored }}</td
              ><td>{{ fmt(row.p10) }}</td
              ><td :class="row.median !== null && row.median >= 0 ? 'positive' : 'negative'">{{
                fmt(row.median)
              }}</td
              ><td>{{ fmt(row.p90) }}</td
              ><td>{{ row.favorable === null ? '—' : fmt(row.favorable, 1) + '%' }}</td
              ><td>{{ fmt(row.mae) }}</td
              ><td>{{ fmt(row.mfe) }}</td></tr
            ></tbody
          ></table
        ></div
      ><p class="analysis-caption"
        >最大不利偏离 MAE、最大有利偏离 MFE
        均基于该固定期限内的采样路径。采样间跳动与退出滑点未被这些数值覆盖。</p
      ></section
    >
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import DemoChart from './DemoChart.vue';
  import { HOUR, type Episode, type Observation, type Direction } from './marketDemo';
  import { firstPassage, forwardPath, horizonOutcomes } from './statistics';

  const props = defineProps<{ rows: Observation[]; events: Episode[] }>();
  const maxHours = ref(8),
    riskLine = ref(2),
    pickedTime = ref<number | null>(null);
  const selectedTime = computed({
    get: () =>
      props.events.some((e) => e.time === pickedTime.value)
        ? pickedTime.value!
        : props.events.at(-1)?.time ?? 0,
    set: (value: number) => {
      pickedTime.value = value;
    },
  });
  const selected = computed(() => props.events.find((e) => e.time === selectedTime.value));
  const statuses = [
    { key: 'target', label: '先触及修复目标', note: '不是净收益胜率' },
    { key: 'risk', label: '先触及不利偏离线', note: '最终回归也可能先超预算' },
    { key: 'timeout', label: '期限内两者均未触及', note: '仍需承担时间成本' },
    { key: 'censored', label: '观察中断 / 尚未完整', note: '不默认为成功或失败' },
  ] as const;
  const counts = computed(() => {
    const result = { target: 0, risk: 0, timeout: 0, censored: 0 };
    props.events.forEach(
      (event) => result[firstPassage(props.rows, event, maxHours.value, riskLine.value).status]++,
    );
    return result;
  });
  const horizons = [0.5, 2, 8, 24];
  const summaries = computed(() =>
    horizons.map((hours) => horizonOutcomes(props.rows, props.events, hours)),
  );
  const horizonRows = computed(() =>
    (['short', 'long'] as Direction[]).flatMap((direction) =>
      horizons.map((hours) => ({
        ...horizonOutcomes(props.rows, props.events, hours, direction),
        key: `${direction}-${hours}`,
        label: direction === 'short' ? '空价差' : '多价差',
      })),
    ),
  );
  const fmt = (v: number | null, digits = 2) =>
    v === null || !Number.isFinite(v) ? '—' : v.toFixed(digits);
  const date = (time: number) =>
    new Date(time + 8 * HOUR).toISOString().slice(5, 16).replace('T', ' ');
  const common = {
    grid: { left: 48, right: 24, top: 40, bottom: 40 },
    tooltip: { trigger: 'axis', confine: true },
    textStyle: { color: '#75879e', fontSize: 11 },
    legend: { top: 5, textStyle: { fontSize: 11 } },
  };
  const pathOption = computed(() => {
    const event = selected.value;
    const path = event ? forwardPath(props.rows, event, maxHours.value).path : [];
    return {
      ...common,
      xAxis: { type: 'value', min: 0, max: maxHours.value, name: '小时' },
      yAxis: { type: 'value', name: '有利变化 / 点' },
      series: [
        {
          name: '事件路径',
          type: 'line',
          showSymbol: true,
          symbolSize: 4,
          lineStyle: { color: '#3169b3', width: 2 },
          itemStyle: { color: '#3169b3' },
          data: path.map((p) => [p.hour, p.change]),
          markLine: {
            symbol: 'none',
            label: { position: 'insideEndTop', formatter: '{b}' },
            data: event
              ? [
                  {
                    name: '修复目标',
                    yAxis: Math.abs(event.target - event.entry),
                    lineStyle: { color: '#438a91' },
                  },
                  { name: '不利偏离线', yAxis: -riskLine.value, lineStyle: { color: '#bd5a5a' } },
                ]
              : [],
          },
        },
      ],
    };
  });
  const horizonOption = computed(() => ({
    ...common,
    xAxis: { type: 'category', data: horizons.map((h) => `${h}h`) },
    yAxis: { type: 'value', name: '有利变化 / 点' },
    series: (
      [
        ['p10', 'P10', '#bc9b61'],
        ['median', '中位数', '#3169b3'],
        ['p90', 'P90', '#438a91'],
      ] as const
    ).map(([key, name, color]) => ({
      name,
      type: 'line',
      data: summaries.value.map((s) => s[key]),
      connectNulls: false,
      itemStyle: { color },
      lineStyle: { color },
    })),
  }));
</script>
<style scoped lang="less">
  @import './researchPanels.less';

  .small-sample {
    margin-top: 14px;
    padding: 10px 13px;
    border-radius: 4px;
    background: #faf5e9;
    color: #9b773b;
    font-size: 11px;
  }
</style>
