<template>
  <div class="flex">
    <div class="h-1 rounded-full control-bg2 relative flex-1">
      <template v-for="(item, index) in curLevelOptions" :key="item.value">
        <div v-if="index != 0" :style="gapFn(item)" class="w-2px bg-#fff h-full"></div>
      </template>
      <div :style="innerStyle" class="rounded-full"></div>
    </div>
    <div class="flex gap-1px ml-4px">
      <div class="w-5px h-5px rounded-full control-bg2" :style="dotStyle"></div>
      <div class="w-5px h-5px rounded-full control-bg2" :style="dotStyle"></div>
      <div class="w-5px h-5px rounded-full control-bg2"></div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { riskLevelOptions } from '@/utils/options/basicOptions';
  import { computed, watch, ref } from 'vue';

  const props = defineProps({
    value: {
      type: [Number, String],
      default: 0,
    },
    levelList: {
      type: Array,
      default: () => [],
    },
    // 是否由大到小排序的数据
    reverse: {
      type: Boolean,
      default: false,
    },
    showLevel: {
      // 是否展示等级配色
      type: Boolean,
      default: true,
    },
  });

  // console.log('levelList-----', props.levelList);
  // console.log('value-----', props.value);

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
  const curMax = computed(() => {
    return Math.max(...curLevelOptions.value.map((item) => item.riskValue)) || 1;
  });
  const curMin = computed(() => {
    return Math.min(...curLevelOptions.value.map((item) => item.riskValue)) || 0;
  });
  // 判断当前等级
  const curLevel = ref<any>();
  watch(
    () => [curLevelOptions.value, props.value],
    (cur) => {
      // 不改变原数组
      let _list = JSON.parse(JSON.stringify(curLevelOptions.value));
      if (!props.reverse) {
        curLevel.value = _list?.reverse()?.find((item: any) => {
          return Number(props.value) >= item.riskValue;
        });
      } else {
        curLevel.value = _list?.reverse()?.find((item: any) => {
          return Number(props.value) <= item.riskValue;
        });
      }
    },
    { immediate: true, deep: true },
  );
  // 超过最大级时dot的背景色发生变化
  const dotStyle = computed(() => {
    let _show = Number(props.value) >= curMax.value;
    if (props.reverse) {
      _show = Number(props.value) <= curMin.value;
    }
    return {
      backgroundColor: _show && curLevel.value && props.showLevel ? curLevel.value.color : '',
    };
  });

  const innerStyle = computed(() => {
    const _val = Number(props.value) - curMin.value;
    let _width = (_val > 0 ? _val : 0) / (curMax.value - curMin.value);
    if (props.reverse) {
      _width = 1 - _width;
    }
    let _bg = curLevel.value ? curLevel.value.color : 'unset';
    if (!props.showLevel) {
      _bg = 'unset';
    }
    return {
      width: `${Math.min(_width, 1) * 100 || 0}%`,
      backgroundColor: _bg,
      height: '100%',
    };
  });
  // console.log('innerStyle----', innerStyle);
  // console.log('curLevel----', curLevel);

  function gapFn(params: any) {
    const _val = params.riskValue - curMin.value;
    let _left = _val / (curMax.value - curMin.value);
    if (props.reverse) {
      _left = 1 - _left;
    }
    return {
      position: 'absolute',
      left: `${_left * 100}%`,
      height: '100%',
    };
  }
</script>
