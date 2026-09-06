import { defineComponent, h, onBeforeUnmount, onMounted, type PropType, ref, watch } from 'vue';
import type { WidgetConfig } from '../nativeData/dashboardClean';

const TradingViewWidget = defineComponent({
  name: 'TradingViewWidget',
  props: {
    widget: {
      type: Object as PropType<WidgetConfig>,
      required: true,
    },
  },
  setup(props) {
    const mountRef = ref<HTMLDivElement | null>(null);
    const loadFailed = ref(false);
    let resizeObserver: ResizeObserver | null = null;
    let intersectionObserver: IntersectionObserver | null = null;
    let renderTimer: number | null = null;
    let frameToken = 0;
    let lastSizeKey = '';

    const clearRenderTimers = () => {
      if (renderTimer) window.clearTimeout(renderTimer);
      renderTimer = null;
    };

    const renderWidget = () => {
      const mountNode = mountRef.value;
      if (!mountNode || !props.widget.scriptSrc || !props.widget.config) return;

      loadFailed.value = false;
      mountNode.innerHTML = '';

      try {
        const container = document.createElement('div');
        container.className = 'tradingview-widget-container';
        container.style.width = '100%';
        container.style.height = '100%';

        const widgetNode = document.createElement('div');
        widgetNode.className = 'tradingview-widget-container__widget';
        widgetNode.style.width = '100%';
        widgetNode.style.height = '100%';
        container.appendChild(widgetNode);

        const script = document.createElement('script');
        script.src = props.widget.scriptSrc;
        script.async = true;
        script.type = 'text/javascript';
        script.innerHTML = JSON.stringify(props.widget.config);
        script.onerror = () => {
          loadFailed.value = true;
          if (mountRef.value) mountRef.value.innerHTML = '';
        };

        container.appendChild(script);
        mountNode.appendChild(container);
      } catch (error) {
        console.error('[hedgeBoard] TradingView widget render failed:', props.widget.title, error);
        loadFailed.value = true;
        mountNode.innerHTML = '';
      }
    };

    const scheduleRender = (force = false) => {
      const mountNode = mountRef.value;
      if (!mountNode) return;

      // Embedded pages can move browser focus while they reload.  Once an
      // iframe is mounted, retain it across layout/scroll changes; only an
      // actual widget-config change may deliberately rebuild it.
      if (!force && mountNode.childElementCount) return;

      const width = mountNode.clientWidth;
      const height = mountNode.clientHeight;
      if (!width || !height) return;
      if (!mountNode.getClientRects().length) return;

      const nextSizeKey = `${Math.round(width)}x${Math.round(height)}`;
      if (!force && nextSizeKey === lastSizeKey) return;
      lastSizeKey = nextSizeKey;

      clearRenderTimers();
      renderTimer = window.setTimeout(() => {
        renderWidget();
      }, 96);
    };

    onMounted(() => {
      scheduleRender();
      frameToken = window.requestAnimationFrame(() => {
        frameToken = window.requestAnimationFrame(() => {
          scheduleRender();
        });
      });

      if (typeof ResizeObserver !== 'undefined' && mountRef.value) {
        resizeObserver = new ResizeObserver(() => {
          if (!mountRef.value?.childElementCount) scheduleRender();
        });
        resizeObserver.observe(mountRef.value);
      }

      if (typeof IntersectionObserver !== 'undefined' && mountRef.value) {
        intersectionObserver = new IntersectionObserver(
          (entries) => {
            if (
              entries.some((entry) => entry.isIntersecting) &&
              !mountRef.value?.childElementCount
            ) {
              scheduleRender();
            }
          },
          { threshold: 0.2 },
        );
        intersectionObserver.observe(mountRef.value);
      }
    });

    watch(
      () => props.widget,
      () => scheduleRender(true),
      { deep: true },
    );
    onBeforeUnmount(() => {
      if (frameToken) window.cancelAnimationFrame(frameToken);
      clearRenderTimers();
      resizeObserver?.disconnect();
      intersectionObserver?.disconnect();
      if (mountRef.value) mountRef.value.innerHTML = '';
    });

    return () =>
      loadFailed.value
        ? h(
            'div',
            {
              class: 'local-empty',
              'data-widget-height': String(props.widget.height ?? 360),
              style: { height: `${props.widget.height ?? 360}px` },
            },
            '该外部图表当前加载失败，页面主体已保留，可继续浏览其他模块。',
          )
        : h('div', {
            ref: mountRef,
            class: 'widget-frame',
            'data-widget-height': String(props.widget.height ?? 360),
            style: { height: `${props.widget.height ?? 360}px` },
          });
  },
});

export default TradingViewWidget;
