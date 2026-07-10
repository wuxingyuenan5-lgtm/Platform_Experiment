<template>
  <div class="flex gap-4">
    <div v-for="item in options" :key="item.value" class="flex items-center">
      <div class="w-2 h-2 rounded-full mr-1" :style="{ background: item.color }"></div>
      <div class="color-third text-xs">{{ item.label }}</div>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { riskLevelOptions } from '@/utils/options/basicOptions';

  const options = riskLevelOptions;
</script>
