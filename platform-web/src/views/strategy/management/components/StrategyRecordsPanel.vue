<template>
  <section class="records-panel" data-testid="strategy-records-panel">
    <header>
      <div>
        <span>订单信息</span>
        <h2>持仓与订单记录</h2>
      </div>
      <em>只读</em>
    </header>

    <nav aria-label="策略记录类型">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: tab.key === activeTab }"
        @click="$emit('update:activeTab', tab.key)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="column in table.columns" :key="column.key">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, index) in table.rows" :key="index">
            <td v-for="column in table.columns" :key="column.key">
              {{ row[column.key] || '--' }}
            </td>
          </tr>
          <tr v-if="!table.rows.length">
            <td :colspan="table.columns.length">暂无可信记录</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { StrategyTableSection } from '@/data/sample/strategy';

  const props = defineProps<{
    tabs: Array<{ key: string; label: string }>;
    tables: Record<string, StrategyTableSection>;
    activeTab: string;
  }>();

  defineEmits<{
    (event: 'update:activeTab', value: string): void;
  }>();

  const table = computed<StrategyTableSection>(() =>
    props.tables[props.activeTab] || { columns: [], rows: [] },
  );
</script>

<style scoped lang="less">
  .records-panel {
    display: grid;
    gap: 14px;
    padding: 18px;
    border: 1px solid var(--strategy-border, #e4e9ef);
    border-radius: var(--strategy-radius-card, 14px);
    background: var(--strategy-surface, #fff);
  }

  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }

  header span,
  em {
    color: var(--strategy-text-3, #778396);
  }

  h2 {
    margin: 4px 0 0;
    font-size: 18px;
  }

  em {
    font-size: 11px;
    font-style: normal;
  }

  nav {
    display: flex;
    gap: 6px;
  }

  nav button {
    padding: 7px 12px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: #667085;
    cursor: pointer;
  }

  nav button.active {
    background: #eef3f8;
    color: #294a67;
    font-weight: 700;
  }

  .table-wrap {
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 11px 10px;
    border-bottom: 1px solid #edf1f5;
    text-align: left;
    white-space: nowrap;
  }

  th {
    color: #778396;
    font-size: 12px;
  }
</style>
