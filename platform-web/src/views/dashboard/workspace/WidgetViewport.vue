<template
  ><div ref="element" class="widget-viewport"
    ><slot v-if="seen"></slot><p v-else>正在准备小组件…</p></div
  ></template
>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useIntersectionObserver } from '@vueuse/core';

  const element = ref<HTMLElement>();
  const seen = ref(false);
  useIntersectionObserver(
    element,
    ([entry]) => {
      if (entry?.isIntersecting) seen.value = true;
    },
    { rootMargin: '200px' },
  );
</script>
<style scoped>
  .widget-viewport {
    min-width: 0;
    min-height: 120px;
  }
</style>
