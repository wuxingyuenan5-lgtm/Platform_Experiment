<template>
  <div :class="['basic-tabs', size]">
    <template v-if="options.length > 0">
      <div
        v-for="(item, i) in options"
        :key="item?.value || i"
        :class="['basic-tabs_item', curValue == item.value && 'active']"
        @click="handleClick(item)"
      >
        {{ item.label || item.value }}
      </div>
    </template>
  </div>
</template>
<script lang="ts" setup>
  import { ref, watch } from 'vue';
  import { basicProps } from './props';

  const emit = defineEmits(['update:value', 'change']);
  const props = defineProps(basicProps);
  const { options = [], value, size } = props;
  const curValue = ref(value || options[0]?.value);
  watch(curValue, (val) => {
    emit('update:value', val);
  });
  function handleClick(params: any) {
    curValue.value = params.value;
    emit('change', params);
  }
</script>
<style lang="less" scoped>
  .basic-tabs {
    display: flex;
    color: @text-color-third;

    &_item {
      padding: 9px 6px;
      font-size: 14px;
      line-height: 20px;
      cursor: pointer;

      &.active {
        color: @text-color-base;
      }
    }

    &.small {
      .basic-tabs_item {
        padding: 8px 6px;
        font-size: 12px;
        line-height: 16px;
      }
    }
  }
</style>
