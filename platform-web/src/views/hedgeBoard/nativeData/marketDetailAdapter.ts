import type { MacroDashboardSeries, MarketDetailRow } from '@/api/hedgeResearch';

import type {
  MarketTerminalPageConfig,
  TerminalTableGroup,
  TerminalTableRow,
} from './marketTerminal';

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
  return prepareLiveMarketDetail(groups);
}

export function prepareCommodityMarketDetail(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return prepareLiveMarketDetail(groups);
}

export function prepareCryptoMarketDetail(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return prepareLiveMarketDetail(groups);
}

/**
 * Commodity and crypto detail tables are sourced from the market-detail API.
 * Until a row is received, show an explicit unavailable state instead of the
 * design-time sample figures that exist in the terminal catalog.
 */
function prepareLiveMarketDetail(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return cloneGroups(groups).map((group) => ({
    ...group,
    rows: group.rows.map((row) => ({
      ...row,
      dataStatus: 'no_data',
      observationDate: undefined,
      asOf: undefined,
      source: undefined,
      sourceUrl: undefined,
      currency: undefined,
      priceKind: undefined,
      qualityFlags: [],
      spark: [],
      price: UNAVAILABLE,
      d1: UNAVAILABLE,
      ytd: UNAVAILABLE,
      qtd: UNAVAILABLE,
      w1: UNAVAILABLE,
      m1: UNAVAILABLE,
      y1: UNAVAILABLE,
      high: UNAVAILABLE,
      d10: UNAVAILABLE,
      d20: UNAVAILABLE,
      d50: UNAVAILABLE,
      d200: UNAVAILABLE,
      x2050: UNAVAILABLE,
      x50200: UNAVAILABLE,
    })),
  }));
}

// The research catalogue uses stable UI identifiers while the provider uses
// canonical series identifiers. Keep this mapping at the display boundary so
// neither identifier leaks into the other contract.
const LIVE_ROW_ID_BY_CATALOG_ID: Record<string, string> = {
  'gold-xau': 'gold-xau-row',
  'gold-gld': 'gold-gld-row',
  'gold-gdx': 'gold-gdx-row',
  'gold-gdxj': 'gold-gdxj-row',
  'gold-xauusd': 'gold-xau-row',
  'gold-xagusd': 'gold-slv-row',
  'gold-copper': 'gold-copper-row',
  'gold-plat': 'gold-plat-row',
  'gold-pall': 'gold-pall-row',
  'gold-ratio-xauxag': 'gold-ratio-row',
  'gold-bcom': 'gold-bcom-row',
  'gold-spgsci': 'gold-spgsci-row',
  'gold-usoil': 'gold-wti-row',
  'gold-brent': 'gold-brent-row',
  'gold-xng': 'gold-gas-row',
  'crypto-btcusd': 'crypto-btc-row',
  'crypto-ibit': 'crypto-ibit-row',
  'crypto-ethusd': 'crypto-eth-row',
  'crypto-solusd': 'crypto-sol-row',
  'crypto-bnbusd': 'crypto-bnb-row',
  'crypto-xrpusd': 'crypto-xrp-row',
  'crypto-dogeusd': 'crypto-doge-row',
  'crypto-hypeusd': 'crypto-hype-row',
  'crypto-mstr': 'crypto-mstr-row',
  'crypto-crcl': 'crypto-crcl-row',
  'crypto-coin': 'crypto-coin-row',
  'crypto-bmnr': 'crypto-bmnr-row',
  'crypto-hood': 'crypto-hood-row',
  'crypto-usdc': 'crypto-usdc-row',
};

