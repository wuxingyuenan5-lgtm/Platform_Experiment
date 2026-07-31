<template>
  <div :class="['container', paddingClass, bgType]">
    <slot></slot>
  </div>
</template>
<script lang="ts">
  import { PropType, computed } from 'vue';

  export enum ContainerBgType {
    DEFAULT = 'default',
    YELLOW = 'yellow',
    GREEN = 'green',
    RED = 'red',
  }
  export enum ContainerPaddingType {
    DEFAULT = 'default',
    SAME = 'same',
    NONE = 'none',
  }

  export default {
    props: {
      bgType: {
        type: String as PropType<ContainerBgType>,
        default: ContainerBgType.DEFAULT,
      },
      paddingType: {
        type: String as PropType<ContainerPaddingType>,
        default: ContainerPaddingType.DEFAULT,
      },
    },
    setup(props) {
      const paddingClass = computed(() => {
        switch (props.paddingType) {
          case ContainerPaddingType.SAME:
            return 'py-3 px-3';
          case ContainerPaddingType.NONE:
            return 'py-0 px-0';
          default:
            return 'py-3 px-5';
        }
      });
      return {
        ...props,
        paddingClass,
      };
    },
  };
</script>
<style lang="less" scoped>
  .container {
    border-radius: 4px;
    background-color: @component-background-light;

    &.green {
      background-color: fade(@success-color, 30%);
    }

    &.yellow {
      background-color: fade(@warning-color, 70%);
    }

    &.red {
      background-color: fade(@error-color, 40%);
    }
  }
</style>
