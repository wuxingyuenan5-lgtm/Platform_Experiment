<template>
  <component :is="expanded ? 'section' : 'details'"
    ><component :is="expanded ? 'h3' : 'summary'" :class="{ 'disclosure-title': expanded }"
      >科技细分行业 · 已有历史分位</component
    ><div class="table-scroll"
      ><table
        ><thead
          ><tr
            ><th>行业</th><th>成交占比</th><th>占比分位</th><th>换手率</th><th>换手分位</th
            ><th>样本</th><th>观测日</th></tr
          ></thead
        ><tbody
          ><tr v-for="row in rows" :key="row.name"
            ><th>{{ row.name }}</th
            ><td>{{ format(row.sharePct, '%') }}</td
            ><td>{{ format(row.shareRank, '%') }}</td
            ><td>{{ format(row.turnover, '%') }}</td
            ><td>{{ format(row.turnoverRank, '%') }}</td
            ><td>{{ row.count }}日</td><td>{{ row.date }}</td></tr
          ></tbody
        ></table
      ></div
    ></component
  >
</template>
<script setup lang="ts">
  import type { EquityObservatory, EquityValue } from '@/api/equityObservatory';

  defineProps<{ rows: NonNullable<EquityObservatory['crowding']>; expanded?: boolean }>();
  const format = (value: EquityValue, suffix: string) =>
    value == null || value === '' || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toFixed(2) + suffix;
</script>
<style scoped>
  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  th,
  td {
    padding: 8px 10px;
    border-bottom: 1px solid #e5edf5;
    text-align: center;
  }

  thead {
    background: #f1f6fa;
  }

  tr > :first-child {
    text-align: left;
  }

  h3,
  summary {
    color: #25374d;
    font-size: 14px;
    font-weight: 600;
  }
</style>
