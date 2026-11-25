<script setup lang="ts">
  import { ref } from 'vue';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const view = ref('composition');
</script>
<template>
  <div class="stablecoin-panel">
    <MacroSeriesChart
      :key="view"
      data-domain="crypto"
      :group-id="view === 'total' ? 'stablecoins' : 'stablecoinComposition'"
      :years="10"
    >
      <template #controls>
        <div class="stablecoin-panel__controls" role="group" aria-label="稳定币市值视图">
          <button
            type="button"
            :aria-pressed="view === 'composition'"
            @click="view = 'composition'"
          >
            主要 8 种稳定币
          </button>
          <button type="button" :aria-pressed="view === 'total'" @click="view = 'total'">
            总市值
          </button>
        </div>
      </template>
    </MacroSeriesChart>
  </div>
</template>

<style scoped lang="less">
  .stablecoin-panel__controls {
    display: flex;
    gap: 8px;
    margin: 0;
  }

  button {
    padding: 5px 10px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: #fff;
    color: var(--hedge-cool-text, #18313c);
    font: inherit;
    font-size: 12px;
    line-height: 18px;
    cursor: pointer;
  }

  button[aria-pressed='true'],
  button:hover {
    border-color: rgb(22 93 255 / 28%);
    background: rgb(22 93 255 / 6%);
    color: #165dff;
  }

  button:focus-visible {
    outline: 2px solid #477bc2;
    outline-offset: 3px;
  }
</style>
