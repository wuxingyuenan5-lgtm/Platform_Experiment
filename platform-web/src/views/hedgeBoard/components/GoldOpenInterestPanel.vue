<template>
  <MacroSeriesChart
    :key="selected"
    data-domain="commodity"
    group-id="goldOpenInterest"
    :preferred-series-ids="[selected]"
    unit-label="手"
    :years="5"
  >
    <template #controls>
      <button
        v-for="market in markets"
        :key="market.id"
        :aria-pressed="selected === market.id"
        type="button"
        :title="market.definition"
        @click="selected = market.id"
        >{{ market.label }}</button
      >
    </template>
  </MacroSeriesChart>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const markets = [
    {
      id: 'comex_gold_open_interest',
      label: 'COMEX GC',
      definition: 'CFTC 周度期货持仓 · 每手 100 金衡盎司 · 不含期权及其他黄金合约',
    },
    {
      id: 'shfe_gold_open_interest',
      label: '上期所 AU',
      definition: '上期所日度期货持仓 · 每手 1000 克 · 全部交割月合计',
    },
  ];
  const selected = ref('comex_gold_open_interest');
</script>
