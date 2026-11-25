import type { IndexValuationChart } from '@/api/equityObservatory';
import { finiteValue, valuationStats, valuationWindow } from './indexValuationStats';

export type ValuationMetric = IndexValuationChart['metrics'][number];
export function researchMetric(chart: IndexValuationChart | undefined, key: string) {
  return chart?.metrics.find((m) => m.id === key || (key === 'pe' && m.id === 'pe-trailing'));
}
export function relativeValuation(
  a: ValuationMetric | undefined,
  b: ValuationMetric | undefined,
  years: number,
  asOf: string,
) {
  const right = new Map(
    valuationWindow(b?.history || [], years, asOf).map((p) => [p.date, finiteValue(p.value)]),
  );
  return valuationWindow(a?.history || [], years, asOf)
    .filter((p) => right.has(p.date))
    .map((p) => {
      const x = finiteValue(p.value),
        y = right.get(p.date);
      return { date: p.date, value: x != null && x > 0 && y != null && y > 0 ? x / y : null };
    });
}
export function scenarioReturn(earningsPct: number, targetPe: number, currentPe: number) {
  return [earningsPct, targetPe, currentPe].every(Number.isFinite) &&
    currentPe > 0 &&
    targetPe > 0 &&
    earningsPct >= -100
    ? (((1 + earningsPct / 100) * targetPe) / currentPe - 1) * 100
    : null;
}
export function valuationAnchor(
  chart: IndexValuationChart | undefined,
  asOf: string,
  metricId = 'pe',
) {
  const metric = researchMetric(chart, metricId);
  const last = valuationWindow(metric?.history || [], 0, asOf).at(-1);
  const pe = finiteValue(last?.value);
  const price = finiteValue(
    (metric?.prices || chart?.prices || []).find((p) => p.date === last?.date)?.value,
  );
  return {
    date: last?.date,
    pe: pe != null && pe > 0 ? pe : null,
    price: price != null && price > 0 ? price : null,
    metric,
  };
}
export function researchStats(metric: ValuationMetric | undefined, years: number, asOf: string) {
  return valuationStats(
    metric?.history || [],
    years,
    asOf,
    metric?.id === 'dividend',
    metric?.rankFrequency,
  );
}

export function earningsToOffset(currentPe: number | null, targetPe: number | null) {
  return currentPe != null &&
    targetPe != null &&
    Number.isFinite(currentPe) &&
    Number.isFinite(targetPe) &&
    currentPe > 0 &&
    targetPe > 0
    ? (currentPe / targetPe - 1) * 100
    : null;
}
