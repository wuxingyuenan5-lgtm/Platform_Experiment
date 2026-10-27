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
            style: { minHeight: '160px' },
            role: 'alert',
          },
          [
            h('p', `“${props.widgetTitle}”暂不可用。`),
            h(
              'button',
              {
                type: 'button',
                onClick: () => {
                  hasError.value = false;
                },
              },
              '重试',
            ),
          ],
        );
      }

      return slots.default ? slots.default() : null;
    };
  },
});
