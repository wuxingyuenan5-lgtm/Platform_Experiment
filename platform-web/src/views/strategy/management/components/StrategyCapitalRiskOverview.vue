<template>
  <article v-if="overview.rows.length" class="capital-risk-overview">
    <header class="capital-risk-overview__header">
      <h3>{{ overview.title }}</h3>
    </header>

    <div class="capital-risk-overview__table">
      <table>
        <thead>
          <tr>
            <th>产品/账户</th>
            <th>类型</th>
            <th>风险等级</th>
            <th>风险因子</th>
            <th>最初数据</th>
            <th>最新数据</th>
            <th>最新时间</th>
            <th>次数</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in overview.rows" :key="`${item.product}-${item.factor}`">
            <td class="is-strong">{{ item.product }}</td>
            <td>{{ item.type }}</td>
            <td>
              <span :class="['risk-level', item.tone ? `is-${item.tone}` : '']">
                {{ item.level }}
              </span>
            </td>
            <td>{{ item.factor }}</td>
            <td>{{ item.firstValue }}</td>
            <td>{{ item.latestValue }}</td>
            <td>{{ item.latestTime }}</td>
            <td>{{ item.count }}</td>
            <td>
              <span class="risk-status">{{ item.status }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </article>
</template>

<script setup lang="ts">
  import type { StrategyCapitalRiskOverview } from '../types';

  defineProps<{
    overview: StrategyCapitalRiskOverview;
  }>();
</script>

<style scoped lang="less">
  .capital-risk-overview {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .capital-risk-overview__header {
    display: flex;
    align-items: center;
    justify-content: space-between;

    h3 {
      margin: 0;
      color: var(--strategy-text-1);
      font-size: var(--strategy-font-card-title);
      font-weight: 800;
    }
  }

  .capital-risk-overview__table {
    overflow-x: auto;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);

    table {
      width: 100%;
      min-width: 1080px;
      border-collapse: collapse;
      color: var(--strategy-text-1);
      font-size: var(--strategy-font-base);
    }

    th,
    td {
      padding: 14px 16px;
      border-bottom: 1px solid var(--strategy-border-soft);
      text-align: left;
      white-space: nowrap;
    }

    th {
      background: var(--strategy-table-head-bg);
      color: var(--strategy-text-3);
      font-weight: 700;
    }

    tbody tr:last-child td {
      border-bottom: 0;
    }

    .is-strong {
      font-weight: 700;
    }
  }

  .risk-level {
    color: var(--strategy-text-1);
    font-weight: 700;

    &.is-positive {
      color: var(--strategy-success);
    }

    &.is-negative {
      color: var(--strategy-danger);
    }
  }

  .risk-status {
    color: var(--strategy-success);
    font-weight: 700;
  }
</style>
