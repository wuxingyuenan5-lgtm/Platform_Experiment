<template>
  <section class="handbook-demo" :aria-label="heading + ' · Demo'">
    <FinancingChart
      v-if="selected && comparisonViews.length"
      :key="selected.id + period"
      :title="heading + ' · Demo'"
      :rows="dataset.rows"
      :lines="dataset.lines"
      :initial-range="0"
      note="模拟数据"
      allow-table
    >
      <template #toolbar>
        <div class="comparison-controls">
          <label
            >比较变量
            <select v-model="comparisonId" aria-label="外资比较变量">
              <option v-for="view in comparisonViews" :key="view.id" :value="view.id">
                {{ view.title.replace('外资流量与', '') }}
              </option>
            </select>
          </label>
          <label
            >报告期
            <select v-model="period" aria-label="外资比较Demo报告期">
              <option v-for="d in demoPeriods" :key="d">{{ d }}</option>
            </select>
          </label>
        </div>
      </template>
    </FinancingChart>
    <div v-else class="demo-layout demo-layout--inline">
      <ChartExpand v-if="selected" :title="chartTitle">
        <div class="demo-content">
          <header class="analysis-heading">
            <h3>{{ heading }}</h3>
            <span class="demo-badge">模拟数据</span>
            <label
              >报告期
              <select v-model="period" :aria-label="selected.title + 'Demo报告期'">
                <option v-for="d in demoPeriods" :key="d">{{ d }}</option>
              </select>
            </label>
          </header>
          <p class="analysis-definition">{{ selected.definition }}</p>
          <FinancingChart
            v-if="dataset.kind === 'time'"
            :key="selected.id + period"
            :title="chartTitle"
            embedded
            :rows="dataset.rows"
            :lines="dataset.lines"
            :initial-range="0"
            allow-table
          />
          <CapitalBars
            v-else-if="dataset.kind === 'bars'"
            :title="chartTitle"
            :rows="dataset.rows"
            :lines="dataset.lines"
          />

          <article v-else class="demo-table-card">
            <div class="table-toolbar">
              <label>筛选<input v-model="rowSearch" placeholder="证券、行业或机构" /></label
            ></div>
            <p v-if="dataset.kind === 'matrix'" class="matrix-key">
              {{
                selected.recipe === 'rankHistory'
                  ? '深色：前十名 · 浅色：十一至二十五名'
                  : '色块深浅表示权重高低'
              }}
            </p>
            <div
              class="table-scroll"
              role="region"
              :aria-label="selected.title + '示例数据表'"
              tabindex="0"
            >
              <table :class="{ matrix: dataset.kind === 'matrix' }">
                <caption>{{ selected.title }} · {{ period }} · Demo · 模拟数据</caption>
                <thead
                  ><tr
                    ><th v-for="column in dataset.columns" :key="column.key" scope="col">
                      <button
                        :aria-label="'按' + column.label + '排序'"
                        @click="sortBy(column.key)"
                      >
                        {{ column.label }}<small v-if="column.unit">（{{ column.unit }}）</small>
                        <span v-if="sortKey === column.key">{{ descending ? ' ↓' : ' ↑' }}</span>
                      </button>
                    </th></tr
                  ></thead
                >
                <tbody
                  ><tr v-for="r in pageRows" :key="String(r.date)">
                    <td
                      v-for="column in dataset.columns"
                      :key="column.key"
                      :class="{ number: typeof r[column.key] === 'number' }"
                      :style="cellStyle(r[column.key], column)"
                      >{{ format(r[column.key]) }}</td
                    > </tr
                  ><tr v-if="!pageRows.length"
                    ><td :colspan="dataset.columns.length" class="empty">没有匹配记录</td></tr
                  ></tbody
                >
              </table>
            </div>
            <footer class="table-pagination"
              ><span>{{ sortedRows.length }}条</span>
              <button :disabled="page === 1" @click="page--">上一页</button
              ><span>{{ page }} / {{ pages }}</span>
              <button :disabled="page === pages" @click="page++">下一页</button></footer
            >
          </article>
        </div>
      </ChartExpand>
    </div>
  </section>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import FinancingChart from './FinancingChart.vue';
  import CapitalBars from './CapitalBars.vue';
  import ChartExpand from '../../components/ChartExpand.vue';
  import { DEMO_CATALOG } from './capitalHandbookDemoCatalog';
  import { buildCapitalDemo, demoPeriods, type DemoColumn } from './capitalHandbookDemoData';

  const props = defineProps<{ demoId: string; comparisonIds?: readonly string[] }>();
  const comparisonId = ref(props.demoId);
  const comparisonViews = computed(() =>
    DEMO_CATALOG.filter((v) => props.comparisonIds?.includes(v.id)),
  );
  const period = ref(demoPeriods.at(-1)!);
  const rowSearch = ref(''),
    sortKey = ref('');
  const descending = ref(true),
    page = ref(1);
  const selected = computed(() =>
    DEMO_CATALOG.find(
      (v) => v.id === (comparisonViews.value.length ? comparisonId.value : props.demoId),
    ),
  );
  const heading = computed(() =>
    comparisonViews.value.length ? '外资流量与宏观变量' : selected.value?.title,
  );
  const dataset = computed(() =>
    selected.value
      ? buildCapitalDemo(selected.value.id, period.value)
      : { kind: 'table' as const, rows: [], lines: [], columns: [] },
  );
  const chartTitle = computed(() => `${selected.value?.title || ''} · Demo`);
  watch(
    () => [selected.value?.id, period.value],
    () => {
      rowSearch.value = '';
      sortKey.value = '';
      page.value = 1;
    },
  );
  watch(rowSearch, () => {
    page.value = 1;
  });
  function sortBy(key: string) {
    descending.value = sortKey.value === key ? !descending.value : true;
    sortKey.value = key;
    page.value = 1;
  }
  const sortedRows = computed(() => {
    const q = rowSearch.value.trim().toLowerCase();
    const rows = dataset.value.rows.filter(
      (r) =>
        !q ||
        Object.values(r).some((v) =>
          String(v ?? '')
            .toLowerCase()
            .includes(q),
        ),
    );
    if (!sortKey.value) return rows;
    return [...rows].sort((a, b) => {
      const x = a[sortKey.value],
        y = b[sortKey.value];
      if (x == null) return y == null ? 0 : 1;
      if (y == null) return -1;
      const value =
        typeof x === 'number' && typeof y === 'number'
          ? x - y
          : String(x).localeCompare(String(y), 'zh-CN');
      return value * (descending.value ? -1 : 1);
    });
  });
  const pages = computed(() => Math.max(1, Math.ceil(sortedRows.value.length / 25)));
  const pageRows = computed(() => sortedRows.value.slice((page.value - 1) * 25, page.value * 25));
  const format = (value: unknown) =>
    value == null
      ? '—'
      : typeof value === 'number'
      ? value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
      : String(value);
  function cellStyle(value: unknown, column: DemoColumn) {
    if (!column.heat || typeof value !== 'number') return {};
    if (selected.value?.recipe === 'rankHistory')
      return {
        background: `rgba(37, 99, 235, ${value <= 10 ? 0.21 : 0.06})`,
        color: 'var(--strategy-text)',
      };
    const strength = Math.min(Math.abs(value) / (column.unit === '百分点' ? 5 : 30), 1);
    return {
      background: `rgba(${value < 0 ? '13,148,136' : '202,99,65'},${0.04 + strength * 0.17})`,
      color: 'var(--strategy-text)',
    };
  }
