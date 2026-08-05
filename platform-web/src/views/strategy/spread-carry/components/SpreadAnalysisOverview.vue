<template>
  <section class="spread-analysis-overview" data-testid="spread-analysis-overview">
    <article v-for="item in items" :key="item.label">
      <span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.note }}</small>
    </article>
  </section>
</template>

<script setup lang="ts">
  defineProps<{ items: Array<{ label: string; value: string; note: string }> }>();
</script>

<style scoped lang="less">
  .spread-analysis-overview { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
  article { display: grid; gap: 5px; padding: 15px; border: 1px solid #e1e7ef; border-radius: 13px; background: #fff; }
  span, small { color: #6c778a; }
  strong { font-size: 22px; }
  @media (max-width: 900px) { .spread-analysis-overview { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 520px) { .spread-analysis-overview { grid-template-columns: 1fr; } }
</style>
