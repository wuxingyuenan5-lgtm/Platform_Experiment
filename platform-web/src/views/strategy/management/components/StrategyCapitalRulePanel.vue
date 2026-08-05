<template>
  <section class="rule-panel" data-testid="strategy-capital-rule-panel">
    <header>
      <h2>{{ panel.title }}</h2>
      <span>安全边界</span>
    </header>
    <ol>
      <li v-for="rule in panel.rules" :key="rule">{{ rule }}</li>
    </ol>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    panel: { title: string; rules: string[] };
  }>();
</script>

<style scoped lang="less">
  .rule-panel {
    display: grid;
    gap: 14px;
    padding: 18px;
    border: 1px solid #eadcae;
    border-radius: var(--strategy-radius-card, 14px);
    background: #fffaf0;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  h2 {
    margin: 0;
    color: #5f4a17;
    font-size: 17px;
  }

  header span {
    color: #8a6a22;
    font-size: 12px;
  }

  ol {
    display: grid;
    gap: 8px;
    margin: 0;
    padding-left: 22px;
    color: #6f5a29;
    line-height: 1.6;
  }
</style>
