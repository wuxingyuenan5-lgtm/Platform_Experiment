export type DecimalDirection = 'positive' | 'negative' | 'zero';

interface DecimalParts {
  negative: boolean;
  integer: string;
  fraction: string;
}

function splitDecimal(value: string): DecimalParts {
  const negative = value.startsWith('-');
  const unsigned = negative ? value.slice(1) : value;
  const [integer = '0', fraction = ''] = unsigned.split('.');
  return { negative, integer: integer || '0', fraction };
}

function groupInteger(value: string): string {
  return value.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function shiftDecimalRight(value: string, places: number): string {
  const { negative, integer, fraction } = splitDecimal(value);
  const targetPosition = integer.length + places;
  let expanded = `${integer}${fraction}`;
  if (targetPosition > expanded.length) {
    expanded = expanded.padEnd(targetPosition, '0');
  }
  const whole = expanded.slice(0, targetPosition) || '0';
  const decimal = expanded.slice(targetPosition).replace(/0+$/, '');
  const normalizedWhole = whole.replace(/^0+(?=\d)/, '') || '0';
  const isZero = /^0+$/.test(normalizedWhole) && (!decimal || /^0+$/.test(decimal));
  return `${negative && !isZero ? '-' : ''}${normalizedWhole}${decimal ? `.${decimal}` : ''}`;
}

export function formatDecimalString(value: string): string {
  const { negative, integer, fraction } = splitDecimal(value);
  return `${negative ? '-' : ''}${groupInteger(integer)}${fraction ? `.${fraction}` : ''}`;
}

export function formatNullableDecimalString(value?: string | null): string {
  return value === undefined || value === null ? '不可用' : formatDecimalString(value);
}

export function formatMoneyString(value: string | undefined | null, currency: string): string {
  return value === undefined || value === null
    ? '不可用'
    : `${formatDecimalString(value)} ${currency}`;
}

export function formatSignedMoneyString(
  value: string | undefined | null,
  currency: string,
): string {
  if (value === undefined || value === null) return '不可用';
  const prefix = value.startsWith('-') || decimalDirection(value) === 'zero' ? '' : '+';
  return `${prefix}${formatDecimalString(value)} ${currency}`;
}

export function formatRatioPercentString(value?: string | null): string {
  if (value === undefined || value === null) return '不可用';
  const percent = shiftDecimalRight(value, 2);
  const prefix = percent.startsWith('-') || decimalDirection(percent) === 'zero' ? '' : '+';
  return `${prefix}${formatDecimalString(percent)}%`;
}

export function decimalDirection(value?: string | null): DecimalDirection {
  if (!value) return 'zero';
  const unsigned = value.startsWith('-') ? value.slice(1) : value;
  const isZero = /^0+(?:\.0+)?$/.test(unsigned);
  if (isZero) return 'zero';
  return value.startsWith('-') ? 'negative' : 'positive';
}
