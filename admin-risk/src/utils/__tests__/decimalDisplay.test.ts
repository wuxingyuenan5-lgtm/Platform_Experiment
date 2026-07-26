import { describe, expect, it } from 'vitest';
import {
  decimalDirection,
  formatDecimalString,
  formatMoneyString,
  formatNullableDecimalString,
  formatRatioPercentString,
  formatSignedMoneyString,
} from '../decimalDisplay';

describe('decimalDisplay', () => {
  it('groups plain decimal strings without Number conversion', () => {
    expect(formatDecimalString('123456789.123456789123456789')).toBe(
      '123,456,789.123456789123456789',
    );
    expect(formatDecimalString('-1000.0001')).toBe('-1,000.0001');
  });

  it('keeps unavailable values distinct from zero', () => {
    expect(formatNullableDecimalString(undefined)).toBe('不可用');
    expect(formatMoneyString(null, 'CNY')).toBe('不可用');
    expect(formatNullableDecimalString('0')).toBe('0');
    expect(formatMoneyString('0', 'CNY')).toBe('0 CNY');
  });

  it('formats signed money without floating point arithmetic', () => {
    expect(formatSignedMoneyString('0.01', 'CNY')).toBe('+0.01 CNY');
    expect(formatSignedMoneyString('-0.01', 'CNY')).toBe('-0.01 CNY');
    expect(formatSignedMoneyString('0.000', 'CNY')).toBe('0.000 CNY');
  });

  it('moves the decimal point exactly when formatting a ratio', () => {
    expect(formatRatioPercentString('1')).toBe('+100%');
    expect(formatRatioPercentString('0.123456789123456789')).toBe(
      '+12.3456789123456789%',
    );
    expect(formatRatioPercentString('-0.0001')).toBe('-0.01%');
    expect(formatRatioPercentString('0')).toBe('0%');
  });

  it('classifies direction from the canonical decimal string', () => {
    expect(decimalDirection('100')).toBe('positive');
    expect(decimalDirection('-0.0001')).toBe('negative');
    expect(decimalDirection('0.000')).toBe('zero');
    expect(decimalDirection(undefined)).toBe('zero');
  });
});
