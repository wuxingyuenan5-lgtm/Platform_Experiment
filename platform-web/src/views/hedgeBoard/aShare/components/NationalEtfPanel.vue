<template>
  <iframe
    :key="`${refreshKey}:${activation}`"
    ref="frame"
    :title="view === 'futures' ? '中信期货股指期货持仓' : '国家队ETF动向追踪'"
    :src="`/api/v1/research/a-share/national-etf/page?view=${view}`"
    sandbox="allow-scripts"
    :style="{ width: '100%', height: `${height}px`, border: '0', borderRadius: '10px' }"
  ></iframe>
</template>
<script setup lang="ts">
  import { ref, onActivated, onMounted, onBeforeUnmount } from 'vue';

  const props = withDefaults(defineProps<{ view?: 'etf' | 'futures'; refreshKey?: number }>(), {
    view: 'etf',
  });
  const frame = ref<HTMLIFrameElement>();
  const activation = ref(0);
  // Browsers discard iframe documents when KeepAlive moves their DOM nodes.
  // Replace only the embedded document after the owning page is connected again.
  onActivated(() => {
    activation.value++;
  });
  const height = ref(props.view === 'futures' ? 680 : 2400);
  function resize(event: MessageEvent) {
    if (event.source !== frame.value?.contentWindow || event.data?.type !== 'national-etf-height')
      return;
    const size = event.data.height;
    if (typeof size === 'number' && Number.isFinite(size) && size > 0 && size <= 20000)
      height.value = Math.max(120, Math.ceil(size));
  }
  onMounted(() => window.addEventListener('message', resize));
  onBeforeUnmount(() => window.removeEventListener('message', resize));
</script>
