import type { EChartsOption } from 'echarts';
import type { Ref } from 'vue';
import { useTimeoutFn } from '@vben/hooks';
import { tryOnUnmounted, useDebounceFn } from '@vueuse/core';
import {
  unref,
  nextTick,
  watch,
  computed,
  shallowRef,
  onMounted,
  onActivated,
  onDeactivated,
} from 'vue';
import { useEventListener } from '@/hooks/event/useEventListener';
import { useBreakpoint } from '@/hooks/event/useBreakpoint';
import echarts from '@/utils/lib/echarts';
import { useRootSetting } from '@/hooks/setting/useRootSetting';
import { useMenuSetting } from '@/hooks/setting/useMenuSetting';

export function useECharts(
  elRef: Ref<HTMLDivElement>,
  theme: 'light' | 'dark' | 'default' = 'default',
) {
  const { getDarkMode: getSysDarkMode } = useRootSetting();
  const { getCollapsed } = useMenuSetting();

  const getDarkMode = computed(() => {
    return theme === 'default' ? getSysDarkMode.value : theme;
  });
  let chartInstance: echarts.ECharts | null = null;
  let resizeFn: Fn = resize;
  const cacheOptions = shallowRef({}) as Ref<EChartsOption>;
  let removeResizeFn: Fn = () => {};
  let active = true;
  let disposed = false;
  let pending = false;
  let clearPending = false;
  let resizeObserver: ResizeObserver | undefined;
  let viewportObserver: IntersectionObserver | undefined;
  let nearViewport = typeof IntersectionObserver === 'undefined';

  resizeFn = useDebounceFn(resize, 200);

  const getOptions = computed(() => {
    if (getDarkMode.value !== 'dark') {
      return cacheOptions.value as EChartsOption;
    }
    return {
      tooltip: {
        show: true,
        backgroundColor: '#3D3F47',
        borderColor: '#3D3F47',
        textStyle: {
          color: '#D1D4DCFF',
        },
      },
      legend: {
        show: true,
        icon: 'rect',
        itemWidth: 12,
        itemHeight: 2,
        itemGap: 36,
        // textStyle: {
        //   color: '#D1D4DCFF',
        // },
      },
      backgroundColor: 'transparent',
      ...cacheOptions.value,
    } as EChartsOption;
  });

  function initCharts(t = theme) {
    const el = unref(elRef);
    if (disposed || !active || !nearViewport || !el || !el.offsetWidth || !el.offsetHeight) {
      return;
    }

    chartInstance = echarts.init(el, t);
    const { removeEvent } = useEventListener({
      el: window,
      name: 'resize',
      listener: resizeFn,
    });
    removeResizeFn = removeEvent;
    const { widthRef, screenEnum } = useBreakpoint();
    if (unref(widthRef) <= screenEnum.MD || el.offsetHeight === 0) {
      useTimeoutFn(() => {
        resizeFn();
      }, 30);
    }
  }

  function applyPending() {
    const el = unref(elRef);
    if (disposed || !active || !nearViewport || !el?.offsetWidth || !el.offsetHeight) return;
    if (!chartInstance && pending) initCharts(getDarkMode.value as 'default');
    if (!chartInstance || !pending) return;
    if (clearPending) chartInstance.clear();
    chartInstance.setOption(unref(getOptions));
    pending = false;
    clearPending = false;
  }

  async function setOptions(options: EChartsOption, clear = true) {
    if (disposed) return null;
    cacheOptions.value = options;
    clearPending = clearPending || clear;
    pending = true;
    await nextTick();
    applyPending();
    return null;
  }

  function resize() {
    const el = unref(elRef);
    if (disposed || !active || !nearViewport || !el?.offsetWidth || !el.offsetHeight) return;
    applyPending();
    chartInstance?.resize({
      animation: {
        duration: 300,
        easing: 'quadraticIn',
      },
    });
  }

  watch(
    () => getDarkMode.value,
    (theme) => {
      if (chartInstance) {
        removeResizeFn();
        chartInstance.dispose();
        chartInstance = null;
        initCharts(theme as 'default');
        setOptions(cacheOptions.value);
      }
    },
  );

  watch(getCollapsed, (_) => {
    useTimeoutFn(() => {
      resizeFn();
    }, 300);
  });

  onMounted(() => {
    if (typeof IntersectionObserver !== 'undefined' && unref(elRef)) {
      viewportObserver = new IntersectionObserver(
        (entries) => {
          nearViewport = entries.some((entry) => entry.isIntersecting);
          if (nearViewport) resize();
        },
        { rootMargin: '300px' },
      );
      viewportObserver.observe(unref(elRef));
    }
    if (typeof ResizeObserver !== 'undefined' && unref(elRef)) {
      resizeObserver = new ResizeObserver(() => resize());
      resizeObserver.observe(unref(elRef));
    }
    resize();
  });
  onDeactivated(() => {
    active = false;
  });
  onActivated(() => {
    active = true;
    nextTick(resize);
  });

  tryOnUnmounted(() => {
    disposed = true;
    viewportObserver?.disconnect();
    resizeObserver?.disconnect();
    if (!chartInstance) return;
    removeResizeFn();
    chartInstance.dispose();
    chartInstance = null;
  });

  function getInstance(): echarts.ECharts | null {
    if (!chartInstance) {
      initCharts(getDarkMode.value as 'default');
    }
    return chartInstance;
  }

  return {
    setOptions,
    resize,
    echarts,
    getInstance,
  };
}
