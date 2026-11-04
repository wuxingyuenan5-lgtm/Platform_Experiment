<template>
  <WidgetErrorBoundary :widget-title="title">
    <LocalChartWidget v-if="option?.widget" :widget="option.widget" />
    <BroadEtfPanel
      v-else-if="option?.broadView"
      :widget-only="option.broadView"
      :initial-index="option.broadIndex"
    /><p v-else>请选择可独立展示的小组件。</p>
  </WidgetErrorBoundary>
</template>
<script setup lang="ts">
  import { computed, defineAsyncComponent } from 'vue';
  import { useUserStore } from '@/store/modules/user';
  import { moduleCatalog } from './moduleCatalog';
  import LocalChartWidget from '@/views/hedgeBoard/charts/LocalChartWidget';
  import WidgetErrorBoundary from '@/views/hedgeBoard/components/WidgetErrorBoundary';

  const BroadEtfPanel = defineAsyncComponent(
    () => import('@/views/hedgeBoard/aShare/components/BroadEtfPanel.vue'),
  );
  const props = defineProps<{ path: string; title: string }>();
  const user = useUserStore();
  const option = computed(() =>
    moduleCatalog(user.getAuthentication?.permissions || []).find((m) => m.path === props.path),
  );
</script>
