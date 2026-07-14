<template>
  <article class="records-card">
    <header class="records-head">
      <div>
        <h3>订单信息</h3>
      </div>
      <div class="records-head__meta">
        <span class="records-total">总数 {{ filteredRows.length }}</span>
        <button type="button" class="refresh-btn" @click="resetFilters">重置筛选</button>
      </div>
    </header>

    <div class="records-tabs">
      <button
        v-for="item in tabs"
        :key="item.key"
        type="button"
        :class="{ 'is-active': item.key === activeTab }"
        @click="$emit('update:activeTab', item.key)"
      >
        {{ item.label }}
      </button>
    </div>

    <section class="records-filters">
      <label class="records-filter">
        <span>开始日期</span>
        <input v-model="startDate" type="date" />
      </label>

      <label class="records-filter">
        <span>结束日期</span>
        <input v-model="endDate" type="date" />
      </label>

      <label class="records-filter" v-if="statusOptions.length">
        <span>订单状态</span>
        <select v-model="statusFilter">
          <option value="">全部</option>
          <option v-for="item in statusOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>

      <label class="records-filter records-filter--compact">
        <span>每页条数</span>
        <select v-model.number="pageSize">
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
      </label>
    </section>

    <div class="records-table">
      <table>
        <thead>
          <tr>
            <th v-for="column in currentColumns" :key="column.key">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in pagedRows" :key="rowIndex">
            <td v-for="column in currentColumns" :key="column.key">
              <span :class="cellClass(row[column.key] || '--')">{{ row[column.key] || '--' }}</span>
            </td>
          </tr>
          <tr v-if="!pagedRows.length">
            <td :colspan="Math.max(currentColumns.length, 1)" class="records-empty">当前筛选条件下暂无数据</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="records-pagination">
      <span>第 {{ currentPage }} / {{ totalPages }} 页</span>
      <div class="records-pagination__actions">
        <button type="button" :disabled="currentPage <= 1" @click="currentPage -= 1">上一页</button>
        <button type="button" :disabled="currentPage >= totalPages" @click="currentPage += 1">下一页</button>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import type { StrategyTableSection, StrategyTableTab } from '../types';

  const props = defineProps<{
    tabs: StrategyTableTab[];
    activeTab: string;
    tables: Record<string, StrategyTableSection>;
    compact?: boolean;
  }>();

  defineEmits<{
    (e: 'update:activeTab', value: string): void;
  }>();

  const currentSection = computed(() => props.tables[props.activeTab] ?? { columns: [], rows: [] });
  const currentColumns = computed(() => currentSection.value.columns);
  const startDate = ref('');
  const endDate = ref('');
  const statusFilter = ref('');
  const pageSize = ref(10);
  const currentPage = ref(1);

  const statusColumnKey = computed(() => currentColumns.value.find((item) => item.key === 'status')?.key || '');

  const statusOptions = computed(() => {
    if (!statusColumnKey.value) return [];
    return Array.from(
      new Set(
        currentSection.value.rows
          .map((row) => row[statusColumnKey.value])
          .filter((value): value is string => Boolean(value && value !== '--')),
      ),
    );
  });

  const filteredRows = computed(() =>
    currentSection.value.rows.filter((row) => {
      const rowDate = parseRowDate(row);
      if (startDate.value && rowDate && rowDate < `${startDate.value} 00:00:00`) return false;
      if (endDate.value && rowDate && rowDate > `${endDate.value} 23:59:59`) return false;
      if (statusFilter.value && statusColumnKey.value && row[statusColumnKey.value] !== statusFilter.value) return false;
      return true;
    }),
  );

  const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize.value)));

  const pagedRows = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value;
    return filteredRows.value.slice(start, start + pageSize.value);
  });

  watch(
    () => [props.activeTab, startDate.value, endDate.value, statusFilter.value, pageSize.value],
    () => {
      currentPage.value = 1;
    },
  );

  watch(totalPages, (value) => {
    if (currentPage.value > value) currentPage.value = value;
  });

  function parseRowDate(row: Record<string, string>) {
    const candidate = row.time || row.date || row.orderTime || row.fillTime || row.executionTime || row.entryTime || '';
    if (!candidate) return '';
    if (/^\d{4}-\d{2}-\d{2}/.test(candidate)) return candidate;
    if (/^\d{2}-\d{2}\s/.test(candidate) || /^\d{2}-\d{2}$/.test(candidate)) return `2026-${candidate}`;
    return '';
  }

  function resetFilters() {
    startDate.value = '';
    endDate.value = '';
    statusFilter.value = '';
    pageSize.value = 10;
    currentPage.value = 1;
  }

  function cellClass(value: string) {
    if (!value || value === '--') return 'cell-muted';
    if (value.startsWith('-') || value === '已失败' || value === '失败' || value === '已撤单') {
      return 'cell-negative';
    }
    if (
      value === '开启自动止盈' ||
      value === '成功' ||
      value === 'Filled' ||
      value === '全部成交' ||
      value === '已完成' ||
      value === '已提交' ||
      value === '查看'
    ) {
      return 'cell-positive';
    }
    return '';
  }
