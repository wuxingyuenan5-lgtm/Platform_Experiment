<template>
  <div class="etf-tab-content">
    <section v-if="tab === 'overview'" :aria-label="flowOnly ? undefined : 'ETF总览'">
      <EtfObservationPanel
        :refresh-key="refreshKey"
        mode="daily"
        :flow-only="flowOnly"
        @ready="$emit('ready')"
      />
      <template v-if="!flowOnly">
        <EtfObservationPanel :refresh-key="refreshKey" mode="support" />
        <EtfMethodologyPanel :refresh-key="refreshKey" />
      </template>
    </section>
    <EtfObservationPanel
      v-else-if="tab === 'intraday'"
      :refresh-key="refreshKey"
      mode="intraday"
      @ready="$emit('ready')"
    />
    <EtfSinglePanel v-else :refresh-key="refreshKey" @ready="$emit('ready')" />
  </div>
</template>
<script setup lang="ts">
  import { defineAsyncComponent, h } from 'vue';
  import EtfObservationPanel from './EtfObservationPanel.vue';
  import EtfMethodologyPanel from './EtfMethodologyPanel.vue';

  const EtfSinglePanel = defineAsyncComponent({
    loader: () => import('./EtfSinglePanel.vue'),
    delay: 0,
    loadingComponent: { render: () => h('p', { role: 'status' }, '正在打开主题ETF…') },
    errorComponent: {
      render: () => h('p', { role: 'alert' }, '主题ETF界面加载失败，请刷新页面重试。'),
    },
  });
  defineProps<{
    tab: 'overview' | 'intraday' | 'single';
    flowOnly?: boolean;
    refreshKey?: number;
  }>();
  defineEmits<{ ready: [] }>();
</script>
