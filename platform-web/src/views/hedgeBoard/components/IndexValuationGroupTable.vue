<template>
  <section
    class="valuation-group"
    :class="{ 'valuation-group--industry': industryComparison }"
    :aria-label="group.name"
  >
    <header class="group-heading" :class="{ 'group-heading--custom': $slots.heading }">
      <slot name="heading"
        ><h3>{{ group.name }}</h3></slot
      >
      <time v-if="seriesDate" :datetime="seriesDate">{{ seriesDate }}</time>
    </header>
    <p :id="tierNoteId" class="tier-note">
      估值判断按主指标近10年分位分档。≤{{ lowRank }}% 低估，{{ lowRank }}% &lt; 分位 &lt;
      {{ midRank }}% 合理偏低，{{ midRank }}% ≤ 分位 &lt; {{ highRank }}% 合理偏高，≥{{ highRank }}%
      高估。主指标为股息率时，使用 100% 减原分位。
    </p>
    <div class="group-scroll" tabindex="0" :aria-label="`${group.name}数据表`">
      <table>
        <thead>
          <tr>
            <th scope="col" class="name-column">
              <button v-bind="sortAttributes('name', '指数名称')" @click="sortBy('name')"
                >指数名称</button
              >
            </th>
            <th scope="col" class="metric-column">
              <button v-bind="sortAttributes('metric', '主指标')" @click="sortBy('metric')"
                >主指标</button
              >
            </th>
            <th scope="col" class="primary-column">
              <button
                v-bind="sortAttributes('primary-value', '主指标当前值')"
                @click="sortBy('primary-value')"
                >当前值</button
              >
              <span aria-hidden="true"> / </span>
              <button
                v-bind="sortAttributes('primary-rank', '主指标10年分位')"
                @click="sortBy('primary-rank')"
                >10年分位</button
              >
            </th>
            <th scope="col" class="tier-column" :aria-describedby="tierNoteId">
              <button v-bind="sortAttributes('tier', '估值判断')" @click="sortBy('tier')"
                >估值判断</button
              >
            </th>
            <th v-for="metric in metrics" :key="metric.id" scope="col" class="valuation-metric">
              <button
                v-bind="sortAttributes(metric.id, `${metric.label}当前值`)"
                @click="sortBy(metric.id)"
                >{{ metric.label }}</button
              >
              <div class="rank-grid">
                <button
                  v-for="window in windows"
                  :key="window"
                  v-bind="
                    sortAttributes(`${metric.id}:${window}`, `${metric.label} ${window}年分位`)
                  "
                  @click="sortBy(`${metric.id}:${window}`)"
                  >{{ window }}年</button
                >
              </div>
            </th>
            <template v-if="industryComparison">
              <th
                v-for="label in industryColumns"
                :key="label"
                scope="col"
                class="industry-column"
                >{{ label }}</th
              >
            </template>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in sortedRows"
            :key="row.code"
            :class="{ selected: row.chartId === selectedId && row.chartId }"
          >
            <th scope="row">
              <button
                v-if="row.chartId"
                type="button"
                class="chart-link"
                @click="$emit('select', row.chartId)"
              >
                {{ row.name }}
              </button>
              <template v-else>{{ row.name }}</template>
              <small class="index-code">{{ row.code }}</small>
            </th>
            <td
              ><span class="metric-badge" :data-metric="row.primaryId">{{
                metricBadges[row.primaryId]
              }}</span
              ><small class="metric-label">{{ metricLabels[row.primaryId] }}</small></td
            >
            <td>
              <div class="primary-reading" :title="valueDetail(row.primary)">
                <strong>{{ showValue(row.primary.value, row.primary.unit) }}</strong>
                <span
                  class="percentile-track"
                  :class="{ 'is-empty': row.primaryRank == null }"
                  aria-hidden="true"
                >
                  <i v-if="row.primaryRank != null" :style="{ left: `${row.primaryRank}%` }"></i>
                </span>
                <span
                  :title="row.primaryId === 'dividend' ? '主指标股息率采用反向分位' : undefined"
                >
                  {{ showValue(row.primaryRank, '%') }}<sup v-if="row.primaryRankShort">*</sup>
                </span>
              </div>
            </td>
            <td>
              <span v-if="row.tier != null" class="tier" :data-tier="row.tier">{{
                tierLabels[row.tier]
              }}</span>
              <span v-else>{{ missingValue }}</span>
            </td>
            <td
              v-if="!row.chartId && !industryComparison"
              :colspan="metrics.length"
              class="unavailable valuation-metric"
              >估值序列未接入</td
            >
            <td
              v-for="cell in row.chartId || industryComparison ? row.cells : []"
              :key="cell.id"
              class="valuation-metric"
            >
              <div class="metric-value" :title="valueDetail(cell)">
                <button
                  v-if="row.chartId && cell.metricId && cell.value != null"
                  type="button"
                  class="chart-link"
                  @click="$emit('select', row.chartId, cell.metricId)"
                  >{{ showValue(cell.value, cell.unit) }}</button
                >
                <strong v-else>{{ showValue(cell.value, cell.unit) }}</strong>
                <small v-if="cell.date && cell.date !== seriesDate">{{ cell.date }}</small>
              </div>
              <div class="rank-grid">
                <span
                  v-for="rank in cell.ranks"
                  :key="rank.window"
                  :title="rank.detail"
                  :class="{
                    'rank-low': cell.id !== 'dividend' && rank.value != null && rank.value < 20,
                    'rank-high': cell.id !== 'dividend' && rank.value != null && rank.value > 80,
                  }"
                  >{{ showValue(rank.value, '%') }}<sup v-if="rank.short">*</sup></span
                >
              </div>
            </td>
            <template v-if="industryComparison">
              <td v-for="label in industryColumns" :key="label" class="industry-column">-</td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { IndexValuationChart } from '@/api/equityObservatory';
  import type { ObservationGroup } from './indexValuationSnapshot';
  import { hasShortValuationHistory, valuationStats } from './indexValuationStats';

  const props = defineProps<{
    group: ObservationGroup;
    charts?: Map<string, IndexValuationChart>;
    asOf: string;
    selectedId?: string;
    industryComparison?: boolean;
  }>();
  defineEmits<{ select: [index: string, metric?: string] }>();
  const tierNoteId = computed(() => `valuation-tier-note-${props.group.name}`);

  const metrics = [
    { id: 'pe', label: 'PE TTM', unit: '倍' },
    { id: 'pb', label: 'PB MRQ', unit: '倍' },
    { id: 'ps', label: '市销率（PS TTM）', unit: '倍' },
    { id: 'dividend', label: '股息率 TTM', unit: '%' },
    { id: 'peLyr', label: 'PE LYR', unit: '倍' },
  ] as const;
  const windows = [3, 5, 10, 15] as const;
  const industryColumns = [
    '样本数',
    '当日涨跌中位数',
    '上涨占比',
    'PE中位数',
    'PB中位数',
    '破净占比',
    '成交额占比',
    '占比分位',
    '换手中位数',
    '换手分位',
    '历史样本',
  ];
  const missingValue = computed(() => (props.industryComparison ? '-' : '—'));
  const tenYearIndex = windows.indexOf(10);
  const primaryIds = { PE: 'pe', PB: 'pb', PS: 'ps', DY: 'dividend' } as const;
  const metricBadges = { pe: 'PE', pb: 'PB', ps: 'PS', dividend: 'DY' };
  const metricLabels = { pe: '市盈率', pb: '市净率', ps: '市销率', dividend: '股息率' };
  const tierLabels = ['低估', '合理偏低', '合理偏高', '高估'];
  const [lowRank, midRank, highRank] = [20, 50, 80] as const;

  function showValue(value: number | null, unit: string) {
    return value == null
      ? missingValue.value
      : value.toLocaleString('en-US', { maximumFractionDigits: 2 }) + unit;
  }

  function metricCell(metric: (typeof metrics)[number], chart: IndexValuationChart | undefined) {
    const series = chart?.metrics.find((item) => item.id === metric.id);
    const frequency = series?.rankFrequency;
    const stats = series?.history.length
      ? windows.map((n) =>
          valuationStats(series.history, n, props.asOf, metric.id === 'dividend', frequency),
        )
      : [];
    return {
      ...metric,
      metricId: series?.id,
      value: stats[tenYearIndex]?.value ?? null,
      date: stats[tenYearIndex]?.latest?.date,
      source: series?.source,
      frequency,
      ranks: windows.map((window, i) => {
        const stat = stats[i];
        const value = stat?.rank ?? null;
        const short =
          value != null && hasShortValuationHistory(window, props.asOf, stat?.start, frequency);
        const detail = stat?.count
          ? `${window}年窗口 · ${stat.count}个${frequency === 'month' ? '月度' : '有效'}样本 · ${
              stat.start
            } 至 ${stat.end}${
              short ? ' · 历史不足该年限' : value == null ? ' · 有效样本不足或最新值无有效分位' : ''
            }`
          : `${window}年分位暂无数据`;
        return { window, value, short, detail };
      }),
    };
  }

  function valueDetail(cell: ReturnType<typeof metricCell>) {
    return [cell.source, cell.date, cell.frequency === 'month' ? '按月末样本计算分位' : '']
      .filter(Boolean)
      .join(' · ');
  }
  const rows = computed(() =>
    props.group.rows.map(([name, code, metric]) => {
      const chart = props.charts?.get(code.split('.')[0]);
      const chartId = chart?.id;
      const primaryId = primaryIds[metric];
      const cells = metrics.map((definition) => metricCell(definition, chart));
      const primary = cells.find((cell) => cell.id === primaryId)!;
      const { value: mainRank, short: primaryRankShort } = primary.ranks[tenYearIndex];
      const primaryRank = mainRank != null && metric === 'DY' ? 100 - mainRank : mainRank;
      const tier =
        primaryRank == null
          ? null
          : primaryRank <= lowRank
          ? 0
          : primaryRank < midRank
          ? 1
          : primaryRank < highRank
          ? 2
          : 3;
      const sortValues: Record<string, number | string | null> = {
        name,
        metric,
        tier,
        'primary-value': primary.value,
        'primary-rank': primaryRank,
      };
      for (const cell of cells) {
        sortValues[cell.id] = cell.value;
        for (const rank of cell.ranks) sortValues[`${cell.id}:${rank.window}`] = rank.value;
      }
      return {
        name,
        code,
        chartId,
        primaryId,
        primary,
        primaryRank,
        primaryRankShort,
        tier,
        cells,
        sortValues,
      };
    }),
  );
  const seriesDate = computed(() =>
    rows.value.reduce(
      (latest, row) =>
        row.cells.reduce(
          (date, cell) => (cell.date && cell.date > date ? cell.date : date),
          latest,
        ),
      '',
    ),
  );

  const sort = ref<{ key: string; descending: boolean }>();
  function sortBy(key: string) {
    if (sort.value?.key !== key) {
      sort.value = { key, descending: false };
    } else {
      sort.value = sort.value.descending ? undefined : { key, descending: true };
    }
  }
  function sortAttributes(key: string, label: string) {
    const direction =
      sort.value?.key === key ? (sort.value.descending ? 'desc' : 'asc') : undefined;
    return {
      type: 'button' as const,
      'aria-label': `按${label}排序${
        direction ? (direction === 'desc' ? '，当前降序，再次点击恢复默认顺序' : '，当前升序') : ''
      }`,
      title: direction === 'desc' ? '恢复默认顺序' : undefined,
      'data-direction': direction,
    };
  }
  const sortedRows = computed(() => {
    const order = sort.value;
    if (!order) return rows.value;
    return [...rows.value].sort((a, b) => {
      const x = a.sortValues[order.key];
      const y = b.sortValues[order.key];
      if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
      const diff =
        typeof x === 'number' && typeof y === 'number'
          ? x - y
          : String(x).localeCompare(String(y), 'zh-CN');
      return order.descending ? -diff : diff;
    });
  });
