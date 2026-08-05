<template>
  <section class="funding-order-panel" data-testid="funding-order-panel">
    <header><div><span>执行面板</span><h2>{{ data.strategyLabel }}</h2></div><em>Live Write 关闭</em></header>
    <div class="order-layout">
      <form @submit.prevent>
        <label v-for="field in data.fields" :key="field.label">
          {{ field.label }}
          <input :value="field.value" disabled />
        </label>
        <button type="submit" disabled data-write-action="true">提交组合订单</button>
        <p>样例状态不可下单；ACK 不等于 Fill，结果未知时必须查询确认。</p>
      </form>
      <div class="table-wrap">
        <table>
          <thead><tr><th>腿</th><th>场所</th><th>方向</th><th>数量</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="leg in data.legs" :key="leg.leg">
              <td>{{ leg.leg }}</td><td>{{ leg.venue }}</td><td>{{ leg.side }}</td><td>{{ leg.quantity }}</td><td>{{ leg.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    data: {
      strategyLabel: string;
      fields: Array<{ label: string; value: string }>;
      legs: Array<{ leg: string; venue: string; side: string; quantity: string; status: string }>;
    };
  }>();
</script>

<style scoped lang="less">
  .funding-order-panel { display: grid; gap: 16px; padding: 18px; border: 1px solid #e1e7ef; border-radius: 14px; background: #fff; }
  header { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
  header div { display: grid; gap: 4px; }
  header span { color: #738094; font-size: 11px; }
  h2 { margin: 0; font-size: 19px; }
  em { color: #9a6700; font-size: 12px; font-style: normal; }
  .order-layout { display: grid; grid-template-columns: minmax(250px, .7fr) minmax(0, 1.5fr); gap: 16px; }
  form { display: grid; gap: 11px; }
  label { display: grid; gap: 5px; color: #667085; }
  input { height: 38px; padding: 0 10px; border: 1px solid #dce3eb; border-radius: 8px; background: #f7f9fb; }
  button { height: 38px; border: 0; border-radius: 8px; background: #e2e7ed; color: #76808e; }
  p { margin: 0; color: #7b652d; font-size: 12px; line-height: 1.6; }
  .table-wrap { overflow: auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 11px; border-bottom: 1px solid #edf1f5; text-align: left; white-space: nowrap; }
  th { color: #788396; font-size: 12px; }
  @media (max-width: 800px) { .order-layout { grid-template-columns: 1fr; } }
</style>
