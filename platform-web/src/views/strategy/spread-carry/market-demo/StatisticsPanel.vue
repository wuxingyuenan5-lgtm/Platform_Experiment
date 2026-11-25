<template>
  <div class="analysis-stack" data-testid="spread-statistics">
    <section class="analysis-panel">
      <header class="analysis-head"
        ><div><h2>统计分析</h2><p>先描述分布，再检查稳定性；价差跨过零，仍以点数衡量波动。</p></div
        ><button class="analysis-button" @click="exportSamples">导出样本 CSV</button></header
      >
      <div class="analysis-controls"
        ><label
          >序列<select v-model="series" aria-label="统计序列"
            ><option value="mid">中间价差</option
            ><option value="buy">买价差 A</option
            ><option value="sell">卖价差 B</option></select
          ></label
        ><label
          >时段<select v-model="session" aria-label="统计时段"
            ><option value="全部">全部时段</option
            ><option>亚洲</option
            ><option>欧洲</option
            ><option>美国</option></select
          ></label
        ><label
          >单位<select v-model="unit" aria-label="统计单位"
            ><option value="points">价差点</option
            ><option value="bps">bps / 4,000 基准</option></select
          ></label
        ><span class="sample-range"
          >{{ date(quality.start) }} — {{ date(quality.end) }} · 北京时间</span
        ></div
      >
      <div class="analysis-metrics stats-summary"
        ><div
          ><span>有效观测 / 交易日</span
          ><strong data-testid="stats-sample-count"
            >{{ stats.n }} <small>/ {{ quality.days }} 日</small></strong
          ><small>30 分钟采样 · {{ quality.breaks }} 处非连续边界</small></div
        ><div
          ><span>均值 / 中位数</span
          ><strong
            >{{ fmt(stats.mean) }} <small>/ {{ fmt(stats.median) }}</small></strong
          ><small>{{ unitLabel }} · 所选历史全部样本</small></div
        ><div
          ><span>水平标准差</span
          ><strong
            >{{ fmt(stats.std) }} <small>{{ unitLabel }}</small></strong
          ><small>样本标准差 · n − 1 分母</small></div
        ><div
          ><span>30 分钟变动标准差</span
          ><strong
            >{{ fmt(changeStats.std) }} <small>{{ unitLabel }}</small></strong
          ><small>{{ quality.pairs }} 对连续观测 · 不年化</small></div
        ></div
      >
      <p class="analysis-caption"
        >买卖价差使用逐时点的合成点差；时段筛选后的隔夜与缺口不参与连续变化计算。顶部情景仅改变当前快照，不改写历史分布。</p
      >
    </section>
    <nav class="analysis-pills" aria-label="统计视角"
      ><button
        v-for="item in views"
        :key="item.key"
        :aria-pressed="view === item.key"
        @click="view = item.key"
        >{{ item.label }}</button
      ></nav
    >
    <template v-if="view === 'distribution'">
      <div class="analysis-two"
        ><section class="analysis-panel"
          ><header class="analysis-head"
            ><div><h2>价差分布与尾部</h2><p>柱高为观测频数；保留所有极端值</p></div></header
          ><DemoChart :option="histogramOption" label="价差频数直方图与当前值" /><p
            class="analysis-caption"
            >当前{{ seriesNames[series] }} {{ fmt(current) }} {{ unitLabel }}，处于所选样本
            {{ fmt(currentPercentile, 1) }}% 分位。历史分位只表示位置，不代表未来回归概率。</p
          ></section
        ><section class="analysis-panel"
          ><header class="analysis-head"
            ><div><h2>经验累计分布</h2><p>横轴价差，纵轴为不高于该值的样本比例</p></div></header
          ><DemoChart :option="cdfOption" label="价差经验累计分布函数" /><p class="analysis-caption"
            >均值 {{ fmt(stats.mean) }} · 中位数 {{ fmt(stats.median) }} · 稳健尺度 1.4826 × MAD
            {{ fmt(stats.mad === null ? null : stats.mad * 1.4826) }} {{ unitLabel }}。</p
          ></section
        ></div
      >
      <section class="analysis-panel"
        ><header class="analysis-head"
          ><div><h2>分位与形态</h2><p>尾部范围、中间区间与偏态分别看</p></div></header
        ><div class="quantile-grid"
          ><div v-for="item in quantiles" :key="item.label"
            ><span>{{ item.label }}</span
            ><strong>{{ fmt(item.value) }}</strong></div
          ></div
        ><div class="shape-row"
          ><span
            >最小 / 最大 <b>{{ fmt(stats.min) }} / {{ fmt(stats.max) }}</b></span
          ><span
            >四分位距
            <b>{{
              fmt(stats.p75 === null || stats.p25 === null ? null : stats.p75 - stats.p25)
            }}</b></span
          ><span
            >偏度 <b>{{ fmt(stats.skew) }}</b></span
          ><span
            >超额峰度 <b>{{ fmt(stats.excessKurtosis) }}</b></span
          ></div
        ><p class="analysis-caption"
          >偏度与峰度为样本中心矩描述；至少 20
          个观测且方差非零才展示。厚尾与单次极端偏离都可能改变均值，不能据此确认正态分布。</p
        ></section
      >
    </template>
    <template v-else-if="view === 'stability'">
      <section class="analysis-panel"
        ><header class="analysis-head"
          ><div><h2>中枢有没有漂移</h2><p>向后滚动的中位数与 P10 / P90，不使用未来观测</p></div
          ><div class="analysis-controls"
            ><label
              >滚动窗口<select v-model.number="rollingSize" aria-label="滚动统计窗口"
                ><option :value="12">连续 6 小时</option
                ><option :value="24">连续 12 小时</option></select
              ></label
            ></div
          ></header
        ><DemoChart
          v-if="rollingHasData"
          :option="rollingOption"
          label="滚动中枢、分位区间与水平波动"
        /><div v-else class="statistics-empty" role="status"
          >所选时段没有连续 {{ rollingSize / 2 }} 小时的完整样本。请选择较短窗口或全部时段。</div
        ><div class="analysis-note"
          ><strong
            >前半窗口中位数 {{ fmt(earlier.median) }} → 后半窗口 {{ fmt(later.median) }}</strong
          >，变化
          {{
            fmt(
              earlier.median === null || later.median === null
                ? null
                : later.median - earlier.median,
            )
          }}
          {{
            unitLabel
          }}。这只是分段描述；持续迁移时应重新检验修复目标，而不是把全时期均值当作锚。</div
        ><p class="analysis-caption"
          >每次缺口或时段筛选边界后重新积累完整窗口，样本不足处断线。图中“水平波动”是该窗口价差水平的标准差，不是收益率波动率。</p
        ></section
      >
      <div class="analysis-two"
        ><section class="analysis-panel"
          ><header class="analysis-head"
            ><div><h2>偏离的记忆持续多久</h2><p>按连续观测配对的滞后相关</p></div></header
          ><DemoChart :option="acfOption" label="30分钟至6小时价差滞后相关" /><p
            class="analysis-caption"
            >仅保留整个滞后区间连续的样本，不跨休市拼接。自相关高意味着持续性强，不等于回归快。</p
          ></section
        ><section class="analysis-panel"
          ><header class="analysis-head"
            ><div><h2>回归速度的粗略估计</h2><p>含截距 AR(1) · 所选历史序列</p></div></header
          ><div class="fit-grid"
            ><div
              ><span>有效相邻样本对</span><strong>{{ fit.n }}</strong></div
            ><div
              ><span>持续系数 φ</span><strong>{{ fmt(fit.slope, 3) }}</strong></div
            ><div
              ><span>拟合 R²</span><strong>{{ fmt(fit.r2, 3) }}</strong></div
            ><div
              ><span>估计半衰期 / h</span><strong>{{ fmt(fit.halfLife, 1) }}</strong></div
            ></div
          ><div class="analysis-note">{{
            fit.halfLife === null
              ? '样本不足、方差为零或 φ 不在 (0,1)，不提供回归半衰期。'
              : '半衰期只是当前样本内的线性拟合。请与事件的实际回归耗时、中枢漂移和尾部路径一起判断。'
          }}</div
          ><p class="analysis-caption"
            >半衰期 = 0.5 × ln(0.5) / ln(φ)，单位小时；至少 40
            对连续观测。不同状态混合可能造成伪持续性，按时段重新比较。这里不把 R²
            或半衰期当作平稳性检验或交易保证。</p
          ></section
        ></div
      >
    </template>
    <template v-else>
      <section class="analysis-panel"
        ><header class="analysis-head"
          ><div
            ><h2>星期 × 小时：哪里经常偏离</h2><p>北京时间 · 单元格为中位价差，点击查看样本</p></div
          ><span class="heat-key">蓝：负价差 / 金：正价差</span></header
        ><div class="analysis-table-wrap"
          ><table class="hour-matrix"
            ><thead
              ><tr
                ><th>时刻</th><th v-for="day in weekdayNames" :key="day">{{ day }}</th></tr
              ></thead
            ><tbody
              ><tr v-for="hour in 24" :key="hour"
                ><th>{{ String(hour - 1).padStart(2, '0') }}:00</th
                ><td v-for="weekday in 5" :key="weekday"
                  ><button
                    :aria-label="`${weekdayNames[weekday - 1]} ${hour - 1}点统计`"
                    :aria-pressed="selectedCell === `${weekday}-${hour - 1}`"
                    :style="heatStyle(cell(weekday, hour - 1).median)"
                    @click="selectedCell = `${weekday}-${hour - 1}`"
                    >{{ fmt(cell(weekday, hour - 1).median, 1) }}</button
                  ></td
                ></tr
              ></tbody
            ></table
          ></div
        ><div class="cell-detail" aria-live="polite"
          >{{ selectedCellLabel }} · {{ selectedStats.n }} 个观测 · 均值
          {{ fmt(selectedStats.mean) }} · P10 / P90 {{ fmt(selectedStats.p10) }} /
          {{ fmt(selectedStats.p90) }} {{ unitLabel }}</div
        ><p class="analysis-caption"
          >空白时段不补零。单元格样本来自所选窗口，仅描述时段结构；90
          天合成历史不支持年度季节性结论。</p
        ></section
      >
      <section class="analysis-panel"
        ><header class="analysis-head"
          ><div><h2>分组比较</h2><p>分布宽度与连续价差变动强度分别统计</p></div
          ><div class="analysis-controls"
            ><label
              >分组<select v-model="groupBy" aria-label="统计分组"
                ><option value="session">交易时段</option
                ><option value="weekday">星期</option
                ><option value="month">月份</option></select
              ></label
            ></div
          ></header
        ><div class="analysis-table-wrap"
          ><table class="analysis-table"
            ><thead
              ><tr
                ><th>组别</th><th>观测数</th><th>均值</th><th>中位数</th><th>P10</th><th>P90</th
                ><th>水平标准差</th><th>30min 变动标准差</th></tr
              ></thead
            ><tbody
              ><tr v-for="group in groups" :key="group.key"
                ><td>{{ group.key }}</td
                ><td>{{ group.n }}</td
                ><td>{{ fmt(group.mean) }}</td
                ><td>{{ fmt(group.median) }}</td
                ><td>{{ fmt(group.p10) }}</td
                ><td>{{ fmt(group.p90) }}</td
                ><td>{{ fmt(group.std) }}</td
                ><td>{{ fmt(group.changeStd) }}</td></tr
              ></tbody
            ></table
          ></div
        ></section
      >
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import DemoChart from './DemoChart.vue';
  import { HOUR, type Observation } from './marketDemo';
  import {
    describe,
    histogram,
    contiguousPairs,
    regression,
    reversionModel,
    rollingDistribution,
    groupedDistribution,
    sampleQuality,
  } from './statistics';

  const props = defineProps<{
    rows: Observation[];
    currentMid: number | null;
    currentWidth: number;
  }>();
  const series = ref<'mid' | 'buy' | 'sell'>('mid'),
    session = ref('全部'),
    unit = ref('points'),
    view = ref('distribution');
  const rollingSize = ref(12),
    groupBy = ref('session'),
    selectedCell = ref('4-21');
  const seriesNames = { mid: '中间价差', buy: '买价差 A', sell: '卖价差 B' };
  const views = [
    { key: 'distribution', label: '分布画像' },
    { key: 'stability', label: '波动与稳定性' },
    { key: 'structure', label: '时段结构' },
  ];
  const factor = computed(() => (unit.value === 'bps' ? 2.5 : 1));
  const unitLabel = computed(() => (unit.value === 'bps' ? 'bps' : '点'));
  const offset = computed(() => (series.value === 'mid' ? 0 : series.value === 'buy' ? 1 : -1));
  const selectedRows = computed(() =>
    props.rows
      .filter((r) => session.value === '全部' || r.session === session.value)
      .map((r) => ({ ...r, mid: (r.mid + (offset.value * (r.width ?? 1.1)) / 2) * factor.value })),
  );
  const values = computed(() => selectedRows.value.map((r) => r.mid));
  const stats = computed(() => describe(values.value));
  const quality = computed(() => sampleQuality(selectedRows.value));
  const changeStats = computed(() =>
    describe(contiguousPairs(selectedRows.value).map((p) => p.y - p.x)),
  );
  const current = computed(() =>
    props.currentMid === null
      ? null
      : (props.currentMid + (offset.value * props.currentWidth) / 2) * factor.value,
  );
  const currentPercentile = computed(() =>
    current.value === null || !values.value.length
      ? null
      : (values.value.filter((v) => v <= current.value!).length / values.value.length) * 100,
  );
  const quantiles = computed(() =>
    [
      ['P01', stats.value.p01],
      ['P05', stats.value.p05],
      ['P10', stats.value.p10],
      ['P25', stats.value.p25],
      ['P50', stats.value.median],
      ['P75', stats.value.p75],
      ['P90', stats.value.p90],
      ['P95', stats.value.p95],
      ['P99', stats.value.p99],
    ].map(([label, value]) => ({ label: String(label), value })),
  );
  const earlier = computed(() =>
    describe(values.value.slice(0, Math.floor(values.value.length / 2))),
  );
  const later = computed(() => describe(values.value.slice(Math.floor(values.value.length / 2))));
  const fit = computed(() => reversionModel(selectedRows.value));
  const bins = computed(() => histogram(values.value));
  const fmt = (v: unknown, digits = 2) =>
    typeof v === 'number' && Number.isFinite(v)
      ? v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
      : '—';
  const date = (time: number | null) =>
    time === null ? '—' : new Date(time + 8 * HOUR).toISOString().slice(5, 16).replace('T', ' ');
  const common = {
    animation: false,
    textStyle: {
      color: '#6c8097',
      fontFamily: 'Segoe UI, Microsoft YaHei, sans-serif',
      fontSize: 11,
    },
    grid: { left: 48, right: 34, top: 40, bottom: 48 },
    tooltip: { trigger: 'axis', confine: true },
  };
  const currentLine = computed(() =>
    current.value === null
      ? undefined
      : {
          symbol: 'none',
          label: { formatter: '当前', position: 'insideEndTop' },
          lineStyle: { color: '#b38944' },
          data: [{ xAxis: current.value }],
        },
  );
  const histogramOption = computed(() => ({
    ...common,
    xAxis: {
      type: 'value',
      name: unitLabel.value,
      nameLocation: 'middle',
      nameGap: 27,
      axisLabel: { formatter: (v: number) => fmt(v, 1), hideOverlap: true },
      min: Math.min(stats.value.min ?? 0, current.value ?? Infinity) - factor.value,
      max: Math.max(stats.value.max ?? 0, current.value ?? -Infinity) + factor.value,
    },
    yAxis: { type: 'value', name: '观测数' },
    series: [
      {
        name: '频数',
        type: 'bar',
        barWidth: '85%',
        itemStyle: { color: '#8baed6' },
        data: bins.value.map((b) => [(b.low + b.high) / 2, b.count]),
        markLine: currentLine.value,
      },
    ],
  }));
  const cdfOption = computed(() => {
    const sorted = [...values.value].sort((a, b) => a - b);
    const points = sorted.flatMap((v, i) =>
      i === sorted.length - 1 || sorted[i + 1] !== v ? [[v, ((i + 1) / sorted.length) * 100]] : [],
    );
    return {
      ...common,
      xAxis: {
        type: 'value',
        name: unitLabel.value,
        nameLocation: 'middle',
        nameGap: 27,
        axisLabel: { formatter: (v: number) => fmt(v, 1), hideOverlap: true },
      },
      yAxis: { type: 'value', min: 0, max: 100, name: '累计 %' },
      series: [
        {
          name: '经验累计分布',
          type: 'line',
          step: 'end',
          showSymbol: false,
          data: points,
          lineStyle: { color: '#438a91', width: 2 },
          areaStyle: { color: '#438a91', opacity: 0.06 },
          markLine: currentLine.value,
        },
      ],
    };
  });
  const rollingRows = computed(() => rollingDistribution(selectedRows.value, rollingSize.value));
  const rollingHasData = computed(() => rollingRows.value.some((r) => r.median !== null));
  const rollingOption = computed(() => {
    const rolling = rollingRows.value;
    return {
      ...common,
      legend: { top: 0, textStyle: { fontSize: 11 } },
      xAxis: { type: 'time', axisLabel: { formatter: (v: number) => date(v).slice(0, 5) } },
      yAxis: [
        { type: 'value', name: unitLabel.value },
        { type: 'value', name: '水平波动' },
      ],
      dataZoom: [{ type: 'inside' }],
      series: (
        [
          ['median', '滚动中枢', '#3169b3'],
          ['p10', 'P10', '#a9bed6'],
          ['p90', 'P90', '#a9bed6'],
          ['std', '水平波动', '#bc9b61'],
        ] as const
      ).map(([key, name, color]) => ({
        name,
        type: 'line',
        yAxisIndex: key === 'std' ? 1 : 0,
        showSymbol: false,
        connectNulls: false,
        lineStyle: {
          color,
          width: key === 'median' ? 2 : 1,
          type: key === 'std' ? 'dashed' : 'solid',
        },
        itemStyle: { color },
        data: rolling.map((r) => [r.time, r[key]]),
      })),
    };
  });
  const acfOption = computed(() => ({
    ...common,
    xAxis: {
      type: 'category',
      name: '小时',
      data: Array.from({ length: 12 }, (_, i) => (i + 1) / 2),
    },
    yAxis: { type: 'value', min: -1, max: 1, name: '相关系数' },
    series: [
      {
        name: '滞后相关',
        type: 'bar',
        itemStyle: { color: '#8baed6' },
        data: Array.from({ length: 12 }, (_, i) => {
          const pairs = contiguousPairs(selectedRows.value, i + 1);
          return pairs.length >= 20 ? regression(pairs).correlation : null;
        }),
      },
    ],
  }));
  const weekdayNames = ['周一', '周二', '周三', '周四', '周五'];
  const cells = computed(() => {
    const result = new Map<string, number[]>();
    selectedRows.value.forEach((r) => {
      const d = new Date(r.time + 8 * HOUR),
        key = `${d.getUTCDay()}-${d.getUTCHours()}`;
      result.set(key, [...(result.get(key) || []), r.mid]);
    });
    return new Map([...result].map(([key, v]) => [key, describe(v)]));
  });
  const cell = (day: number, hour: number) => cells.value.get(`${day}-${hour}`) ?? describe([]);
  const selectedStats = computed(() => cells.value.get(selectedCell.value) ?? describe([]));
  const selectedCellLabel = computed(() => {
    const [day, hour] = selectedCell.value.split('-').map(Number);
    return `${weekdayNames[day - 1]} ${String(hour).padStart(2, '0')}:00`;
  });
  const heatStyle = (value: number | null) => ({
    background:
      value === null
        ? '#f7f9fc'
        : value >= 0
        ? `rgba(193,154,83,${0.08 + Math.min(0.5, Math.abs(value) / (12 * factor.value))})`
        : `rgba(75,124,186,${0.08 + Math.min(0.5, Math.abs(value) / (12 * factor.value))})`,
  });
  const groups = computed(() =>
    groupedDistribution(selectedRows.value, (r) => {
      const d = new Date(r.time + 8 * HOUR);
      return groupBy.value === 'session'
        ? r.session
        : groupBy.value === 'weekday'
        ? weekdayNames[d.getUTCDay() - 1]
        : d.toISOString().slice(0, 7);
    }).sort((a, b) => a.key.localeCompare(b.key, 'zh-CN')),
  );
  function exportSamples() {
    const csv = [
      '数据类型,北京时间,时段,序列,单位,数值',
      ...selectedRows.value.map(
        (r) =>
          `合成演示,${new Date(r.time + 8 * HOUR).toISOString().slice(0, 19).replace('T', ' ')},${
            r.session
          },${seriesNames[series.value]},${unitLabel.value},${r.mid}`,
      ),
    ].join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = '跨所价差_演示统计样本.csv';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>
<style scoped lang="less">
  @import './researchPanels.less';

  .statistics-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 180px;
    padding: 20px;
    background: #f8fafc;
    color: #8393a8;
    font-size: 12px;
  }

  .stats-summary {
    margin-top: 24px;
  }

  .sample-range {
    margin-left: auto;
    color: #8493a5;
    font-size: 11px;
  }

  .quantile-grid {
    display: grid;
    grid-template-columns: repeat(9, 1fr);
    gap: 10px;
  }

  .quantile-grid > div {
    display: grid;
    padding: 15px 8px;
    border-radius: 4px;
    background: #f6f8fc;
    text-align: center;
    gap: 9px;
  }

  .quantile-grid span {
    color: #7b8fa7;
    font-size: 11px;
  }

  .quantile-grid strong {
    color: #2d4e73;
    font-size: 16px;
    font-weight: 500;
  }

  .shape-row {
    display: flex;
    flex-wrap: wrap;
    margin-top: 20px;
    color: #7a8ca3;
    font-size: 11px;
    gap: 24px;
  }

  .shape-row b {
    margin-left: 8px;
    color: #3e5f83;
    font-weight: 500;
  }

  .fit-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 26px;
    margin: 28px 0;
  }

  .fit-grid > div {
    display: grid;
    gap: 10px;
  }

  .fit-grid span {
    color: #7f90a5;
    font-size: 11px;
  }

  .fit-grid strong {
    color: #365779;
    font-size: 27px;
    font-weight: 500;
  }

  .heat-key {
    color: #7c8ba0;
    font-size: 11px;
  }

  .hour-matrix {
    width: 100%;
    border-spacing: 5px 3px;
    border-collapse: separate;
    font-size: 11px;
  }

  .hour-matrix th {
    padding: 4px;
    color: #7b8ca3;
    font-weight: 500;
  }

  .hour-matrix td {
    padding: 0;
  }

  .hour-matrix button {
    width: 100%;
    min-width: 43px;
    padding: 5px;
    border: 1px solid transparent;
    border-radius: 3px;
    color: #46617e;
    cursor: pointer;
    font-variant-numeric: tabular-nums;
  }

  .hour-matrix button[aria-pressed='true'] {
    border-color: #3169b3;
    outline: 1px solid #3169b3;
  }

  .cell-detail {
    margin-top: 16px;
    padding: 13px;
    background: #f3f7fc;
    color: #42658e;
    font-size: 12px;
  }

  @media (max-width: 900px) {
    .quantile-grid {
      grid-template-columns: repeat(5, 1fr);
    }

    .sample-range {
      width: 100%;
      margin-left: 0;
    }
  }

  @media (max-width: 540px) {
    .quantile-grid {
      grid-template-columns: repeat(3, 1fr);
    }

    .shape-row {
      gap: 12px;
    }
  }
</style>
