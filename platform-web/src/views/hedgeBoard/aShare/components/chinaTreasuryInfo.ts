import Decimal from 'decimal.js';
import type { MacroDashboardSeries } from '@/api/hedgeResearch';

function decimal(value: unknown): Decimal | null {
  if (value == null || value === '') return null;
  try {
    const result = new Decimal(String(value));
    return result.isFinite() ? result : null;
  } catch {
    return null;
  }
}

export function chinaTreasuryInfoCards(series: MacroDashboardSeries[], failed = false) {
  return [10, 30].map((years) => {
    const row = series.find((item) => item.seriesId === `cn_treasury_${years}y`);
    const label = `中国${years}Y国债`;
    const date = row?.observationDate || row?.asOf?.slice(0, 10);
    const value = row?.unit === 'percent' ? decimal(row.latestValue) : null;
    const previous = [...(row?.observations || [])]
      .filter((point) => date && point.date < date && decimal(point.value) != null)
      .sort((a, b) => a.date.localeCompare(b.date))
      .at(-1);
    const bp =
      value != null && previous
        ? value.minus(decimal(previous.value)!).times(100).toDecimalPlaces(2)
        : null;
    const change = bp == null ? '—BP' : `${bp.gt(0) ? '+' : ''}${bp.toString()}BP`;
    const stale =
      failed || row?.isStale || ['stale', 'error', 'degraded'].includes(row?.status || '');
    const source = row?.source === 'chinabond' ? '中债' : row?.source;
    return {
      label,
      yieldLabel: value == null ? '—' : `${value.toFixed(2)}%`,
      changeLabel: value == null ? '' : change,
      note:
        date && source
          ? `${date} · ${source}${stale ? ' · 待更新' : ''}`
          : failed
          ? '暂不可用'
          : '暂无数据',
      title: row
        ? `${row.source}；数据日期 ${date || '—'}；较上一有效日 ${
            previous?.date || '—'
          } 的变动；1BP = 0.01个百分点`
        : '暂无国债收益率数据',
    };
  });
}
