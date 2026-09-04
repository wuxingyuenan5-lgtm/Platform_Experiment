<template>
  <section class="content-panel" data-testid="macro-calendar-panel">
    <header>
      <h2>宏观日历</h2>
      <button
        type="button"
        :aria-expanded="expanded"
        aria-controls="macro-calendar-content"
        @click="expanded = !expanded"
      >
        {{ expanded ? '收起' : '展开' }}
        <span aria-hidden="true">{{ expanded ? '⌃' : '⌄' }}</span>
      </button>
    </header>
    <div v-show="expanded" id="macro-calendar-content">
      <TradingViewEconomicCalendarPanel />
    </div>
  </section>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import TradingViewEconomicCalendarPanel from '../tradingTools/components/TradingViewEconomicCalendarPanel.vue';

  const expanded = ref(false);
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

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  button {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 34px;
    padding: 0 14px;
    border: 1px solid #d8e2ee;
    border-radius: 999px;
    background: #fff;
    color: #294a67;
    font-weight: 700;
    cursor: pointer;
  }
</style>
