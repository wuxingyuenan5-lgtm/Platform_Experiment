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
    let verifyTimers: number[] = [];
    let frameToken = 0;
    let lastSizeKey = '';
    let repairAttempts = 0;

    const clearRenderTimers = () => {
      if (renderTimer) window.clearTimeout(renderTimer);
      verifyTimers.forEach((timer) => window.clearTimeout(timer));
      renderTimer = null;
      verifyTimers = [];
    };

    const verifyWidgetLayout = () => {
      const mountNode = mountRef.value;
      if (!mountNode) return;

      const hostWidth = mountNode.clientWidth;
      if (!hostWidth) return;

      const iframe = mountNode.querySelector('iframe') as HTMLIFrameElement | null;
      const iframeWidth = iframe?.clientWidth ?? 0;
      if (iframe && iframeWidth > 0 && iframeWidth < hostWidth * 0.9 && repairAttempts < 3) {
        repairAttempts += 1;
        lastSizeKey = '';
        scheduleRender(true);
        return;
      }

      if (iframe && iframeWidth >= hostWidth * 0.9) repairAttempts = 0;
    };

    const scheduleLayoutHealing = () => {
      verifyTimers.forEach((timer) => window.clearTimeout(timer));
      verifyTimers = [180, 520, 1100, 1900].map((delay) =>
        window.setTimeout(() => {
          verifyWidgetLayout();
          window.dispatchEvent(new Event('resize'));
        }, delay),
      );
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
        script.onload = () => {
          scheduleLayoutHealing();
        };
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

      const width = mountNode.clientWidth;
      const height = mountNode.clientHeight;
      if (!width || !height) return;
      if (!mountNode.getClientRects().length) return;

      const nextSizeKey = `${Math.round(width)}x${Math.round(height)}`;
      if (!force && nextSizeKey === lastSizeKey && mountNode.childElementCount) return;
      lastSizeKey = nextSizeKey;

      clearRenderTimers();
      if (force) repairAttempts = 0;
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
          scheduleRender();
        });
        resizeObserver.observe(mountRef.value);
      }

      if (typeof IntersectionObserver !== 'undefined' && mountRef.value) {
        intersectionObserver = new IntersectionObserver(
          (entries) => {
            if (entries.some((entry) => entry.isIntersecting)) {
              scheduleRender(true);
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
