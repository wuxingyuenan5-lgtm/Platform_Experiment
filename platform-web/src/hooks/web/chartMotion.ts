import { nextTick, onActivated, onDeactivated, onBeforeUnmount, watch, type Ref } from 'vue';

export function reducedChartMotion() {
  return (
    typeof window !== 'undefined' &&
    Boolean(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
  );
}
export function motionOptions(options: any) {
  const series = Array.isArray(options.series)
    ? options.series
    : options.series
    ? [options.series]
    : [];
  const datasets = Array.isArray(options.dataset) ? options.dataset : [options.dataset];
  const sizes = series.map(
    (item: any) => item.data?.length ?? datasets[item.datasetIndex || 0]?.source?.length ?? 0,
  );
  const animate =
    !reducedChartMotion() &&
    Math.max(0, ...sizes) <= 1200 &&
    sizes.reduce((a: number, b: number) => a + b, 0) <= 3000;
  const motion = {
    animation: animate,
    animationDuration: animate ? 1000 : 0,
    animationDurationUpdate: animate ? 500 : 0,
    animationEasing: 'cubicInOut',
    animationEasingUpdate: 'cubicInOut',
    animationDelay: 0,
    animationDelayUpdate: 0,
  };
  return {
    ...options,
    ...motion,
    ...(options.series ? { series: series.map((item: any) => ({ ...item, ...motion })) } : {}),
  };
}

/** Reveal chart geometry at the native ETF chart's pace; gestures stay direct. */
export function useChartReveal(
  element: Ref<HTMLElement | SVGElement | undefined>,
  revealOnMount = true,
) {
  let animations: Animation[] = [];
  let revision = 0;
  let active = true;
  let drawn = false;
  function cancel() {
    revision++;
    animations.forEach((animation) => animation.cancel());
    animations = [];
  }
  async function reveal(points = 0) {
    const current = ++revision;
    await nextTick();
    if (current !== revision || !active) return;
    cancel();
    const elementValue = element.value;
    if (!elementValue) return;
    const series = elementValue.querySelectorAll<SVGElement>('[data-chart-kind]');
    // Dense plots use one lightweight reveal instead of animating thousands of marks.
    const shapes = points > 3000 || !series.length ? [elementValue] : Array.from(series);
    const duration = drawn ? 500 : 1000;
    drawn = true;
    if (reducedChartMotion()) return;
    shapes.forEach((shape) => {
      const frames =
        shape.dataset?.chartKind === 'bar'
          ? [{ transform: 'scaleY(0)' }, { transform: 'scaleY(1)' }]
          : [{ clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0% 0 0)' }];
      const animation = shape.animate?.(frames, {
        duration,
        easing: 'cubic-bezier(0.65, 0, 0.35, 1)',
      });
      if (animation) animations.push(animation);
    });
  }
  onBeforeUnmount(cancel);
  onDeactivated(() => {
    active = false;
    cancel();
  });
  onActivated(() => {
    active = true;
  });
  watch(
    element,
    (el, _old, cleanup) => {
      if (!el) return;
      el.addEventListener?.('pointerdown', cancel, { passive: true });
      el.addEventListener?.('wheel', cancel, { passive: true });
      if (
        revealOnMount &&
        (el.namespaceURI === 'http://www.w3.org/2000/svg' ||
          el.querySelector?.('[data-chart-kind]'))
      )
        void reveal();
      cleanup(() => {
        el.removeEventListener?.('pointerdown', cancel);
        el.removeEventListener?.('wheel', cancel);
      });
    },
    { immediate: true, flush: 'post' },
  );
  // Moving the chart must immediately interrupt any timed drawing.
  return Object.assign(reveal, { cancel });
}
