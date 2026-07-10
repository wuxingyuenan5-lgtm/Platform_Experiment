<template>
  <div @click="$emit('click')" :class="['ghost-btn', curClass]">
    <slot></slot>
  </div>
</template>
<script lang="ts" setup>
  import { computed } from 'vue';
  import { buttonProps } from './props';

  const props = defineProps({
    ...buttonProps,
    size: {
      type: String,
      default: 'default',
    },
  });
  const curClass = computed(() => {
    let _class = '';
    if (props?.color) {
      _class = props?.color + ' ';
    }
    if (props?.size) {
      _class += props?.size + ' ';
    }
    if (props?.disabled) {
      _class += 'disabled ';
    }
    if (props?.noBorder) {
      _class += 'no-border ';
    }
    return _class;
  });
</script>
<style lang="less" scoped>
  .ghost-btn {
    display: inline-block;
    height: 28px;
    padding: 4px 12px;
    border: 1px solid @primary-color;
    border-radius: 4px;
    background-color: fade(@primary-color, 10);
    color: @primary-color;
    font-size: 13px;
    line-height: 18px;
    word-break: keep-all;
    cursor: pointer;

    &.middle {
      height: 32px;
      font-size: 14px;
      line-height: 22px;
    }

    &.small {
      height: 24px;
      font-size: 12px;
      line-height: 14px;
    }

    &.error {
      border-color: @color-error;
      background-color: fade(@color-error, 10);
      color: @color-error;
    }

    &.success {
      border-color: 1px solid @color-success;
      background-color: fade(@color-success, 10);
      color: @color-success;
    }

    &.info {
      border-color: 1px solid transparent;
      background-color: rgb(255 255 255 / 10%);
      color: rgb(255 255 255 / 80%);
    }

    &.disabled {
      border-color: transparent;
      background: rgb(255 255 255 / 5%);
      color: rgb(255 255 255 / 50%);
      cursor: no-drop;
    }

    &.no-border {
      border-color: transparent;
    }
  }
</style>
