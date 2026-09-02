import type { MarketDetailRow } from '@/api/hedgeResearch';

import type { TerminalTableGroup, TerminalTableRow } from './marketTerminal';

const UNAVAILABLE = '—';
const ENABLED_MACRO_ROW_IDS = new Set(['macro-us2y', 'macro-us10y', 'macro-us30y']);
const DATA_SIGNAL_KEYS: Array<keyof TerminalTableRow> = [
  'd10',
  'd20',
  'd50',
  'd200',
  'x2050',
  'x50200',
];

function cloneGroups(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return groups.map((group) => ({ ...group, rows: group.rows.map((row) => ({ ...row })) }));
}

function numeric(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function signed(value: string | number | null | undefined, unit: MarketDetailRow['changeUnit']) {
  const parsed = numeric(value);
  if (parsed === null) return UNAVAILABLE;
  const sign = parsed > 0 ? '+' : '';
  const suffix = unit === 'basis_points' ? 'bp' : unit === 'percent' ? '%' : '';
  return `${sign}${parsed.toFixed(unit === 'basis_points' ? 1 : 2)}${suffix}`;
}

function unavailableRow(row: TerminalTableRow): TerminalTableRow {
  const next = {
    ...row,
    spark: [],
    price: UNAVAILABLE,
    d1: UNAVAILABLE,
    ytd: UNAVAILABLE,
    qtd: UNAVAILABLE,
    w1: UNAVAILABLE,
    m1: UNAVAILABLE,
    y1: UNAVAILABLE,
    high: UNAVAILABLE,
  };
  DATA_SIGNAL_KEYS.forEach((key) => (next[key] = UNAVAILABLE as never));
  return next;
}

export function prepareMacroMarketDetail(groups: TerminalTableGroup[]): TerminalTableGroup[] {
  return cloneGroups(groups).map((group) => ({
    ...group,
    rows: group.rows.map((row) => (ENABLED_MACRO_ROW_IDS.has(row.id) ? unavailableRow(row) : row)),
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
        spark: remote.spark30d.map(Number).filter(Number.isFinite),
        price: close === null ? UNAVAILABLE : `${close.toFixed(2)}%`,
        d1: signed(remote.change1d, remote.changeUnit),
        ytd: signed(remote.changeYtd, remote.changeUnit),
        qtd: signed(remote.changeQtd, remote.changeUnit),
        w1: signed(remote.change1w, remote.changeUnit),
        m1: signed(remote.change1m, remote.changeUnit),
        y1: signed(remote.change1y, remote.changeUnit),
        high: signed(remote.distance52wHigh, 'percent'),
      };
      DATA_SIGNAL_KEYS.forEach((key) => (next[key] = UNAVAILABLE as never));
      return next;
    }),
  }));
}