</script>

<style scoped>
  .valuation-group {
    min-width: 0;
    border: 1px solid #d9e3ee;
    border-radius: 8px;
    background: var(--strategy-surface, #fff);
    color: #243a51;
  }

  .group-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    padding: 10px 14px;
    border-left: 4px solid #225371;
    border-radius: 7px 7px 0 0;
    background: #f6f9fc;
    color: #596f87;
    font-size: 13px;
    gap: 4px 10px;
  }

  .group-heading h3 {
    margin: 0;
    color: #1d3950;
    font-size: 16px;
    font-weight: 600;
  }

  .group-heading--custom {
    align-items: center;
    justify-content: space-between;
  }

  .tier-note {
    margin: 0;
    padding: 7px 14px;
    color: #526880;
    font-size: 12px;
    line-height: 1.5;
  }

  .group-scroll {
    max-height: 680px;
    overflow: auto;
  }

  .group-scroll:focus-visible {
    outline: 2px solid #1d4ed8;
    outline-offset: 2px;
  }

  table {
    width: 100%;
    min-width: max(1900px, 120%);
    table-layout: fixed;
    border-spacing: 0;
    border-collapse: separate;
    font-size: 14px;
    line-height: 1.45;
    font-variant-numeric: tabular-nums;
  }

  .valuation-group--industry table {
    min-width: max(3260px, 120%);
  }

  .industry-column {
    width: 112px;
  }

  .valuation-metric + .industry-column {
    border-left: 1px solid #dce6ef;
  }

  th,
  td {
    padding: 9px 12px;
    border-top: 1px solid #e3ebf3;
    text-align: center;
    white-space: nowrap;
  }

  thead th {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #edf3f8;
    color: #354d68;
  }

  .valuation-metric {
    border-left: 1px solid #dce6ef;
  }

  thead .valuation-metric:nth-child(even) {
    background: #e7eff6;
  }

  .name-column {
    z-index: 3;
    left: 0;
    width: 162px;
  }

  .metric-column {
    width: 72px;
  }

  .primary-column {
    width: 260px;
  }

  .tier-column {
    width: 100px;
  }

  tr > th:first-child {
    padding-left: 12px;
    text-align: left;
  }

  tbody th {
    position: sticky;
    z-index: 2;
    left: 0;
    background: var(--strategy-surface, #fff);
    box-shadow: 1px 0 #e3ebf3;
    font-size: 15px;
  }

  .unavailable {
    color: #596f87;
  }

  .selected,
  tbody tr.selected:hover,
  tbody tr.selected th {
    background: #f0f5ff;
  }

  tbody tr:hover,
  tbody tr:hover th {
    background: #f6f9fc;
  }

  tbody tr.selected:hover th {
    background: #f0f5ff;
  }

  button {
    padding: 0;
    border: 0;
    border-radius: 3px;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  button:hover,
  button:focus-visible,
  button[data-direction] {
    background: #e6efff;
    color: #1c54a3;
  }

  button[data-direction]::after {
    content: ' ▲';
    font-size: 7px;
  }

  button[data-direction='desc']::after {
    content: ' ▼';
  }

  .chart-link:hover {
    text-decoration: underline;
  }

  .index-code,
  .metric-label,
  .metric-value small {
    color: #596f87;
    font-size: 12px;
    font-weight: 400;
  }

  .index-code,
  .metric-label {
    display: block;
  }

  .metric-value {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 5px;
  }

  .metric-value button {
    font-weight: 600;
  }

  .rank-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 3px;
    font-size: 12px;
  }

  .rank-grid > * + * {
    border-left: 1px solid #dbe4ea;
  }

  .rank-grid sup {
    color: #596f87;
  }

  .rank-low {
    color: #23734f;
  }

  .rank-high {
    color: #a33329;
  }

  .metric-badge,
  .tier {
    display: inline-block;
    font-size: 12px;
    font-weight: 600;
  }

  .metric-badge {
    min-width: 28px;
    padding: 1px 4px;
    border-radius: 4px;
    background: #326da8;
    color: #fff;
  }

  .metric-badge[data-metric='pb'] {
    background: #7550a3;
  }

  .metric-badge[data-metric='ps'] {
    background: #107b7c;
  }

  .metric-badge[data-metric='dividend'] {
    background: #955e0d;
  }

  .tier {
    min-width: 48px;
    padding: 3px 8px;
    border-radius: 999px;
  }

  .tier[data-tier='0'] {
    background: #d4eedf;
    color: #17613e;
  }

  .tier[data-tier='1'] {
    background: #e5f3ea;
    color: #22674c;
  }

  .tier[data-tier='2'] {
    background: #fbefd8;
    color: #81530c;
  }

  .tier[data-tier='3'] {
    background: #fbe3e0;
    color: #a33329;
  }

  .primary-reading {
    display: grid;
    grid-template-columns: 8ch minmax(86px, 132px) 7ch;
    align-items: center;
    justify-content: center;
    text-align: right;
    gap: 8px;
  }

  .primary-reading strong {
    font-size: 16px;
  }

  .percentile-track {
    position: relative;
    height: 10px;
    border-radius: 2px;
    background: linear-gradient(
      to right,
      #b9e5cb 20%,
      #d4eadc 20% 50%,
      #f4dca7 50% 80%,
      #f4c5bf 80%
    );
  }

  .percentile-track.is-empty {
    background: #edf3f8;
  }

  .percentile-track i {
    position: absolute;
    top: -3px;
    bottom: -3px;
    width: 2px;
    transform: translateX(-50%);
    background: #1d3950;
    box-shadow: 0 0 0 1px #fff;
  }

  .percentile-track i::before {
    content: '';
    position: absolute;
    top: -1px;
    left: 50%;
    transform: translateX(-50%);
    border: 3px solid transparent;
    border-top-color: #1d3950;
  }
</style>
