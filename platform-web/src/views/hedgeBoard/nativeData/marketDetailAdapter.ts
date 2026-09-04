import type { MacroDashboardSeries, MarketDetailRow } from '@/api/hedgeResearch';

import type { TerminalTableGroup, TerminalTableRow } from './marketTerminal';

const UNAVAILABLE = '—';

function cloneGroups(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return groups.map((group) => ({ ...group, rows: group.rows.map((row) => ({ ...row })) }));
}

function numeric(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function signed(
  value: string | number | null | undefined,
  unit: MarketDetailRow['changeUnit'],
  valueUnit?: string,
) {
  const parsed = numeric(value);
  if (parsed === null) return UNAVAILABLE;
  const sign = parsed > 0 ? '+' : '';
  const suffix =
    unit === 'basis_points'
      ? 'bp'
      : unit === 'percent'
      ? '%'
      : valueUnit === 'usd_million'
      ? 'M'
      : valueUnit === 'usd_billion'
      ? 'B'
      : '';
  return `${sign}${parsed.toFixed(unit === 'basis_points' ? 1 : 2)}${suffix}`;
}

function closeValue(value: number | null, unit: string): string {
  if (value === null) return UNAVAILABLE;
  if (unit === 'percent') return `${value.toFixed(2)}%`;
  if (unit === 'usd_million') return `$${(value / 1_000_000).toFixed(2)}T`;
  if (unit === 'usd_billion' && Math.abs(value) >= 1_000) return `$${(value / 1_000).toFixed(2)}T`;
  if (unit === 'usd_billion') return `$${value.toFixed(2)}B`;
  if (unit === 'price') return `$${value.toFixed(2)}`;
  return value.toFixed(2);
}

export function prepareMacroMarketDetail(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return cloneGroups(groups);
}

export function prepareCommodityMarketDetail(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return cloneGroups(groups).map((group) => ({
    ...group,
    rows: group.rows.map((row) => ({ ...row, spark: [] })),
  }));
}

export function prepareCryptoMarketDetail(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return cloneGroups(groups).map((group) => ({
    ...group,
    rows: group.rows.map((row) => ({ ...row, spark: [] })),
  }));
}

function cryptoChange(points: Array<{ date: string; value: number }>, days: number): string {
  if (points.length < 2) return UNAVAILABLE;
  const latest = points[points.length - 1];
  const cutoff = Date.parse(latest.date) - days * 86_400_000;
  const previous = [...points].reverse().find((point) => Date.parse(point.date) <= cutoff);
  if (!previous || previous.value === 0) return UNAVAILABLE;
  return signed((latest.value / previous.value - 1) * 100, 'percent');
}

function cryptoChangeSince(points: Array<{ date: string; value: number }>, cutoff: number): string {
  const latest = points[points.length - 1];
  const baseline = points.find((point) => Date.parse(point.date) >= cutoff);
  if (!baseline || baseline.value === 0) return UNAVAILABLE;
  return signed((latest.value / baseline.value - 1) * 100, 'percent');
}

export function mergeCryptoMarketDetail(
  groups: TerminalTableGroup[],
  series: MacroDashboardSeries[],
): TerminalTableGroup[] {
  const rowBySeries = new Map([
    ['binance_btc_spot', 'crypto-btc-row'],
    ['binance_eth_spot', 'crypto-eth-row'],
  ]);
  const byRow = new Map(
    series.flatMap((item) => {
      const rowId = rowBySeries.get(item.seriesId);
      if (!rowId || item.status === 'error' || item.status === 'no_data') return [];
      return [[rowId, item] as const];
    }),
  );
  return prepareCryptoMarketDetail(groups).map((group) => ({
    ...group,
    rows: group.rows.map((row) => {
      const remote = byRow.get(row.id);
      if (!remote) return row;
      const points = remote.observations
        .map((point) => ({ date: point.date, value: Number(point.value) }))
        .filter((point) => Number.isFinite(point.value));
      if (!points.length) return row;
      const latest = points[points.length - 1].value;
      const latestDate = new Date(`${points[points.length - 1].date}T00:00:00Z`);
      const yearStart = Date.UTC(latestDate.getUTCFullYear(), 0, 1);
      const quarterStart = Date.UTC(
        latestDate.getUTCFullYear(),
        Math.floor(latestDate.getUTCMonth() / 3) * 3,
        1,
      );
      const trailingYear = points.filter(
        (point) =>
          Date.parse(point.date) >= Date.parse(points[points.length - 1].date) - 366 * 86_400_000,
      );
      const high = Math.max(...trailingYear.map((point) => point.value));
      return {
        ...row,
        price: closeValue(latest, 'price'),
        d1: cryptoChange(points, 1),
        w1: cryptoChange(points, 7),
        m1: cryptoChange(points, 30),
        qtd: cryptoChangeSince(points, quarterStart),
        ytd: cryptoChangeSince(points, yearStart),
        y1: cryptoChange(points, 365),
        high: signed((latest / high - 1) * 100, 'percent'),
        spark: points.slice(-90).map((point) => point.value),
      };
    }),
  }));
}

export function mergeMacroMarketDetail(
  groups: TerminalTableGroup[],
  remoteRows: MarketDetailRow[],
): TerminalTableGroup[] {
  const byId = new Map(remoteRows.map((row) => [row.id, row]));
  return prepareMacroMarketDetail(groups).map((group) => ({
    ...group,
    rows: group.rows.map((row) => {
      const remote = byId.get(row.id);
      if (!remote || remote.status === 'no_data' || remote.status === 'error') return row;
      const close = numeric(remote.close);
      const next: TerminalTableRow = {
        ...row,
        name: remote.name,
        symbol: remote.symbol,
        spark: (remote.spark90d?.length ? remote.spark90d : remote.spark30d)
          .map(Number)
          .filter(Number.isFinite),
        price: closeValue(close, remote.unit),
        d1: signed(remote.change1d, remote.changeUnit, remote.unit),
        ytd: signed(remote.changeYtd, remote.changeUnit, remote.unit),
        qtd: signed(remote.changeQtd, remote.changeUnit, remote.unit),
        w1: signed(remote.change1w, remote.changeUnit, remote.unit),
        m1: signed(remote.change1m, remote.changeUnit, remote.unit),
        y1: signed(remote.change1y, remote.changeUnit, remote.unit),
        high: signed(remote.distance52wHigh, 'percent'),
      };
      return next;
    }),
  }));
}

export function mergeLiveMarketDetail(
  groups: TerminalTableGroup[],
  remoteRows: MarketDetailRow[],
): TerminalTableGroup[] {
  const byId = new Map(remoteRows.map((row) => [row.id, row]));
  return groups.map((group) => ({
    ...group,
    rows: group.rows.map((row) => {
      const remote = byId.get(row.id);
      const spark = remote
        ? (remote.spark90d?.length ? remote.spark90d : remote.spark30d)
            .map(Number)
            .filter(Number.isFinite)
        : [];
      return { ...row, spark };
    }),
  }));
}
