<template>
  <div class="gold-oi-panel">
    <div role="group" aria-label="黄金持仓市场" class="gold-oi-tabs">
      <button
        v-for="market in markets"
        :key="market.id"
        :aria-pressed="selected === market.id"
        @click="selected = market.id"
        >{{ market.label }}</button
      >
    </div>
    <p class="gold-oi-note">{{ markets.find((market) => market.id === selected)?.definition }}</p>
    <MacroSeriesChart
      :key="selected"
      data-domain="commodity"
      group-id="goldOpenInterest"
      :preferred-series-ids="[selected]"
      unit-label="手"
      :years="5"
    />
  </div>
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

<style scoped>
  .gold-oi-panel {
    padding: 12px;
  }

  .gold-oi-tabs {
    display: flex;
    gap: 8px;
  }

  button {
    padding: 5px 10px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: #fff;
    font-size: 12px;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    background: #edf4ff;
    color: #165dff;
  }

  .gold-oi-note,
  .gold-oi-gap {
    margin: 10px 0;
    color: #64748b;
    font-size: 12px;
  }
</style>
