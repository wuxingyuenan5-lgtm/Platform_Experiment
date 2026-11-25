<template>
  <header class="participation-heading">
    <h2>宽基参与度与价格位置</h2>
  </header>
  <div class="participation-table" role="region" aria-label="宽基参与度与价格位置" tabindex="0">
    <table>
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            scope="col"
            :aria-sort="direction(column.key)"
          >
            <button type="button" @click="sortBy(column.key)">
              {{ column.label
              }}<span aria-hidden="true">{{
                direction(column.key) === 'ascending'
                  ? ' ↑'
                  : direction(column.key) === 'descending'
                  ? ' ↓'
                  : ''
              }}</span>
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in sortedRows" :key="row.key">
          <th scope="row">{{ row.values.name }}</th>
          <td v-for="column in columns.slice(1)" :key="column.key">
            {{ cell(row.values[column.key], column) }}
          </td>
        </tr>
        <tr v-if="!sortedRows.length"><td :colspan="columns.length">暂无宽基观察数据</td></tr>
      </tbody>
    </table>
  </div>
  <p v-if="data.sectionStatus?.market === 'stale'" class="observation-note"
    >市场观察待更新，当前显示最近有效数据。</p
  >
  <details class="observation-note">
    <summary>查看口径</summary>
    <p
      >中证官方成分与同日行情匹配；换手率取有效成分中位数。仅完整覆盖的收盘观测进入历史分位，不使用当前成分回填历史。</p
    >
    <p>均线偏离是价格过热的观察项，不替代成分股换手率或市场广度；高拥挤不等于立即下跌。</p>
  </details>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { EquityObservatory, EquityValue } from '@/api/equityObservatory';
  import { observationGroups } from '../../components/indexValuationSnapshot';

  const props = defineProps<{ data: EquityObservatory }>();
  type Column = { key: string; label: string; unit?: '%' | '日' };
  const columns: Column[] = [
    { key: 'name', label: '指数' },
    { key: 'advancing', label: '上涨占比', unit: '%' },
    { key: 'rank', label: '换手分位', unit: '%' },
    { key: 'top20', label: '前20股成交占比', unit: '%' },
    { key: 'deviation60', label: '距60日均线', unit: '%' },
    { key: 'drawdown252', label: '距252日高点', unit: '%' },
    { key: 'coverage', label: '成分覆盖' },
    { key: 'turnover', label: '换手率中位数', unit: '%' },
    { key: 'sampleDays', label: '历史样本', unit: '日' },
    { key: 'deviation20', label: '距20日均线', unit: '%' },
    { key: 'deviation200', label: '距200日均线', unit: '%' },
    { key: 'membershipDate', label: '成分日期' },
    { key: 'tradeDate', label: '成交观察日' },
    { key: 'priceDate', label: '价格观察日' },
  ];
  const activeSort = ref<{ key: string; direction: 'ascending' | 'descending' }>();
  const normalizeCode = (code?: string) => code?.split('.')[0].toUpperCase();
  const preferredOrder = new Map(
    observationGroups[0].rows.map((row, i) => [normalizeCode(row[1]), i]),
  );
  const numeric = (value: EquityValue | undefined) =>
    value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);

  const rows = computed(() => {
    const trading = new Map(
      (props.data.indexCrowding || []).map((row) => [normalizeCode(row.code) || row.name, row]),
    );
    const prices = new Map(
      (props.data.indices || []).map((row) => [normalizeCode(row.code) || row.name, row]),
    );
    return [...new Set([...trading.keys(), ...prices.keys()])]
      .sort(
        (a, b) => (preferredOrder.get(a) ?? Infinity) - (preferredOrder.get(b) ?? Infinity) || 0,
      )
      .map((key) => {
        const trade = trading.get(key);
        const price = prices.get(key);
        const values: Record<string, EquityValue | undefined> = {
          name: trade?.name || price?.name || key,
          advancing: trade?.advancingPct,
          rank: trade?.turnoverRank,
          top20: trade?.top20AmountPct,
          deviation60: price?.deviation60,
          drawdown252: price?.drawdown252,
          coverage: trade ? trade.count + '/' + trade.expected : null,
          turnover: trade?.medianTurnover,
          sampleDays: trade?.sampleCount,
          deviation20: price?.deviation20,
          deviation200: price?.deviation200,
          membershipDate: trade?.membershipDate,
          tradeDate: trade?.date,
          priceDate: price?.date,
        };
        return { key, values, coverage: trade?.expected ? trade.count / trade.expected : null };
      });
  });

  const sortedRows = computed(() => {
    const sort = activeSort.value;
    const column = columns.find((item) => item.key === sort?.key);
    if (!sort || !column) return rows.value;
    const compareValue = (row: (typeof rows.value)[number]) => {
      if (column.key === 'coverage') return row.coverage;
      const value = row.values[column.key];
      return column.unit ? numeric(value) : value ?? null;
    };
    return [...rows.value].sort((a, b) => {
      const aa = compareValue(a);
      const bb = compareValue(b);
      if (aa == null) return bb == null ? 0 : 1;
      if (bb == null) return -1;
      const comparison =
        typeof aa === 'number' && typeof bb === 'number'
          ? aa - bb
          : String(aa).localeCompare(String(bb), 'zh-CN');
      return sort.direction === 'ascending' ? comparison : -comparison;
    });
  });

  function sortBy(key: string) {
    const sort = activeSort.value;
    if (sort?.key !== key) activeSort.value = { key, direction: 'ascending' };
    else if (sort.direction === 'ascending') activeSort.value = { key, direction: 'descending' };
    else activeSort.value = undefined;
  }

  const direction = (key: string) =>
    activeSort.value?.key === key ? activeSort.value.direction : undefined;
  function cell(value: EquityValue | undefined, column: Column) {
    if (!column.unit) return value == null || value === '' ? '—' : value;
    const number = numeric(value);
    return number == null ? '—' : number.toFixed(column.unit === '%' ? 2 : 0) + column.unit;
  }
</script>
<style scoped>
  .participation-heading {
    margin-bottom: 8px;
  }

  .participation-table tr > :first-child {
    position: sticky;
    left: 0;
    background: #fff;
  }

  .participation-table thead tr > :first-child {
    background: #edf4f9;
  }

  .participation-heading h2 {
    margin: 0;
    color: #172d46;
    font-size: 16px;
  }

  button {
    color: inherit;
    cursor: pointer;
  }

  .participation-table {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 6px 8px;
    border-bottom: 1px solid #e5edf5;
    text-align: center;
  }

  tr > :first-child {
    text-align: left;
  }

  thead {
    background: #edf4f9;
  }

  thead button {
    padding: 3px 0;
    border: 0;
    background: transparent;
    font-weight: 650;
  }

  .observation-note {
    margin: 8px 0 0;
    color: #536980;
    font-size: 12px;
  }

  summary {
    cursor: pointer;
  }
</style>
