export type NumericInput = string | number | null | undefined;

export function parseOptionalNumber(value: NumericInput) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatNumber(value: number, digits = 2) {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatSigned(value: number) {
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}`;
}

export function formatNullablePrice(value: NumericInput, digits = 2) {
  const parsed = parseOptionalNumber(value);
  return parsed === null ? '--' : formatNumber(parsed, digits);
}

export function formatNullableSigned(value: NumericInput) {
  const parsed = parseOptionalNumber(value);
  if (parsed === null) return '--';
  return formatSigned(parsed);
}

export function formatNullableRate(value: NumericInput) {
  const parsed = parseOptionalNumber(value);
  if (parsed === null) return '--';
  return `${(parsed * 100).toFixed(4)}%`;
}

export function formatEditableNumber(value: number | null | undefined) {
  if (value === null || value === undefined) return '';
  if (!Number.isFinite(value)) return '';
  return Number.isInteger(value) ? String(value) : String(value);
}

export function parseEditableNumber(value: string) {
  const normalized = value.trim().replace(/[^0-9.-]/g, '');
  if (!normalized || normalized === '-' || normalized === '.' || normalized === '-.') return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function spreadTone(value: NumericInput) {
  const parsed = parseOptionalNumber(value);
  if (parsed === null) return '';
  return parsed <= 0 ? 'green' : 'red';
}