export function mergeTerminalMarket(
  config: MarketTerminalPageConfig,
  remoteRows: MarketDetailRow[],
): MarketTerminalPageConfig {
  const bySymbol = new Map(remoteRows.map((row) => [row.symbol.replace(/^\^/, ''), row]));
  const lookup = (symbol: string) => {
    const row = bySymbol.get(symbol);
    return row && !['error', 'no_data'].includes(row.status) ? row : undefined;
  };
  const cards = (items: NonNullable<MarketTerminalPageConfig['overviewCards']>) =>
    items.map((item) => {
      const row = lookup(item.symbol);
      const change = numeric(row?.change1d);
      return {
        ...item,
        price: closeValue(numeric(row?.close), row?.unit ?? 'price'),
        change: signed(row?.change1d, 'percent'),
        spark: (row?.spark30d ?? []).map(Number).filter(Number.isFinite),
        tone: (change == null || change === 0
          ? 'neutral'
          : change > 0
          ? 'positive'
          : 'negative') as 'neutral' | 'positive' | 'negative',
      };
    });
  return {
    ...config,
    updatedAt: '',
    overviewChip: '',
    detailGroups: mergeLiveMarketDetail(config.detailGroups, remoteRows),
    overviewCards: cards(config.overviewCards ?? []),
    moverCards: cards(config.moverCards ?? []),
    breadthCards: config.breadthCards?.map((item) => {
      const row = remoteRows.find((candidate) => candidate.id === item.id);
      const value = row && !['error', 'no_data'].includes(row.status) ? numeric(row.close) : null;
      return {
        ...item,
        value: value === null ? UNAVAILABLE : `${value.toFixed(1)}%`,
        tag:
          value === null
            ? '暂无数据'
            : `${row?.status === 'stale' ? '旧数据 · ' : ''}${row?.sampleSize}/${
                row?.expectedSampleSize
              } 样本`,
        delta: row?.observationDate ?? UNAVAILABLE,
      };
    }),
    volatilityCards: config.volatilityCards?.map((item) => ({
      ...item,
      value: numeric(lookup(item.title)?.close)?.toFixed(2) ?? UNAVAILABLE,
      badge: lookup(item.title)
        ? `${lookup(item.title)?.status === 'stale' ? '旧数据 · ' : ''}${
            lookup(item.title)?.observationDate ?? '最近观测'
          }`
        : '暂无数据',
      badgeTone: 'neutral',
    })),
    rotationHeatmap: config.rotationHeatmap?.map((item) => {
      const row = lookup(item.symbol);
      return {
        ...item,
        observationDate: row?.observationDate ?? undefined,
        source: row?.source ?? undefined,
        sourceUrl: row?.sourceUrl ?? undefined,
        dataStatus: row?.status ?? 'no_data',
        d1: signed(row?.change1d, 'percent'),
        w1: signed(row?.change1w, 'percent'),
        m1: signed(row?.change1m, 'percent'),
        ytd: signed(row?.changeYtd, 'percent'),
        y1: signed(row?.change1y, 'percent'),
      };
    }),
  };
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
        ...rowMetadata(remote),
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

function rowMetadata(remote: MarketDetailRow) {
  return {
    observationDate: remote.observationDate ?? undefined,
    asOf: remote.asOf ?? undefined,
    source: remote.source,
    sourceUrl: remote.sourceUrl ?? undefined,
    dataStatus: remote.status,
    qualityFlags: remote.qualityFlags ?? [],
    currency: remote.currency ?? undefined,
    priceKind: remote.priceKind ?? 'observation',
  };
}

export function mergeLiveMarketDetail(
  groups: TerminalTableGroup[],
  remoteRows: MarketDetailRow[],
): TerminalTableGroup[] {
  const byId = new Map(remoteRows.map((row) => [row.id, row]));
  return prepareLiveMarketDetail(groups).map((group) => ({
    ...group,
    rows: group.rows.map((row) => {
      const remote = byId.get(LIVE_ROW_ID_BY_CATALOG_ID[row.id] ?? row.id);
      if (!remote || remote.status === 'no_data' || remote.status === 'error') return row;
      if (row.symbol === 'IMOEX' && remote.symbol !== 'IMOEX') return row;
      const spark = (remote.spark90d?.length ? remote.spark90d : remote.spark30d)
        .map(Number)
        .filter(Number.isFinite);
      return {
        ...row,
        ...(remote.qualityFlags?.includes('continuous_futures_not_spot')
          ? { name: remote.name, symbol: remote.symbol }
          : {}),
        ...rowMetadata(remote),
        ...Object.fromEntries(
          ['d10', 'd20', 'd50', 'd200', 'x2050', 'x50200'].map((key) => [
            key,
            remote.signals?.[key as keyof NonNullable<MarketDetailRow['signals']>] ?? UNAVAILABLE,
          ]),
        ),
        spark,
        price: closeValue(numeric(remote.close), remote.unit),
        d1: signed(remote.change1d, remote.changeUnit, remote.unit),
        w1: signed(remote.change1w, remote.changeUnit, remote.unit),
        m1: signed(remote.change1m, remote.changeUnit, remote.unit),
        qtd: signed(remote.changeQtd, remote.changeUnit, remote.unit),
        ytd: signed(remote.changeYtd, remote.changeUnit, remote.unit),
        y1: signed(remote.change1y, remote.changeUnit, remote.unit),
        high: signed(remote.distance52wHigh, 'percent'),
      };
    }),
  }));
}
