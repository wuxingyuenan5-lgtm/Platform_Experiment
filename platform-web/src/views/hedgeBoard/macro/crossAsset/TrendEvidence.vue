<template>
  <div class="trend-evidence">
    <p v-if="typeof source.listing?.firstTradingDate === 'string'" class="screening-muted"
      >来源披露的交易起点 {{ source.listing.firstTradingDate }} ·
      {{ source.listing.note }}；上市前不补造长周期历史。</p
    >
    <p v-if="signalAt && index < 0" role="status" class="screening-warning"
      >该信号观测日不在当前有效原生历史中。</p
    >
    <template v-if="bar && assessment">
      <p class="screening-muted"
        >{{ signalAt ? '信号K线起始日' : source.frame === '1D' ? '有效行情日' : '有效K线起始日' }}
        {{ day(bar.t) }} · {{ index + 1 }}根有效K线 ·
        {{
          source.rolling && index === data.bars.length - 1 && !source.lastBarComplete
            ? '末根未完成，仅供预览'
            : source.lastBarComplete
            ? '末根已确认'
            : '原生未确认末根已剔除'
        }}</p
      >
      <details open
        ><summary
          >{{ signalAt ? '信号观测日判定依据' : '当前判定依据' }} ·
          {{ directionLabel(assessment.direction) }}</summary
        >
        <div class="trend-evidence-grid"
          ><article v-for="system in SYSTEMS" :key="system"
            ><h4
              >{{ SYSTEM_NAMES[system] }} ·
              {{ directionLabel(assessment.systems[system].direction) }}</h4
            ><small>{{ system === 'zlma' ? '主方向判定' : '均线参考' }}</small
            ><p>{{ assessment.systems[system].reason }}</p
            ><p v-if="!assessment.systems[system].ready"
              >{{
                system === 'pma'
                  ? 'EMA676种子残余 ' +
                    (maturity(676, index + 1).residual * 100).toFixed(1) +
                    '%，需≤1%；'
                  : ''
              }}当前历史不足</p
            ><p v-else-if="assessment.systems[system].raw !== assessment.systems[system].direction"
              >方向候选尚未完成连续确认</p
            ><dl v-if="assessment.systems[system].ready"
              ><div v-for="e in assessment.systems[system].evidence" :key="e.label"
                ><dt>{{ e.label }}</dt
                ><dd>{{ e.value.toFixed(2) }} ATR · {{ directionLabel(e.side) }}</dd></div
              ></dl
            ></article
          ></div
        >
      </details>
      <details
        ><summary>指标数值与价格偏离 · {{ keys.length }}条曲线</summary
        ><div class="screening-table"
          ><table
            ><thead
              ><tr
                ><th>指标</th><th>数值</th><th>价格偏离</th><th>价格位置</th><th>近3根斜率</th
                ><th>历史状态</th></tr
              ></thead
            ><tbody
              ><tr v-for="key in keys" :key="key"
                ><th>{{ key }}</th
                ><td>{{ number(data.lines[key][index]) }}</td
                ><td>{{ deviation(key) }}</td
                ><td>{{ position(key) }}</td
                ><td>{{ slope(key) }}</td
                ><td>{{ historyState(key) }}</td></tr
              ></tbody
            ></table
          ></div
        ><p v-if="!keys.length">当前仅显示价格K线。</p></details
      >
    </template>
    <p v-else-if="!signalAt" role="status">尚无已完成K线，趋势暂不判定。</p>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { compute, maturity, type SnapshotSeries } from './engine';
  import {
    classify,
    directionLabel,
    GROUP_LINES,
    SYSTEM_NAMES,
    SYSTEMS,
    type System,
  } from './rules';

  const props = defineProps<{ source: SnapshotSeries; groups: System[]; signalAt?: number }>();
  const data = computed(() =>
    compute(props.source.bars, props.source.lastBarComplete === true || !!props.source.rolling),
  );
  const index = computed(() =>
    props.signalAt == null
      ? data.value.bars.length - 1
      : data.value.bars.findIndex((b) => b.t === props.signalAt),
  );
  const bar = computed(() => data.value.bars[index.value]);
  const assessment = computed(() => classify(data.value).history[index.value]);
  const keys = computed(() => props.groups.flatMap((s) => GROUP_LINES[s]));
  const day = (t: number) => new Date(t * 1000).toISOString().slice(0, 10);
  const number = (n: number | null | undefined) => (n == null ? '—' : n.toFixed(4));
  const period = (key: string) => Number(key.replace(/\D/g, '')) || 15;
  const eligible = (key: string) => index.value + 1 >= period(key);
  function deviation(key: string) {
    const value = data.value.lines[key][index.value];
    return value && bar.value ? ((bar.value.c / value - 1) * 100).toFixed(2) + '%' : '—';
  }
  function position(key: string) {
    const value = data.value.lines[key][index.value];
    return !eligible(key) || value == null
      ? '历史不足'
      : bar.value.c > value
      ? '线上'
      : bar.value.c < value
      ? '线下'
      : '持平';
  }
  function slope(key: string) {
    const values = data.value.lines[key],
      value = values[index.value],
      previous = values[index.value - 3];
    return !eligible(key) || value == null || previous == null
      ? '—'
      : value > previous
      ? '上行'
      : value < previous
      ? '下行'
      : '走平';
  }
  function historyState(key: string) {
    return key === 'ZLMA'
      ? index.value + 1 < 60
        ? '不足60根'
        : '观察窗完整'
      : key.startsWith('MA')
      ? data.value.lines[key][index.value] == null
        ? '历史不足'
        : '窗口完整'
      : maturity(period(key), index.value + 1).label;
  }
</script>
<style scoped>
  .trend-evidence {
    margin: 12px 0;
  }

  .trend-evidence-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .trend-evidence-grid article {
    min-width: 0;
    padding: 10px;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
    font-size: 11px;
  }

  .trend-evidence-grid h4 {
    margin: 0 0 6px;
    font-size: 12px;
  }

  .trend-evidence-grid p {
    margin: 5px 0;
    color: #7a8797;
  }

  .trend-evidence-grid dl {
    margin: 8px 0 0;
  }

  .trend-evidence-grid dl > div {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 4px;
    margin: 4px 0;
  }

  @media (max-width: 650px) {
    .trend-evidence-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
