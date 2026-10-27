import { skeletonProps } from 'ant-design-vue/es/skeleton';
import type { PropType } from 'vue';
import type { EmptyProps } from 'ant-design-vue';

export function baseSkeletonProps() {
  return {
    ...skeletonProps(),
    active: {
      type: Boolean,
      default: true,
    },
    showEmpty: {
      type: Boolean,
      default: false,
    },
    emptyProps: {
      type: Object as PropType<EmptyProps>,
      default: () => ({}),
      // image: {
      //     type: Object as PropType<VNode>,
      //     default: Empty.PRESENTED_IMAGE_SIMPLE
      // }
    },
  };
}
