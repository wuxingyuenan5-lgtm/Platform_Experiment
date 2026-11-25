import type { Security, CapSnapshot } from './model';

export type { CapSnapshot, CapRow } from './model';
export interface AssetScreen {
  sectors: string[];
  industries: string[];
  etfs: string[];
  min: string;
  max: string;
  unit: number;
  includeUnknown: boolean;
  includeStale: boolean;
  keepEtfs: boolean;
  date: string;
}
export const defaultAssetScreen = (): AssetScreen => ({
  sectors: [],
  industries: [],
  etfs: [],
  min: '',
  max: '',
  unit: 1e8,
  includeUnknown: false,
  includeStale: false,
  keepEtfs: false,
  date: '',
});
export function effectiveAssetScreen(value: AssetScreen, kind: string) {
  return kind === 'etf' ? { ...value, min: '', max: '' } : value;
}
export function changeCapUnit(value: AssetScreen, unit: number) {
  const convert = (s: string) =>
    s === '' || !Number.isFinite(Number(s))
      ? s
      : String(Number(((Number(s) * value.unit) / unit).toPrecision(12)));
  return { ...value, unit, min: convert(value.min), max: convert(value.max) };
}
export function capRangeError(f: AssetScreen) {
  if ([f.min, f.max].some((s) => s !== '' && (!Number.isFinite(Number(s)) || Number(s) < 0)))
    return '市值请输入非负数';
  if (f.min !== '' && f.max !== '' && Number(f.min) > Number(f.max))
    return '最低市值不能大于最高市值';
  return '';
}
export function matchesAssetScreen(s: Security, f: AssetScreen, caps: CapSnapshot | null) {
  const bounded = f.min !== '' || f.max !== '';
  if (capRangeError(f)) return false;
  if (s.kind === 'etf')
    return (!f.etfs.length || f.etfs.includes(s.category)) && (!bounded || f.keepEtfs);
  if (
    (f.sectors.length && !f.sectors.includes(s.sector)) ||
    (f.industries.length && !f.industries.includes(s.category))
  )
    return false;
  if (!bounded) return true;
  const cap = caps?.rows[s.symbol],
    valid = !!cap && cap.currency === 'USD' && Number.isFinite(cap.value) && cap.value > 0;
  if (!valid) return f.includeUnknown;
  if (cap!.date !== caps?.date && !f.includeStale) return false;
  return (
    (f.min === '' || cap!.value >= Number(f.min) * f.unit) &&
    (f.max === '' || cap!.value <= Number(f.max) * f.unit)
  );
}
export function capLabel(s: Security, caps: CapSnapshot | null) {
  if (s.kind !== 'stock') return '';
  const cap = caps?.rows[s.symbol];
  if (!cap || cap.currency !== 'USD' || !Number.isFinite(cap.value) || cap.value <= 0)
    return '市值待采集';
  const label =
    cap.value >= 1e12
      ? `$${(cap.value / 1e12).toFixed(2)}T`
      : cap.value >= 1e9
      ? `$${(cap.value / 1e9).toFixed(2)}B`
      : `$${(cap.value / 1e6).toFixed(1)}M`;
  return `${label} · ${cap.date}${cap.date !== caps?.date ? ' 旧值' : ''}`;
}
