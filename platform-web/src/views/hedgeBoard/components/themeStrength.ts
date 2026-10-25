import type { EquityTheme, EquityValue } from '@/api/equityObservatory';

export type StrengthPeriod = 'change' | 'change_5d' | 'change_20d';
export interface ThemeStrengthRow {
  instrument_id: string;
  code: string;
  name: string;
  industry: string;
  change: number | null;
  change_5d: number | null;
  change_20d: number | null;
}
const ratio = (value: EquityValue | undefined) =>
  value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value) / 100;

export function themeStrengthRows(themes: EquityTheme[]): ThemeStrengthRow[] {
  return themes
    .filter((row) => row.kind !== 'style')
    .map((row) => ({
      instrument_id: row.name,
      code: row.name,
      name: row.name,
      industry: `${row.expected}只成员`,
      change: row.returnPctRankable === true ? ratio(row.medianReturn) : null,
      change_5d: row.return5Rankable === true ? ratio(row.return5) : null,
      change_20d: row.return20Rankable === true ? ratio(row.return20) : null,
    }));
}

export function strengthRanking(rows: ThemeStrengthRow[], field: StrengthPeriod) {
  const sorted = rows
    .filter((r) => r[field] !== null)
    .sort((a, b) => b[field]! - a[field]! || a.name.localeCompare(b.name, 'zh-CN'));
  return { up: sorted.slice(0, 5), down: [...sorted].reverse().slice(0, 5) };
}

export function strengthMatrix(rows: ThemeStrengthRow[]) {
  const valid = rows.filter((r) => r.change !== null && r.change_20d !== null);
  const domain = {
    x: Math.max(0.01, ...valid.map((r) => Math.abs(r.change_20d!))),
    y: Math.max(0.01, ...valid.map((r) => Math.abs(r.change!))),
  };
  const quadrants = { leader: 0, improving: 0, weakening: 0, lagging: 0 };
  const points = valid.map((row) => {
    const positive = row.change! >= 0 && row.change_20d! >= 0;
    const negative = row.change! < 0 && row.change_20d! < 0;
    if (positive) quadrants.leader++;
    else if (negative) quadrants.lagging++;
    else if (row.change! >= 0) quadrants.improving++;
    else quadrants.weakening++;
    return {
      row,
      x: 52 + ((row.change_20d! + domain.x) / (2 * domain.x)) * 896,
      y: 368 - ((row.change! + domain.y) / (2 * domain.y)) * 316,
      radius: 6,
      positive,
      negative,
    };
  });
  const occupied: { left: number; top: number; right: number; bottom: number }[] = [];
  const labeled = [...points]
    .sort((a, b) => a.y - b.y)
    .map((point) => {
      const width = Array.from(point.row.name).reduce(
        (sum, char) => sum + (char.charCodeAt(0) > 127 ? 10 : 6),
        0,
      );
      const offsets = [
        -10,
        ...Array.from({ length: 18 }, (_, i) => [(i + 1) * 18, -(i + 1) * 18 - 10]).flat(),
      ];
      const candidates = offsets.flatMap((offset) =>
        (['start', 'end'] as const).map((anchor) => {
          const left = Math.max(
            58,
            Math.min(942 - width, anchor === 'start' ? point.x + 9 : point.x - 9 - width),
          );
          const top = Math.max(80, Math.min(330, point.y + offset - 10));
          return { left, top, right: left + width, bottom: top + 14, anchor };
        }),
      );
      const overlaps = (box: (typeof candidates)[number]) =>
        occupied.reduce(
          (sum, other) =>
            sum +
            Math.max(0, Math.min(box.right + 3, other.right + 3) - Math.max(box.left, other.left)) *
              Math.max(
                0,
                Math.min(box.bottom + 2, other.bottom + 2) - Math.max(box.top, other.top),
              ),
          0,
        );
      const box =
        candidates.find((candidate) => overlaps(candidate) === 0) ??
        candidates.reduce((best, candidate) =>
          overlaps(candidate) < overlaps(best) ? candidate : best,
        );
      occupied.push(box);
      return {
        ...point,
        labelX: box.anchor === 'start' ? box.left : box.right,
        labelY: box.top + 10,
        labelAnchor: box.anchor,
      };
    });
  return { domain, quadrants, points: labeled };
}
