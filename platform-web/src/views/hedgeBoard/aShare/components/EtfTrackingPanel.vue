<template>
  <section class="etf-workspace" :aria-label="flowOnly ? '宽基ETF资金' : 'ETF跟踪'">
    <KeepAlive>
      <EtfTabContent
        :key="tab"
        :tab="tab"
        :flow-only="flowOnly"
        :refresh-key="refreshKey"
        @ready="$emit('ready')"
      />
    </KeepAlive>
  </section>
</template>
<script setup lang="ts">
  import { onMounted } from 'vue';
  import EtfTabContent from './EtfTabContent.vue';

  defineProps<{
    tab: 'overview' | 'intraday' | 'single';
    flowOnly?: boolean;
    refreshKey?: number;
  }>();
  const emit = defineEmits<{ ready: [] }>();
  onMounted(() => emit('ready'));
</script>
<style scoped>
  .etf-workspace {
    min-width: 0;
  }
</style>
