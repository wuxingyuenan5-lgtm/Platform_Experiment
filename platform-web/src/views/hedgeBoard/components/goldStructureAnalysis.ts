import type { GoldFactorRow } from '../charts/goldFactorOptions';
import { factorNames } from '../charts/goldFactorOptions';

export function factorAttribution(rows: GoldFactorRow[]) {
  const keys = ['mid', 'tips', 'yieldFactor', 'premium'] as const;
  const valid = [...rows]
    .sort((a, b) => a.date.localeCompare(b.date))
    .filter(
      (r) =>
        r.available &&
        (['gold', ...keys] as const).every(
          (k) => typeof r[k] === 'number' && Number.isFinite(r[k]) && r[k]! > 0,
        ),
    );
  if (valid.length < 2) return null;
  const first = valid[0],
    last = valid[valid.length - 1];
  const parts = keys.map((key) => ({
    name: factorNames[key],
    value: 100 * Math.log(last[key]! / first[key]!),
  }));
  const gold = 100 * Math.log(last.gold / first.gold);
  return {
    first: first.date,
    last: last.date,
    count: valid.length,
    parts,
    gold,
    priceReturn: 100 * (last.gold / first.gold - 1),
    difference: gold - parts.reduce((s, p) => s + p.value, 0),
  };
}
export interface OptionStrike {
  strike: number;
  volume: number;
  openInterest: number;
}
export function optionStructure(calls: OptionStrike[], puts: OptionStrike[]) {
  if (!calls.length || !puts.length) return null;
  for (const side of [calls, puts]) {
    if (
      new Set(side.map((r) => r.strike)).size !== side.length ||
      side.some(
        (r) =>
          !Number.isFinite(r.strike) ||
          r.strike <= 0 ||
          !Number.isSafeInteger(r.volume) ||
          r.volume < 0 ||
          !Number.isSafeInteger(r.openInterest) ||
          r.openInterest < 0,
      )
    )
      return null;
  }
  const call = new Map(calls.map((r) => [r.strike, r])),
    put = new Map(puts.map((r) => [r.strike, r]));
  const rows = [...new Set([...call.keys(), ...put.keys()])]
    .sort((a, b) => a - b)
    .map((strike) => ({
      strike,
      callOi: call.get(strike)?.openInterest ?? null,
      putOi: put.get(strike)?.openInterest ?? null,
      callVolume: call.get(strike)?.volume ?? null,
      putVolume: put.get(strike)?.volume ?? null,
    }));
  const sum = (side: OptionStrike[], key: 'volume' | 'openInterest') =>
    side.reduce((s, r) => s + r[key], 0);
  const callOi = sum(calls, 'openInterest'),
    putOi = sum(puts, 'openInterest');
  return {
    rows,
    callOi,
    putOi,
    callVolume: sum(calls, 'volume'),
    putVolume: sum(puts, 'volume'),
    oiRatio: callOi > 0 ? putOi / callOi : null,
  };
}
