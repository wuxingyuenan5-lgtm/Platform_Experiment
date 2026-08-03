<template>
  <div :class="['check-button', active && 'is-active']" @click="handleClick">
    <slot></slot>
  </div>
</template>
<script lang="ts" setup>
  import { watch, ref } from 'vue';

  const emit = defineEmits(['update:value']);
  const props = defineProps({
    value: {
      type: Boolean,
      default: false,
    },
  });
  const active = ref(false);
  function handleClick() {
    active.value = !active.value;
    emit('update:value', active.value);
  }
  watch(
    () => props.value,
    (newValue) => (active.value = newValue),
    { immediate: true },
  );
</script>
<style lang="less" scoped>
  .check-button {
    height: 32px;
    padding: 4px 15px;
    border-radius: 4px;
    background: @component-background-light;
    font-size: 14px;
    line-height: 1.5rem;
    word-break: keep-all;
    cursor: pointer;

    &.is-active {
      background: @primary-color;
      color: #000;
    }
  }
</style>