</script>

<style scoped lang="less">
  .records-card {
    border: 1px solid #edf1f6;
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 8px 20px rgba(18, 29, 53, 0.04);
  }

  .records-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 16px 10px;
    gap: 16px;
  }

  .records-head h3 {
    margin: 0;
    color: #172947;
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 0.01em;
  }

  .records-head__meta {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .records-total {
    display: none;
  }

  .refresh-btn {
    height: 32px;
    padding: 0 14px;
    border: 1px solid #e4e8ef;
    border-radius: 8px;
    background: #fff;
    color: #667788;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }

  .records-filters {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    padding: 14px 16px;
    border-bottom: 1px solid #eef2f6;
    background: #fafbfd;
  }

  .records-filter {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 160px;
  }

  .records-filter--compact {
    min-width: 120px;
  }

  .records-filter span {
    color: #8a97ab;
    font-size: 13px;
    font-weight: 700;
  }

  .records-filter input,
  .records-filter select {
    height: 34px;
    padding: 0 10px;
    border: 1px solid #dde5ef;
    border-radius: 8px;
    background: #fff;
    color: #30435f;
    font-size: 14px;
    font-weight: 600;
  }

  .records-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0;
    padding: 0 16px;
    border-bottom: 1px solid #eef2f6;
  }

  .records-tabs button {
    position: relative;
    height: 44px;
    padding: 0 18px;
    border: none;
    background: transparent;
    color: #536174;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .records-tabs .is-active {
    color: #cf4d4d;
    font-weight: 800;
  }

  .records-tabs .is-active::after {
    content: '';
    position: absolute;
    right: 10px;
    bottom: 0;
    left: 10px;
    height: 3px;
    border-radius: 999px;
    background: #d8585f;
  }

  .records-table {
    overflow-x: auto;
  }

  .records-table table {
    width: 100%;
    min-width: 1080px;
    border-collapse: collapse;
  }

  .records-table th,
  .records-table td {
    padding: 12px 14px;
    border-bottom: 1px solid #f0f3f7;
    white-space: nowrap;
    text-align: left;
  }

  .records-table th {
    color: #728097;
    font-size: 13px;
    font-weight: 700;
  }

  .records-table td {
    color: #30435f;
    font-size: 14px;
    font-weight: 600;
  }

  .records-empty {
    color: #8a97ab;
    text-align: center !important;
  }

  .records-pagination {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px 16px;
    color: #667788;
    font-size: 13px;
    font-weight: 600;
  }

  .records-pagination__actions {
    display: flex;
    gap: 8px;
  }

  .records-pagination__actions button {
    height: 32px;
    padding: 0 12px;
    border: 1px solid #e4e8ef;
    border-radius: 8px;
    background: #fff;
    color: #667788;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }

  .records-pagination__actions button:disabled {
    color: #b5bfcd;
    cursor: not-allowed;
  }

  .cell-positive {
    color: #18a058;
    font-weight: 600;
  }

  .cell-negative {
    color: #ef4444;
    font-weight: 600;
  }

  .cell-muted {
    color: #a8b2c3;
  }

  @media (max-width: 860px) {
    .records-head,
    .records-pagination {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
