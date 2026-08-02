import { h } from 'vue';

import { getRange, scaleX, scaleY } from './chartCore';

function buildRangeOverview(values: number[], width: number, height: number) {
  if (values.length <= 1) {
    const midY = (height / 2).toFixed(2);
    return {
      linePath: `M 0 ${midY} L ${width.toFixed(2)} ${midY}`,
      areaPath: `M 0 ${height.toFixed(2)} L 0 ${midY} L ${width.toFixed(
        2,
      )} ${midY} L ${width.toFixed(2)} ${height.toFixed(2)} Z`,
    };
  }

  const range = getRange(values);
  const points = values.map((value, index) => {
    const x = scaleX(index, values.length, width);
    const y = scaleY(value, range.min, range.max, height - 4) + 2;
    return { x, y };
  });
  const linePath = points
    .map(
      (point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`,
    )
    .join(' ');
  const areaPath = [
    `M ${points[0].x.toFixed(2)} ${height.toFixed(2)}`,
    ...points.map((point) => `L ${point.x.toFixed(2)} ${point.y.toFixed(2)}`),
    `L ${points.at(-1)!.x.toFixed(2)} ${height.toFixed(2)}`,
    'Z',
  ].join(' ');

  return { linePath, areaPath };
}

function clampRangeValue(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function beginChartRangeDrag(
  event: MouseEvent,
  options: {
    mode: 'start' | 'end' | 'window' | 'jump';
    viewport: HTMLElement | null;
    maxIndex: number;
    minGap: number;
    startIndex: number;
    endIndex: number;
    onStartChange: (value: number) => void;
    onEndChange: (value: number) => void;
  },
) {
  const { viewport, mode, maxIndex, minGap, startIndex, endIndex, onStartChange, onEndChange } =
    options;
  if (!viewport || maxIndex <= 0) return;

  event.preventDefault();
  event.stopPropagation();

  const rect = viewport.getBoundingClientRect();
  const pixelToIndex = (clientX: number) => {
    const ratio = clampRangeValue((clientX - rect.left) / rect.width, 0, 1);
    return Math.round(ratio * maxIndex);
  };

  const windowSpan = endIndex - startIndex;
  const anchorIndex = pixelToIndex(event.clientX);

  if (mode === 'jump') {
    const centeredStart = clampRangeValue(
      anchorIndex - Math.round(windowSpan / 2),
      0,
      Math.max(0, maxIndex - windowSpan),
    );
    onStartChange(centeredStart);
    onEndChange(centeredStart + windowSpan);
    return;
  }

  const dragOriginX = event.clientX;
  const dragOriginStart = startIndex;
  const dragOriginEnd = endIndex;

  const handleMouseMove = (moveEvent: MouseEvent) => {
    if (mode === 'window') {
      const deltaRatio = (moveEvent.clientX - dragOriginX) / rect.width;
      const deltaIndex = Math.round(deltaRatio * maxIndex);
      const nextStart = clampRangeValue(
        dragOriginStart + deltaIndex,
        0,
        Math.max(0, maxIndex - windowSpan),
      );
      onStartChange(nextStart);
      onEndChange(nextStart + windowSpan);
      return;
    }

    const nextIndex = pixelToIndex(moveEvent.clientX);
    if (mode === 'start') {
      onStartChange(clampRangeValue(nextIndex, 0, dragOriginEnd - minGap));
      return;
    }
    onEndChange(clampRangeValue(nextIndex, dragOriginStart + minGap, maxIndex));
  };

  const handleMouseUp = () => {
    window.removeEventListener('mousemove', handleMouseMove);
    window.removeEventListener('mouseup', handleMouseUp);
  };

  window.addEventListener('mousemove', handleMouseMove);
  window.addEventListener('mouseup', handleMouseUp);
}

export function renderChartRangeSelector(options: {
  labels: string[];
  values: number[];
  startIndex: number;
  endIndex: number;
  minWindowSize: number;
  onStartChange: (value: number) => void;
  onEndChange: (value: number) => void;
}) {
  const { labels, values, startIndex, endIndex, minWindowSize, onStartChange, onEndChange } =
    options;
  if (labels.length <= 1) return null;

  const maxIndex = labels.length - 1;
  const minSpan = Math.max(2, Math.min(minWindowSize, labels.length));
  const minGap = minSpan - 1;
  const safeStart = Math.max(0, Math.min(startIndex, Math.max(0, maxIndex - minGap)));
  const safeEnd = Math.max(safeStart + minGap, Math.min(endIndex, maxIndex));
  const startPercent = maxIndex <= 0 ? 0 : (safeStart / maxIndex) * 100;
  const endPercent = maxIndex <= 0 ? 100 : (safeEnd / maxIndex) * 100;
  const getLabelTransform = (percent: number, side: 'start' | 'end') => {
    if (side === 'start') {
      if (percent < 8) return 'translateX(0)';
      if (percent > 92) return 'translateX(-100%)';
    } else {
      if (percent < 8) return 'translateX(0)';
      if (percent > 92) return 'translateX(-100%)';
    }
    return 'translateX(-50%)';
  };
  const { linePath, areaPath } = buildRangeOverview(values, 100, 20);
  const metaStyle = {
    position: 'relative',
    height: '16px',
    marginBottom: '4px',
    fontSize: '11px',
    lineHeight: 1,
    color: 'var(--hedge-cool-muted)',
  } as const;
  const viewportStyle = {
    position: 'relative',
    height: '22px',
    background: 'transparent',
    overflow: 'hidden',
  } as const;
  const overviewStyle = {
    position: 'absolute',
    inset: '1px 0',
    width: '100%',
    height: 'calc(100% - 2px)',
    display: 'block',
    pointerEvents: 'none',
    zIndex: 0,
  } as const;
  const railStyle = {
    position: 'absolute',
    left: 0,
    right: 0,
    top: '50%',
    transform: 'translateY(-50%)',
    height: '12px',
    borderRadius: '999px',
    border: '1px solid rgba(192, 205, 227, 0.92)',
    background: 'rgba(225, 235, 252, 0.28)',
    boxShadow: 'inset 0 1px 1px rgba(255, 255, 255, 0.72)',
    zIndex: 1,
    cursor: 'pointer',
  } as const;
  const selectionStyle = {
    left: `${startPercent}%`,
    width: `${Math.max(4, endPercent - startPercent)}%`,
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    height: '12px',
    borderRadius: '999px',
    background: 'rgba(202, 218, 251, 0.46)',
    border: '1px solid rgba(142, 171, 235, 0.88)',
    boxShadow: 'inset 0 0 0 1px rgba(255, 255, 255, 0.32)',
    zIndex: 2,
    cursor: 'grab',
  } as const;
  const handleBaseStyle = {
    position: 'absolute',
    top: '50%',
    width: '6px',
    height: '14px',
    borderRadius: '999px',
    background: 'rgba(255, 255, 255, 0.98)',
    border: '1px solid rgba(146, 171, 230, 0.9)',
    boxShadow: '0 1px 2px rgba(124, 145, 186, 0.14)',
    transform: 'translateY(-50%)',
    cursor: 'ew-resize',
    zIndex: 3,
  } as const;

  return h('div', { class: 'chart-range' }, [
    h('div', { class: 'chart-range__labels', style: metaStyle }, [
      h(
        'span',
        {
          class: 'chart-range__label chart-range__label--start',
          style: {
            position: 'absolute',
            left: `${startPercent}%`,
            top: 0,
            transform: getLabelTransform(startPercent, 'start'),
            whiteSpace: 'nowrap',
          },
        },
        labels[safeStart] ?? '',
      ),
      h(
        'span',
        {
          class: 'chart-range__label chart-range__label--end',
          style: {
            position: 'absolute',
            left: `${endPercent}%`,
            top: 0,
            transform: getLabelTransform(endPercent, 'end'),
            whiteSpace: 'nowrap',
          },
        },
        labels[safeEnd] ?? '',
      ),
    ]),
    h(
      'div',
      {
        class: 'chart-range__viewport',
        style: viewportStyle,
        onMousedown: (mouseEvent: MouseEvent) =>
          beginChartRangeDrag(mouseEvent, {
            mode: 'jump',
            viewport: mouseEvent.currentTarget as HTMLElement,
            maxIndex,
            minGap,
            startIndex: safeStart,
            endIndex: safeEnd,
            onStartChange,
            onEndChange,
          }),
      },
      [
        h(
          'svg',
          {
            viewBox: '0 0 100 20',
            preserveAspectRatio: 'none',
            class: 'chart-range__overview',
            style: overviewStyle,
            'aria-hidden': 'true',
          },
          [
            h('path', {
              d: areaPath,
              class: 'chart-range__overview-area',
              fill: 'rgba(197, 214, 249, 0.7)',
            }),
            h('path', {
              d: linePath,
              class: 'chart-range__overview-line',
              fill: 'none',
              stroke: 'rgba(137, 167, 233, 0.95)',
              'stroke-width': 1.1,
              'stroke-linecap': 'round',
              'stroke-linejoin': 'round',
            }),
          ],
        ),
        h('span', {
          class: 'chart-range__rail',
          style: railStyle,
          'aria-hidden': 'true',
        }),
        h(
          'div',
          {
            class: 'chart-range__selection',
            style: selectionStyle,
            onMousedown: (mouseEvent: MouseEvent) =>
              beginChartRangeDrag(mouseEvent, {
                mode: 'window',
                viewport: (mouseEvent.currentTarget as HTMLElement).closest(
                  '.chart-range__viewport',
                ) as HTMLElement | null,
                maxIndex,
                minGap,
                startIndex: safeStart,
                endIndex: safeEnd,
                onStartChange,
                onEndChange,
              }),
          },
          [
            h('span', {
              class: 'chart-range__handle chart-range__handle--start',
              style: { ...handleBaseStyle, left: '-3px' },
              onMousedown: (mouseEvent: MouseEvent) =>
                beginChartRangeDrag(mouseEvent, {
                  mode: 'start',
                  viewport: (mouseEvent.currentTarget as HTMLElement).closest(
                    '.chart-range__viewport',
                  ) as HTMLElement | null,
                  maxIndex,
                  minGap,
                  startIndex: safeStart,
                  endIndex: safeEnd,
                  onStartChange,
                  onEndChange,
                }),
            }),
            h('span', {
              class: 'chart-range__handle chart-range__handle--end',
              style: { ...handleBaseStyle, right: '-3px' },
              onMousedown: (mouseEvent: MouseEvent) =>
                beginChartRangeDrag(mouseEvent, {
                  mode: 'end',
                  viewport: (mouseEvent.currentTarget as HTMLElement).closest(
                    '.chart-range__viewport',
                  ) as HTMLElement | null,
                  maxIndex,
                  minGap,
                  startIndex: safeStart,
                  endIndex: safeEnd,
                  onStartChange,
                  onEndChange,
                }),
            }),
          ],
        ),
      ],
    ),
  ]);
}
