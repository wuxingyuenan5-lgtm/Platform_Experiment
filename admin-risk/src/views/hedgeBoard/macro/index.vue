<template>
  <div class="macro-board-page">
    <LegacyHedgeBoard />
    <MacroExpectationPanel />
  </div>
</template>

<script setup lang="ts">
  import LegacyHedgeBoard from '../index.vue';
  import MacroExpectationPanel from './MacroExpectationPanel.vue';
</script>

<style scoped lang="less">
  .macro-board-page { min-width: 0; }
</style>
