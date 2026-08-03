// 设置定时器
import { tryOnUnmounted, tryOnMounted, useDocumentVisibility } from '@vueuse/core';
import { watch, ref } from 'vue';

export interface UseIntervalCustomOptions {
  delay?: number; // 延迟时间
  immediate?: boolean; // 立即执行
  immediateStart?: boolean; // 页面首屏未显示，展示后立即执行，
  // artificialStop?: boolean; // 人工停止，页面不可见不会再去激活
}

export function useIntervalCustom(callback: Function, options: UseIntervalCustomOptions = {}) {
  const visibility = useDocumentVisibility();
  const artificialStop = ref(false);
  const { delay = 1000, immediate = true, immediateStart = false } = options;
  let timer: any = null;

  const setIntervalImmediately = (func, interval) => {
    if (immediate || immediateStart) {
      func();
    }
    return setInterval(func, interval);
  };
  const start = () => {
    stop();
    timer = setIntervalImmediately(fetch, delay);
  };

  const stop = () => {
    if (!timer) return;
    clearInterval(timer);
    timer = null;
  };
  tryOnMounted(immediate ? start : () => {});
  tryOnUnmounted(() => {
    stop();
  });
  // 监听页面可见性变化
  watch(visibility, (cur, pre) => {
    if (cur === 'visible' && pre === 'hidden' && !artificialStop.value) {
      start();
    } else {
      stop();
    }
  });

  async function fetch() {
    try {
      await callback();
    } catch (error) {
      stop();
    }
  }

  return { start, stop, fetch, artificialStop };
}
