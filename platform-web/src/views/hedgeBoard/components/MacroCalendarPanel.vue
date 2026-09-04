<template>
  <section class="content-panel" data-testid="macro-calendar-panel">
    <header><h2>宏观日历</h2></header>
    <TradingViewEconomicCalendarPanel />
  </section>
</template>

<script setup lang="ts">
  import TradingViewEconomicCalendarPanel from '../tradingTools/components/TradingViewEconomicCalendarPanel.vue';
</script>

<style scoped lang="less">
  .content-panel {
    display: grid;
    gap: 16px;
    margin-bottom: 14px;
    padding: 18px;
    border: 1px solid #dbe4ed;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 1px 3px rgb(15 23 42 / 6%);
  }

  h2 {
    margin: 0;
    color: #17212f;
    font-size: 20px;
    font-weight: 800;
  }
</style>
