<template>
  <div :class="['cur-tab', size == 'small' ? 'is-small' : '']">
    <div
      @click="handleClick(item)"
      :class="['cur-tab-item', noBorder ? 'no-border' : '', value == item.value ? 'active' : '']"
      v-for="item in options"
      :key="item.value"
    >
      <slot v-if="$slots?.label" name="label" :item="item"></slot>
      <template v-else>{{ item.label || item.value }}</template>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { watch } from 'vue';
  import { basicProps } from './props';

  const props = defineProps(basicProps);

  const emits = defineEmits(['update:value']);

  watch(
    () => props.value,
    (val) => {
      emits('update:value', val);
    },
  );

  watch(
    () => props.options,
    (val) => {
      if (val.length) {
        emits('update:value', val[0]?.value);
      }
    },
  );
  function handleClick(params: any) {
    emits('update:value', params.value);
  }
</script>
<style lang="less" scoped>
  .cur-tab {
    display: flex;
    color: @text-color-secondary;
    font-size: 16px;
    line-height: 24px;
    gap: 16px;

    &.is-small {
      font-size: 14px;
      line-height: 22px;
    }

    &-item {
      padding-bottom: 4px;
      cursor: pointer;

      &:hover,
      &.active {
        color: @primary-color;
      }

      &.active {
        border-bottom: 1px solid @primary-color;
      }

      &.no-border {
        border-bottom: 0;
      }
    }
  }
</style>
