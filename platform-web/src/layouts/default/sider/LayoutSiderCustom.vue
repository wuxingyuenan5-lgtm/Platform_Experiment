<template>
  <div class="pt-8 pb-8" :style="getHiddenDomStyle">
    <img class="pl-10 pb-10" :src="logoSvg" />
    <div> layoutsider </div>
  </div>
</template>
<script lang="ts" setup>
  import { computed, CSSProperties, unref } from 'vue';
  import logoSvg from '@/assets/svg/logo.png';
  import { useMenuSetting } from '@/hooks/setting/useMenuSetting';

  const { getRealWidth } = useMenuSetting();

  const getHiddenDomStyle = computed((): CSSProperties => {
    const width = `${unref(getRealWidth)}px`;
    return {
      width,
      overflow: 'hidden',
      flex: `0 0 ${width}`,
      maxWidth: width,
      minWidth: width,
      transition: 'all 0.2s',
    };
  });
</script>
