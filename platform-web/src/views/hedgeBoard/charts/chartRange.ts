import { h } from 'vue';

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
  const metaStyle = {
    position: 'relative',
    height: '14px',
    marginBottom: '2px',
    fontSize: '10px',
    lineHeight: 1,
    color: '#98a2b3',
  } as const;
  const viewportStyle = {
    position: 'relative',
    height: '24px',
    background: 'transparent',
    overflow: 'visible',
  } as const;
  const railStyle = {
    position: 'absolute',
    left: 0,
    right: 0,
    top: '50%',
    transform: 'translateY(-50%)',
    height: '16px',
    borderRadius: '3px',
    border: '1px solid rgba(205, 214, 224, 0.8)',
    background: 'rgba(240, 244, 248, 0.9)',
    boxShadow: 'inset 0 1px 1px rgba(148, 163, 184, 0.12)',
    zIndex: 1,
    cursor: 'pointer',
  } as const;
  const selectionStyle = {
    left: `${startPercent}%`,
    width: `${Math.max(4, endPercent - startPercent)}%`,
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    height: '16px',
    borderRadius: '3px',
    background: 'rgba(125, 167, 255, 0.12)',
    border: '1px solid rgba(125, 167, 255, 0.48)',
    boxShadow: 'inset 0 0 0 1px rgba(255, 255, 255, 0.42)',
    zIndex: 2,
    cursor: 'grab',
  } as const;
  const handleBaseStyle = {
    position: 'absolute',
    top: '50%',
    width: '12px',
    height: '12px',
    borderRadius: '999px',
    background: 'rgba(255, 255, 255, 0.98)',
    border: '2px solid #4f7bf5',
    boxShadow: '0 1px 3px rgba(79, 123, 245, 0.24)',
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
