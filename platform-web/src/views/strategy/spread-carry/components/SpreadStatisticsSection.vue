<template>
  <section class="spread-statistics" data-testid="spread-statistics-section">
    <article>
      <header><h2>损益拆分</h2><span>只读</span></header>
      <dl><div v-for="item in decomposition" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></div></dl>
    </article>
    <article>
      <header><h2>研究场景</h2><span>不可执行</span></header>
      <div class="scenario-grid">
        <section v-for="item in scenarios" :key="item.title"><strong>{{ item.title }}</strong><p>{{ item.body }}</p><small>{{ item.result }}</small></section>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    decomposition: Array<{ label: string; value: string }>;
    scenarios: Array<{ title: string; body: string; result: string }>;
  }>();
</script>

<style scoped lang="less">
  .spread-statistics { display: grid; grid-template-columns: .8fr 1.4fr; gap: 12px; }
  article { display: grid; gap: 14px; padding: 17px; border: 1px solid #e1e7ef; border-radius: 13px; background: #fff; }
  header { display: flex; align-items: center; justify-content: space-between; }
  h2 { margin: 0; font-size: 17px; }
  header span { color: #846116; font-size: 11px; }
  dl { display: grid; gap: 10px; margin: 0; }
  dl div { display: flex; justify-content: space-between; gap: 12px; padding-bottom: 9px; border-bottom: 1px solid #edf1f5; }
  dt { color: #6d788a; }
  dd { margin: 0; font-weight: 700; text-align: right; }
  .scenario-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
  .scenario-grid section { padding: 13px; border: 1px solid #e5eaf1; border-radius: 10px; background: #fafbfd; }
  p { color: #667085; line-height: 1.6; }
  small { color: #3c649d; font-weight: 700; }
  @media (max-width: 900px) { .spread-statistics, .scenario-grid { grid-template-columns: 1fr; } }
</style>
