<template>
  <div>
    <div class="flex gap-2">
      <InputNumber class="w-full" :min="0" v-bind="imputProps" v-model:value="dataSource.val" />
      <Popconfirm
        v-if="showBtn"
        :disabled="!dataSource.val"
        placement="topRight"
        @confirm="handleClick"
        ok-text="确定"
        cancel-text="取消"
      >
        <template #title>
          <div class="text-nowrap">你确定{{ popTitle }}：{{ dataSource.val }}</div>
        </template>
        <Button :disabled="!dataSource.val" type="primary">平仓</Button>
      </Popconfirm>
    </div>
    <div class="pr-2">
      <Slider v-bind="sliderProps" v-model:value="dataSource.slider" @change="change" />
    </div>
  </div>
</template>
<script lang="tsx" setup>
  import type { SliderProps, InputNumberProps } from 'ant-design-vue';
  import { InputNumber, Button, Slider, Popconfirm, message } from 'ant-design-vue';
  import { reactive, defineProps, PropType, watch } from 'vue';
  import { watchDebounced } from '@vueuse/shared';

  const emit = defineEmits(['submit', 'update:value', 'change']);
  const props = defineProps({
    value: {
      type: [Number, String],
      default: 0,
    },
    total: {
      type: Number,
      default: 100,
    },
    popTitle: {
      type: String,
      default: '平仓',
    },
    imputProps: {
      type: Object as PropType<InputNumberProps>,
      default: () => ({
        placeholder: '请输入平仓数量',
      }),
    },
    sliderProps: {
      type: Object as PropType<SliderProps>,
      default: () => ({
        marks: {
          0: '0%',
          10: '10%',
          50: '50%',
          100: '100%',
        },
      }),
    },
    // 是否显示按钮
    showBtn: {
      type: Boolean,
      default: true,
    },
  });
  const dataSource = reactive<any>({
    val: null,
    slider: 0,
  });
  function handleClick() {
    emit('submit', dataSource.val);
  }
  function change(params: any) {
    dataSource.val = ((params / 100) * props.total).toFixed(props.imputProps?.precision || 2);
  }

  watchDebounced(
    () => dataSource.val,
    (val) => {
      // console.log('val-----', val, props.total, props.imputProps);
      if (val > props.total) {
        dataSource.val = props.total;
        return;
      }
      if (props.imputProps?.min && val < props.imputProps.min) {
        dataSource.val = props.imputProps.min;
        return;
      }

      dataSource.slider = (val / props.total) * 100;
      // console.log('val-----2323', dataSource.slider);
      emit('update:value', val);
      emit('change', dataSource.val);
    },
    { debounce: 150 },
  );
  watch(
    () => props.value,
    (val) => {
      dataSource.val = val;
    },
  );
  function reset() {
    dataSource.val = null;
    dataSource.slider = 0;
  }
  defineExpose({
    reset,
  });
</script>
