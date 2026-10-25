import type { NarrativeDriver } from '@/api/macroNarratives';

export const narrativeColors = [
  '#176f55',
  '#946619',
  '#465db3',
  '#7856a6',
  '#be5147',
  '#28748f',
  '#887046',
  '#4e7f3d',
  '#a54681',
  '#4d6584',
  '#a07910',
  '#237e83',
  '#6a5caa',
  '#a65e2f',
  '#307b5c',
  '#727b28',
  '#4e73a3',
  '#8d4f7d',
  '#786743',
];
export const colorFor = (index: number) => narrativeColors[index % narrativeColors.length];

export function mapSnapshot(drivers: NarrativeDriver[], end: string) {
  return drivers.flatMap((driver, index) => {
    const point = [...driver.history].reverse().find((p) => p.date <= end && p.momentum !== null);
    if (!point || (Date.parse(end) - Date.parse(point.date)) / 86400000 > 14) return [];
    return [{ driver, point, color: colorFor(index) }];
  });
}

export function narrativeMap(drivers: NarrativeDriver[], end: string) {
  const rows = mapSnapshot(drivers, end);
  const domain = {
    x: Math.max(2.5, ...rows.map((r) => Math.abs(r.point.score))) * 1.12,
    y: Math.max(1.5, ...rows.map((r) => Math.abs(r.point.momentum!))) * 1.12,
  };
  const boxes: Array<{ left: number; top: number; width: number }> = [];
  const points = rows
    .map((row) => ({
      ...row,
      x: 550 + (row.point.score / domain.x) * 470,
      y: 250 - (row.point.momentum! / domain.y) * 175,
    }))
    .sort((a, b) => a.y - b.y)
    .map((row) => {
      const width = Array.from(row.driver.label).length * 10;
      const candidates = [-10, 16, -28, 34, -46, 52, -64, 70, -82, 88, -100, 106].flatMap((dy) =>
        [9, -width - 9].map((dx) => ({
          left: Math.max(70, Math.min(1030 - width, row.x + dx)),
          top: Math.max(88, Math.min(407, row.y + dy - 10)),
          width,
        })),
      );
      const box =
        candidates.find((b) =>
          boxes.every(
            (o) =>
              b.left + b.width + 4 < o.left ||
              o.left + o.width + 4 < b.left ||
              b.top + 16 < o.top ||
              o.top + 16 < b.top,
          ),
        ) || candidates[0];
      boxes.push(box);
      return { ...row, labelX: box.left, labelY: box.top + 10 };
    });
  return { domain, points };
}

export function narrativeLines(
  drivers: NarrativeDriver[],
  end: string,
  years: number,
  selected: string,
) {
  const endStamp = Date.parse(end);
  const cutoff = endStamp - (years === 0.25 ? 90 : years * 366) * 86400000;
  return {
    animation: false,
    backgroundColor: 'transparent',
    color: drivers.map((_, i) => colorFor(i)),
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#fff',
      borderColor: '#d9e3ee',
      textStyle: { color: '#17334d' },
      confine: true,
      enterable: true,
      extraCssText: 'max-height:260px;overflow-y:auto;',
      formatter: (params: unknown) => {
        const items = (Array.isArray(params) ? params : []) as Array<{
          seriesName: string;
          value: [string, number | null];
        }>;
        const escape = (text: string) =>
          String(text).replace(
            /[&<>"']/g,
            (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!),
          );
        const label = drivers.find((d) => d.id === selected)?.label;
        const visible = items.filter(
          (p) => (!label || p.seriesName === label) && p.value?.[1] != null,
        );
        return (
          `<b>${escape(String(items[0]?.value?.[0] || '').slice(0, 10))}</b><br>` +
          visible
            .map((p) => `${escape(p.seriesName)} ${Number(p.value[1]).toFixed(2)} σ`)
            .join('<br>')
        );
      },
    },
    legend: { show: false },
    grid: { left: 62, right: 22, top: 24, bottom: 75 },
    xAxis: { type: 'time', axisLabel: { color: '#60758f' }, splitLine: { show: false } },
    yAxis: {
      type: 'value',
      scale: true,
      name: '叙事强度（σ）',
      nameTextStyle: { color: '#60758f' },
      axisLabel: { color: '#60758f' },
      splitLine: { lineStyle: { color: '#e2e8f0', type: 'dashed' } },
    },
    dataZoom: [
      { type: 'inside', filterMode: 'empty' },
      {
        type: 'slider',
        height: 22,
        bottom: 12,
        borderColor: '#d9e3ee',
        backgroundColor: '#f5f8fc',
        fillerColor: 'rgba(29, 78, 216, 0.10)',
        dataBackground: { lineStyle: { color: '#8fb0ed' }, areaStyle: { color: '#dce8ff' } },
        selectedDataBackground: {
          lineStyle: { color: '#5684ce' },
          areaStyle: { color: '#bdd2fa' },
        },
        handleStyle: { color: '#5684ce', borderColor: '#5684ce' },
        textStyle: { color: '#60758f' },
      },
    ],
    series: drivers.map((driver, index) => ({
      name: driver.label,
      type: 'line',
      showSymbol: false,
      connectNulls: false,
      lineStyle: {
        width: selected === driver.id ? 2.5 : 1.2,
        opacity: !selected || selected === driver.id ? 1 : 0.13,
      },
      itemStyle: { color: colorFor(index) },
      data: driver.history
        .filter((p) => p.date <= end && Date.parse(p.date) >= cutoff)
        .flatMap((p, i, all) => {
          const row = [p.date, p.score];
          return i > 0 && Date.parse(p.date) - Date.parse(all[i - 1].date) > 7 * 86400000
            ? [[new Date(Date.parse(p.date) - 1).toISOString(), null], row]
            : [row];
        }),
    })),
  };
}
