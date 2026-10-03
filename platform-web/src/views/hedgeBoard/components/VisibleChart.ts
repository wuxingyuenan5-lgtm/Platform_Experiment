import {
  defineComponent,
  h,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
} from 'vue';

/** Mount expensive local charts only when their card approaches the viewport. */
export default defineComponent({
  name: 'VisibleChart',
  props: { height: { type: Number, default: 360 } },
  setup(props, { slots }) {
    const host = ref<HTMLElement>();
    const loaded = ref(false);
    let observer: IntersectionObserver | undefined;

    function stop() {
      observer?.disconnect();
      observer = undefined;
    }

    function observe() {
      if (loaded.value || observer || !host.value) return;
      if (typeof IntersectionObserver === 'undefined') {
        loaded.value = true;
        return;
      }
      observer = new IntersectionObserver(
        (entries) => {
          if (!entries.some((entry) => entry.isIntersecting)) return;
          loaded.value = true;
          stop();
        },
        { rootMargin: '160px 0px' },
      );
      observer.observe(host.value);
    }

    onMounted(observe);
    onActivated(observe);
    onDeactivated(stop);
    onBeforeUnmount(stop);

    return () =>
      h('div', { ref: host, class: 'visible-chart', 'data-loaded': loaded.value }, [
        loaded.value
          ? slots.default?.()
          : h('div', {
              class: 'visible-chart__placeholder',
              style: { height: `${props.height}px` },
              'aria-hidden': 'true',
            }),
      ]);
  },
});
