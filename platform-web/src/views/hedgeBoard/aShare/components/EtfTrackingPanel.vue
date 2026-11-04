<template>
  <section class="etf-workspace" aria-label="ETF跟踪">
    <header
      ><h2>ETF跟踪</h2
      ><nav aria-label="ETF研究分类"
        ><button
          v-for="item in tabs"
          :key="item.id"
          :aria-pressed="tab === item.id"
          @click="tab = item.id"
          >{{ item.label }}</button
        ></nav
      ></header
    >
    <section v-if="tab === 'overview'" aria-label="资金总览">
      <EtfObservationPanel mode="daily" />
      <BroadEtfPanel :refresh-key="refreshKey" />
      <EtfObservationPanel mode="support" />
    </section>
    <EtfObservationPanel v-else-if="tab === 'intraday'" mode="intraday" />
    <EtfSinglePanel v-else :refresh-key="refreshKey" @ready="$emit('ready')" />
  </section>
</template>
<script setup lang="ts">
  import { defineAsyncComponent, onMounted, ref } from 'vue';
  import BroadEtfPanel from './BroadEtfPanel.vue';
  import EtfObservationPanel from './EtfObservationPanel.vue';

  const EtfSinglePanel = defineAsyncComponent(() => import('./EtfSinglePanel.vue'));
  defineProps<{ refreshKey?: number }>();
  const emit = defineEmits<{ ready: [] }>();
  const tabs = [
    { id: 'overview', label: '资金总览' },
    { id: 'intraday', label: '盘中监测' },
    { id: 'single', label: '单只ETF' },
  ] as const;
  const tab = ref<'overview' | 'intraday' | 'single'>('overview');
  onMounted(() => emit('ready'));
</script>
<style scoped>
  .etf-workspace {
    min-width: 0;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    gap: 12px;
  }

  h2 {
    margin: 0;
    font-size: 18px;
  }

  nav {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  button {
    padding: 8px 16px;
    border: 1px solid #dbe4ee;
    border-radius: 7px;
    background: #fff;
    color: #40546b;
    font: inherit;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #a5bfff;
    background: #edf3ff;
    color: #2864ec;
  }

  .extras {
    margin-top: 16px;
    padding: 14px;
    border: 1px solid #dbe4ee;
    border-radius: 10px;
    background: #fff;
  }

  summary {
    font-weight: 600;
    cursor: pointer;
  }
</style>
