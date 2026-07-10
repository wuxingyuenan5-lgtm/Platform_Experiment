<template>
  <article class="records-card">
    <header class="records-head">
      <h3>订单信息</h3>
      <button type="button" class="refresh-btn">刷新</button>
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

    <div class="records-table">
      <table>
        <thead>
          <tr>
            <th v-for="column in currentSection.columns" :key="column.key">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in currentSection.rows" :key="rowIndex">
            <td v-for="column in currentSection.columns" :key="column.key">
              <span :class="cellClass(row[column.key] || '--')">{{ row[column.key] || '--' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </article>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
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

  function cellClass(value: string) {
    if (!value || value === '--') return 'cell-muted';
    if (value.startsWith('-')) return 'cell-negative';
    if (
      value === '开启自动止盈' ||
      value === '成功' ||
      value === 'Filled' ||
      value === '全部成交' ||
      value === '已完成' ||
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
  }

  .records-head h3 {
    margin: 0;
    color: #172947;
    font-size: 18px;
    font-weight: 700;
  }

  .refresh-btn {
    height: 32px;
    padding: 0 14px;
    border: 1px solid #e4e8ef;
    border-radius: 8px;
    background: #fff;
    color: #667788;
    font-size: 13px;
    cursor: pointer;
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
    height: 40px;
    padding: 0 16px;
    border: none;
    background: transparent;
    color: #6b7280;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
  }

  .records-tabs .is-active {
    color: #d97706;
    font-weight: 700;
  }

  .records-tabs .is-active::after {
    content: '';
    position: absolute;
    right: 10px;
    bottom: 0;
    left: 10px;
    height: 2px;
    border-radius: 999px;
    background: #f59e0b;
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
    color: #8a97ab;
    font-size: 12px;
    font-weight: 600;
  }

  .records-table td {
    color: #30435f;
    font-size: 13px;
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
</style>