</script>

<style scoped lang="less">
  .comparison-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 12px;
    font-size: 12px;
  }

  .handbook-demo {
    min-width: 0;
    color: var(--strategy-text);
  }

  .demo-heading,
  .analysis-heading,
  .table-toolbar,
  .table-pagination {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .demo-heading {
    margin: 18px 0;
  }

  h2,
  h3,
  p {
    margin: 0;
  }

  h2 {
    display: inline;
    margin-left: 10px;
    font-size: 19px;
  }

  h3 {
    margin-top: 5px;
    font-size: 17px;
  }

  .demo-heading p,
  .analysis-definition,
  .matrix-key {
    margin-top: 9px;
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.7;
  }

  .demo-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 5px;
    background: #fff4df;
    color: #875310;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
  }

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }

  input,
  select {
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
    color: var(--strategy-text);
  }

  button {
    color: inherit;
    cursor: pointer;
  }

  button:focus-visible,
  input:focus-visible,
  select:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  .demo-categories {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    margin-bottom: 16px;
  }

  .demo-categories button,
  .table-pagination button {
    padding: 7px 11px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
  }

  .demo-categories button[aria-pressed='true'] {
    border-color: #2563eb;
    background: rgb(37 99 235 / 6%);
    color: #2563eb;
  }

  .demo-layout {
    display: grid;
    grid-template-columns: 252px minmax(0, 1fr);
    gap: 20px;
    align-items: start;
  }

  .demo-directory {
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  .catalog-search {
    display: grid;
    gap: 7px;
  }

  .directory-count {
    padding: 14px 2px 8px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .directory-items {
    display: grid;
    max-height: 640px;
    overflow-y: auto;
    gap: 5px;
  }

  .directory-items button {
    padding: 10px;
    border: 1px solid transparent;
    border-radius: 7px;
    background: transparent;
    font-size: 12px;
    text-align: left;
  }

  .directory-items small {
    display: block;
    margin-top: 5px;
    color: var(--strategy-text-3);
    font-size: 10px;
  }

  .directory-items button[aria-pressed='true'] {
    border-color: rgb(37 99 235 / 25%);
    background: rgb(37 99 235 / 7%);
    color: #2563eb;
  }

  .demo-content {
    min-width: 0;
  }

  .analysis-heading > div > span {
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  .analysis-definition {
    margin: 10px 0 16px;
  }

  .demo-table-card {
    min-width: 0;
    padding: 17px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  .table-toolbar {
    margin-bottom: 12px;
    padding-right: 25px;
    font-size: 13px;
  }

  .table-toolbar input {
    width: 180px;
  }

  .table-scroll {
    max-height: 650px;
    overflow: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 7px;
  }

  table {
    width: 100%;
    border-spacing: 0;
    border-collapse: separate;
    font-size: 12px;
    white-space: nowrap;
  }

  caption {
    padding: 10px;
    color: var(--strategy-text-3);
    font-size: 11px;
    text-align: left;
  }

  th,
  td {
    padding: 11px 12px;
    border-bottom: 1px solid var(--strategy-border);
    text-align: left;
  }

  th {
    position: sticky;
    z-index: 2;
    top: 0;
    background: var(--strategy-surface-2);
    font-weight: 500;
  }

  th button {
    padding: 0;
    border: 0;
    background: transparent;
    font-size: inherit;
  }

  th small {
    font-size: 10px;
    font-weight: normal;
  }

  th:first-child,
  td:first-child {
    position: sticky;
    z-index: 1;
    left: 0;
    background: var(--strategy-surface);
  }

  th:first-child {
    z-index: 3;
    background: var(--strategy-surface-2);
  }

  .number {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .matrix td {
    border-right: 1px solid var(--strategy-border);
  }

  .matrix-key {
    margin: 0 0 12px;
  }

  .table-pagination {
    justify-content: flex-end;
    margin-top: 12px;
    font-size: 11px;
  }

  button:disabled {
    opacity: 0.4;
    cursor: default;
  }

  .empty {
    padding: 25px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  @media (max-width: 1100px) {
    .demo-layout {
      grid-template-columns: 210px minmax(0, 1fr);
      gap: 12px;
    }
  }

  @media (max-width: 760px) {
    .demo-layout {
      grid-template-columns: minmax(0, 1fr);
    }

    .directory-items {
      max-height: 180px;
    }

    .demo-table-card {
      padding: 10px;
    }

    .table-toolbar {
      padding-right: 22px;
    }

    .table-toolbar label {
      width: 100%;
    }

    .table-toolbar input {
      flex: 1;
      width: 0;
    }

    .demo-heading h2 {
      font-size: 16px;
    }
  }

  .demo-layout--inline {
    grid-template-columns: minmax(0, 1fr);
    margin-top: 24px;
  }
</style>
