<template>
  <ThemeEtfPanorama :refresh-key="refreshKey" />
  <BroadEtfPanel :refresh-key="refreshKey" @ready="$emit('ready')" />
  <details
    class="etf-detail-workspace"
    @toggle="detailOpen = ($event.target as HTMLDetailsElement).open"
  >
    <summary>单只ETF完整分析</summary>
    <EtfDetailedWorkspace v-if="detailOpen" :refresh-key="refreshKey" />
  </details>
</template>
<script setup lang="ts">
  import { defineAsyncComponent, ref } from 'vue';
  import BroadEtfPanel from './BroadEtfPanel.vue';
  import ThemeEtfPanorama from './ThemeEtfPanorama.vue';

  const EtfDetailedWorkspace = defineAsyncComponent(() => import('./EtfDetailedWorkspace.vue'));
  const detailOpen = ref(false);
  defineProps<{ refreshKey?: number }>();
  defineEmits<{ ready: [] }>();
</script>
<style scoped>
  .etf-detail-workspace {
    margin-top: 16px;
    padding: 16px;
    border: 1px solid var(--strategy-border, #dbe4ee);
    border-radius: 12px;
    background: var(--strategy-surface, #fff);
  }

  summary {
    font-weight: 600;
    cursor: pointer;
  }
</style>
