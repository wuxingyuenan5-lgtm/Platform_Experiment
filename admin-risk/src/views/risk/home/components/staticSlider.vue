<template>
  <div class="rounded-full h-1 control-bg2 relative">
    <div :style="innerStyle" class="bg-#C1272D h-full rounded-full"></div>
    <!-- <div
      :style="dotStyle"
      class="w-10px h-10px translate-y-[-7px] translate-x-[-7px] rounded-full absolute bg-#C1272D"
    ></div> -->
    <div class="flex justify-between text-xs color-third mt-2px">
      <div>0</div>
      <div>-{{ max }}%</div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { riskLevelOptions } from '@/utils/options/basicOptions';

  const props = defineProps({
    value: {
      type: [Number, String],
      default: 0,
    },
    levelList: {
      type: Array,
      default: () => [],
    },
    max: {
      type: Number,
      default: 100,
    },
  });
  const curLevel = ref<any>();
  const innerStyle = computed(() => {
    return {
      width: `${Math.min(Number(props.value) / props.max) * 100}%`,
      backgroundColor: curLevel.value ? curLevel.value.color : 'unset',
    };
  });
  const curLevelOptions = ref<any[]>([]);
  watch(
    () => props.levelList,
    (cur) => {
      curLevelOptions.value =
        cur?.map((items: any) => {
          const _item = riskLevelOptions.find((item) => item.value === items.grade);
          return {
            ..._item,
            riskValue: items.value,
          };
        }) || [];
    },
    { immediate: true, deep: true },
  );
  watch(
    () => [curLevelOptions.value, props.value],
    (cur) => {
      const _arr = JSON.parse(JSON.stringify(curLevelOptions.value));
      curLevel.value = _arr?.reverse()?.find((item: any) => {
        return -Number(props.value) <= item.riskValue;
      });
    },
    { immediate: true, deep: true },
  );
</script>
