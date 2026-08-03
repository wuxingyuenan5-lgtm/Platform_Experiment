import { defineComponent, h, type PropType } from 'vue';

export default defineComponent({
  name: 'MetricStrip',
  props: {
    metrics: {
      type: Array as PropType<Array<[string, string]>>,
      required: true,
    },
  },
  setup(props) {
    return () =>
      h(
        'div',
        { class: 'metric-strip' },
        props.metrics.map(([label, value]) =>
          h('article', { key: `${label}-${value}` }, [h('span', label), h('strong', value)]),
        ),
      );
  },
});
