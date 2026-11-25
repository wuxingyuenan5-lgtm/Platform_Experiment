<template>
  <component :is="embedded ? 'div' : ChartExpand" :title="embedded ? undefined : activeTitle">
    <article class="financing-chart" :class="{ 'is-embedded': embedded }">
      <header
        ><h3 v-if="!embedded">{{ activeTitle }}</h3
        ><slot name="toolbar"></slot
        ><div class="ranges"
          ><div v-if="alternate" class="chart-views" role="group" aria-label="图表视图">
            <button
              type="button"
              :class="{ active: !showAlternate }"
              :aria-pressed="!showAlternate"
              @click="showAlternate = false"
              >{{ primaryLabel }}</button
            >
            <button
              type="button"
              :class="{ active: showAlternate }"
              :aria-pressed="showAlternate"
              @click="showAlternate = true"
              >一年分位与波动区间</button
            > </div
          ><slot v-if="!showAlternate" name="range-controls"></slot
          ><template v-if="!hideRanges && !categoryAxis">
            <button
              v-for="p in presets"
              :key="p.value"
              :class="{ active: range === p.value }"
              :aria-pressed="range === p.value"
              @click="selectRange(p.value)"
              >{{ p.label }}</button
            > </template
          ><button
            v-if="allowTable"
            type="button"
            :aria-pressed="tableView"
            @click="tableView = !tableView"
            >{{ tableView ? '图表' : '查看数据' }}</button
          ></div
        ></header
      >
      <div v-if="$slots.summary && !showAlternate" class="chart-summary"
        ><slot name="summary"></slot
      ></div>
      <p v-if="note" class="definition">{{ note }}</p>
      <p v-if="!activeRows.length" class="empty">暂无有效历史</p>
      <div
        v-show="activeRows.length && !tableView"
        ref="element"
        class="plot"
        role="img"
        :aria-label="`${activeTitle}，可拖动下方${
          categoryAxis ? '滚轴' : '时间范围'
        }并悬浮查看数值`"
        @click="pickObservation"
      ></div>
      <slot
        v-if="allowTable && tableView && activeRows.length && $slots['data-table']"
        name="data-table"
      ></slot>
      <template v-else-if="allowTable && tableView && activeRows.length">
        <div class="data-scroll" tabindex="0" :aria-label="`${activeTitle}数据表`">
          <table>
            <thead
              ><tr
                ><th scope="col">日期</th><th v-if="hasContract" scope="col">合约</th
                ><th v-for="series in activeLines" :key="series.key" scope="col"
                  >{{ series.name }}（{{ series.unit }}）</th
                ></tr
              ></thead
            >
            <tbody
              ><tr v-for="row in tableRows" :key="row.date"
                ><th scope="row">{{ row.date }}</th
                ><td v-if="hasContract">{{ row.contract || '—' }}</td
                ><td v-for="series in activeLines" :key="series.key">{{
                  format(row[series.key])
                }}</td></tr
              ></tbody
            >
          </table>
        </div>
        <div class="table-pages"
          ><span>{{ filtered.length }} 条</span
          ><button type="button" :disabled="tablePage <= 1" @click="tablePage--">上一页</button
          ><span>{{ tablePage }} / {{ tablePageCount }}</span
          ><button type="button" :disabled="tablePage >= tablePageCount" @click="tablePage++"
            >下一页</button
          ></div
        >
      </template>
    </article>
  </component>
</template>

<script setup lang="ts">
  import { computed, inject, nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../../components/ChartExpand.vue';
  import {
    RESEARCH_HISTORY_RANGE_KEY,
    DEFAULT_RESEARCH_HISTORY_YEARS,
    RESEARCH_HISTORY_YEARS,
    windowStart,
  } from '../../components/indexValuationStats';

  export interface FinanceLine {
    key: string;
    name: string;
    color: string;
    unit: string;
    bar?: boolean;
    barColor?: 'series';
    right?: boolean;
    axis?: 0 | 1 | 2 | 3;
    hideAxis?: boolean;
    stack?: string;
    defaultSelected?: boolean;
    lineType?: 'solid' | 'dashed' | 'dotted';
    width?: number;
    markLatest?: boolean;
  }
  export interface FinanceRow {
    date: string;
    [key: string]: string | number | null | boolean | undefined;
  }
  const props = defineProps<{
    title: string;
    rows: FinanceRow[];
    lines: FinanceLine[];
    alternate?: { rows: FinanceRow[]; lines: FinanceLine[]; title?: string };
    primaryLabel?: string;
    note?: string;
    embedded?: boolean;
    independentDates?: boolean;
    bounds?: [number, number];
    markOverflow?: boolean;
    initialRange?: number;
    rangeDays?: number;
    rangeYears?: number;
    axisNames?: [string, string];
    allowTable?: boolean;
    hideRanges?: boolean;
    pickDate?: boolean;
    categoryAxis?: boolean;
  }>();
  const calendarRanges = inject(RESEARCH_HISTORY_RANGE_KEY, false) && !props.hideRanges;
  const presets = calendarRanges
    ? RESEARCH_HISTORY_YEARS.map((years) => ({
        value: years,
        label: years ? `${years}年` : '全部',
      }))
    : [
        { value: 90, label: '3个月' },
        { value: 365, label: '1年' },
        { value: 1095, label: '3年' },
        { value: 0, label: '全部' },
      ];
  const lineAxis = (line: FinanceLine) => line.axis ?? (line.right ? 1 : 0);
  const emit = defineEmits<{
    range: [days: number];
    'range-years': [years: number];
    pick: [date: string];
  }>();
  const element = ref<HTMLDivElement | null>(null);
  const chart = useECharts(element as Ref<HTMLDivElement>, 'light');
  const showAlternate = ref(false);
  const activeTitle = computed(() =>
    showAlternate.value ? props.alternate?.title ?? props.title : props.title,
  );
  const activeRows = computed(
    () => (showAlternate.value ? props.alternate?.rows : props.rows) ?? [],
  );
  const activeLines = computed(
    () => (showAlternate.value ? props.alternate?.lines : props.lines) ?? [],
  );
  const controlledRange = () => (calendarRanges ? props.rangeYears : props.rangeDays);
  const range = ref(
    controlledRange() ??
      (calendarRanges ? DEFAULT_RESEARCH_HISTORY_YEARS : props.initialRange ?? 365),
  );
  const tableView = ref(false),
    tablePage = ref(1);
  watch(controlledRange, (value) => {
    if (value !== undefined) range.value = value;
  });
  function selectRange(value: number) {
    range.value = value;
    if (calendarRanges) emit('range-years', value);
    else emit('range', value);
  }
  const numeric = (value: unknown) =>
    value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
  const filtered = computed(() => {
    const last = activeRows.value.at(-1)?.date;
    if (!last || !range.value || props.categoryAxis) return activeRows.value;
    if (calendarRanges) {
      const cutoff = windowStart(range.value, last.slice(0, 10));
      return activeRows.value.filter((r) => r.date >= cutoff);
    }
    const start = new Date(last.length === 10 ? last + 'T00:00:00Z' : last);
    start.setUTCDate(start.getUTCDate() - range.value);
    return activeRows.value.filter((r) => r.date >= start.toISOString().slice(0, 10));
  });
  function pickObservation(event: MouseEvent) {
    if (!props.pickDate || !element.value) return;
    const instance = chart.getInstance();
    const bounds = element.value.getBoundingClientRect();
    const pixel: [number, number] = [event.clientX - bounds.left, event.clientY - bounds.top];
    if (!instance?.containPixel({ gridIndex: 0 }, pixel)) return;
    const index = Math.round(Number(instance.convertFromPixel({ xAxisIndex: 0 }, pixel[0])));
    const row = filtered.value[index];
    if (row) emit('pick', row.date);
  }
  const escape = (value: unknown) =>
    String(value).replace(
      /[&<>"']/g,
      (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c),
    );
  const displayDate = (value: string) =>
    value.includes('T')
      ? new Intl.DateTimeFormat('sv-SE', {
          timeZone: 'America/New_York',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        }).format(new Date(value)) + ' NY'
      : value;
  const format = (v: unknown) =>
    numeric(v) == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 4 });
  const tableRows = computed(() =>
    filtered.value
      .slice()
      .reverse()
      .slice((tablePage.value - 1) * 20, tablePage.value * 20),
  );
  const tablePageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / 20)));
  const hasContract = computed(() => filtered.value.some((row) => row.contract));
  watch(filtered, () => {
    tablePage.value = 1;
  });
  let renderedIdentity = '';
  watch(
    [filtered, tableView, activeLines, () => props.bounds, () => props.markOverflow],
    async () => {
      await nextTick();
      const rows = filtered.value;
      if (!element.value || !rows.length || tableView.value) return;
      const lines = activeLines.value;
      const identity = `${props.title}:${range.value}:${lines.map((l) => l.key).join(',')}`;
      const currentZoom =
        renderedIdentity === identity
          ? (
              chart.getInstance()?.getOption().dataZoom as
                | Array<{ start?: number; end?: number }>
                | undefined
            )?.[0]
          : undefined;
      const axisUnits = Array.from(
        { length: Math.max(1, ...lines.map(lineAxis)) + 1 },
        (_, i) => lines.find((l) => lineAxis(l) === i)?.unit || '',
      );
      const hiddenAxis = (i: number) => lines.some((l) => lineAxis(l) === i && l.hideAxis);
      const rightAxisCount = axisUnits.filter((unit, i) => i && unit && !hiddenAxis(i)).length;
      const selected = {
        ...Object.fromEntries(lines.map((l) => [l.name, l.defaultSelected ?? true])),
        ...(
          chart.getInstance()?.getOption().legend as
            | Array<{ selected?: Record<string, boolean> }>
            | undefined
        )?.[0]?.selected,
      };
      const option = {
        animation: false,
        color: lines.map((l) => l.color),
        legend: {
          selected,
          top: 0,
          type: 'scroll',
          textStyle: { fontSize: 11, color: '#65809b', fontFamily: 'inherit' },
        },
        grid: {
          left: 65,
          right: rightAxisCount ? rightAxisCount * 70 : 28,
          top: 65,
          bottom: props.categoryAxis ? 88 : 65,
        },
        tooltip: {
          trigger: 'axis',
          confine: true,
          axisPointer: { type: 'cross' },
          formatter: (
            items: Array<{
              dataIndex: number;
              axisValue?: string;
              seriesIndex: number;
              marker: string;
            }>,
          ) => {
            if (!items.length) return '';
            const row = props.independentDates
              ? rows.find((row) => row.date === items[0].axisValue)
              : rows[items[0].dataIndex];
            if (!row) return '';
            const texts = [
              escape(displayDate(row.date)) + (row.contract ? ` · ${escape(row.contract)}` : ''),
              ...items.map((item) => {
                const l = lines[item.seriesIndex];
                return `${item.marker}${escape(l.name)}：${format(row[l.key])} ${escape(l.unit)}`;
              }),
            ];
            if (row.total !== undefined) texts.push(`合计：${format(row.total)} 亿元`);
            if (row.partialWeek) texts.push('本周截至当前交易日');
            if (row.qualityNote) texts.push(escape(row.qualityNote));
            return texts.join('<br/>');
          },
        },
        xAxis: {
          type: 'category',
          data: rows.map((r) => r.date),
          boundaryGap: lines.some((l) => l.bar),
          axisLabel: {
            color: '#71869e',
            hideOverlap: true,
            formatter: (value: string) =>
              props.categoryAxis ? value : displayDate(value).slice(2),
            rotate: props.categoryAxis && rows.length > 12 ? 45 : 0,
            fontSize: 11,
          },
        },
        yAxis: axisUnits.map((unit, i) => ({
          type: 'value',
          name: props.axisNames?.[i] || unit,
          nameTextStyle: props.axisNames ? { align: i ? 'right' : 'left' } : undefined,
          position: i ? 'right' : 'left',
          offset: i > 1 ? 65 : 0,
          show: (!i || Boolean(unit)) && !hiddenAxis(i),
          scale: !lines.some((l) => lineAxis(l) === i && l.bar),
          min: !i ? props.bounds?.[0] : hiddenAxis(i) ? 'dataMin' : undefined,
          max: !i ? props.bounds?.[1] : hiddenAxis(i) ? 'dataMax' : undefined,
          splitLine: { show: !i, lineStyle: { color: '#e8eef5' } },
          axisLabel: { color: '#71869e' },
        })),
        dataZoom: [
          {
            type: 'inside',
            filterMode: 'filter',
            zoomOnMouseWheel: 'ctrl',
            moveOnMouseWheel: false,
          },
          { type: 'slider', filterMode: 'filter', height: 20, bottom: 8 },
        ],
        series: lines.map((l) => ({
          name: l.name,
          type: l.bar ? 'bar' : 'line',
          barMaxWidth: props.categoryAxis ? 24 : undefined,
          yAxisIndex: lineAxis(l),
          stack: l.stack,
          // An absent field is not a session for this series; explicit null is
          // a missing observation and must still break the line.
          data: props.independentDates
            ? rows
                .filter((r) => Object.prototype.hasOwnProperty.call(r, l.key))
                .map((r) => [r.date, numeric(r[l.key])])
            : rows.map((r) => numeric(r[l.key])),
          showSymbol: rows.filter((r) => numeric(r[l.key]) != null).length === 1,
          symbolSize: 7,
          connectNulls: false,
          markPoint:
            props.markOverflow && props.bounds && lineAxis(l) === 0
              ? {
                  symbol: 'triangle',
                  symbolSize: 10,
                  label: { show: false },
                  tooltip: {
                    trigger: 'item',
                    formatter: (p: { data: { name: string; value: number } }) =>
                      `${escape(p.data.name)}<br/>${escape(l.name)}：${format(
                        p.data.value,
                      )} ${escape(l.unit)}<br/>超出坐标范围`,
                  },
                  data: rows.flatMap((r) => {
                    const value = numeric(r[l.key]);
                    const [min, max] = props.bounds!;
                    if (value == null || (value >= min && value <= max)) return [];
                    return [
                      {
                        name: r.date,
                        coord: [r.date, value > max ? max : min],
                        value,
                        symbolRotate: value > max ? 0 : 180,
                      },
                    ];
                  }),
                }
              : l.markLatest
              ? {
                  symbol: 'circle',
                  symbolSize: 7,
                  label: { show: false },
                  data: rows
                    .filter((row) => numeric(row[l.key]) != null)
                    .slice(-1)
                    .map((row) => ({
                      name: row.date,
                      coord: [row.date, numeric(row[l.key])],
                      value: numeric(row[l.key]),
                    })),
                }
              : undefined,
          lineStyle: {
            width: l.width ?? (l.color === '#171717' ? 2.2 : 1.5),
            type: l.lineType || 'solid',
          },
          itemStyle:
            l.bar && !l.stack && l.barColor !== 'series'
              ? { color: (p: { value: number }) => (p.value >= 0 ? '#e87478' : '#35a47b') }
              : { color: l.color },
        })),
      } as EChartsOption;
      if (currentZoom && Array.isArray(option.dataZoom))
        option.dataZoom = option.dataZoom.map((zoom) => ({
          ...zoom,
          start: currentZoom.start,
          end: currentZoom.end,
        }));
      chart.setOptions(option, true);
      renderedIdentity = identity;
    },
    { immediate: true },
  );
</script>

<style scoped>
  .financing-chart.is-embedded {
    padding: 0;
    border: 0;
    background: transparent;
  }

  .financing-chart {
    margin: 14px 0;
    padding: 18px;
    border: 1px solid #d7e3ee;
    border-radius: 14px;
    background: linear-gradient(#fff, #f4f9fc);
    color: #123247;
    font-family: inherit;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    padding-right: 38px;
    gap: 12px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
  }

  .ranges,
  .chart-views {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }

  .chart-summary {
    display: grid;
    gap: 5px;
    margin-top: 10px;
    font-size: 12px;
  }

  button {
    padding: 4px 10px;
    border: 1px solid #d7e3ee;
    border-radius: 6px;
    background: #fff;
    color: #42617e;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button.active {
    background: #edf3ff;
    color: #2563eb;
  }

  button:focus-visible,
  .data-scroll:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  .data-scroll {
    margin-top: 14px;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  th,
  td {
    padding: 10px 12px;
    border-bottom: 1px solid #d7e3ee;
    text-align: right;
  }

  th {
    font-weight: 500;
  }

  thead {
    background: #f4f8fc;
  }

  th:first-child {
    text-align: left;
  }

  .table-pages {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    margin-top: 12px;
    font-size: 12px;
    gap: 10px;
  }

  .definition {
    margin: 10px 0;
    color: #71869e;
    font-size: 12px;
  }

  .plot {
    width: 100%;
    height: 380px;
  }

  .empty {
    padding: 35px;
    color: #71869e;
  }
</style>
