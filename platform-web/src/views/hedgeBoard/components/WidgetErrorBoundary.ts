import { defineComponent, h, onErrorCaptured, ref, useSlots } from 'vue';

export default defineComponent({
  name: 'WidgetErrorBoundary',
  props: {
    widgetTitle: {
      type: String,
      required: true,
    },
  },
  setup(props) {
    const slots = useSlots();
    const hasError = ref(false);

    onErrorCaptured((error) => {
      console.error('[hedgeBoard] Widget boundary captured:', props.widgetTitle, error);
      hasError.value = true;
      return false;
    });

    return () => {
      if (hasError.value) {
        return h(
          'div',
          {
            class: 'local-empty',
            style: { minHeight: '360px' },
          },
          `模块 "${props.widgetTitle}" 渲染失败，已自动跳过，不影响其他内容浏览。`,
        );
      }

      return slots.default ? slots.default() : null;
    };
  },
});
