<template>
  <div class="macro-board-page">
    <LegacyHedgeBoard />
  </div>
</template>

<script setup lang="ts">
  import LegacyHedgeBoard from '../index.vue';
</script>

<style scoped lang="less">
  .macro-board-page {
    min-width: 0;
  }

  .macro-board-page :deep(.strategy-top-toolbar__left) {
    min-width: 0;
    max-width: 100%;
    overflow-x: auto;
  }
</style>
