import type { EtfRow } from '@/api/etfTracking';

function growth(current: unknown, previous: unknown) {
  const a = Number(current),
    b = Number(previous);
  return Number.isFinite(a) && Number.isFinite(b) && a > 0 && b > 0 ? a / b - 1 : null;
}

export function etfLeadLag(rows: EtfRow[], sessions: string[], start: string, end: string) {
  const byDate = new Map(rows.map((row) => [row.date, row]));
  const changes = sessions.map((day, i) => {
    const row = byDate.get(day),
      prev = byDate.get(sessions[i - 1]);
    return {
      day,
      units:
        row && prev && row.share_basis === prev.share_basis
          ? growth(
              row.native_units_yi ?? row.qfq_total_units_yi,
              prev.native_units_yi ?? prev.qfq_total_units_yi,
            )
          : null,
      price: growth(row?.etf_qfq_close, prev?.etf_qfq_close),
    };
  });
  return [-5, -3, -1, 0, 1, 3, 5].map((lag) => {
    const pairs: Array<[number, number]> = [];
    changes.forEach((point, i) => {
      const other = changes[i + lag];
      if (
        point.day >= start &&
        point.day <= end &&
        other &&
        other.day >= start &&
        other.day <= end &&
        point.units != null &&
        other.price != null
      )
        pairs.push([point.units, other.price]);
    });
    const n = pairs.length;
    let correlation: number | null = null;
    if (n >= 20) {
      const x = pairs.reduce((sum, pair) => sum + pair[0], 0) / n;
      const y = pairs.reduce((sum, pair) => sum + pair[1], 0) / n;
      let xx = 0,
        yy = 0,
        xy = 0;
      for (const [a, b] of pairs) {
        xx += (a - x) ** 2;
        yy += (b - y) ** 2;
        xy += (a - x) * (b - y);
      }
      if (
        xx > 0 &&
        yy > 0 &&
        pairs.some(([a]) => a !== pairs[0][0]) &&
        pairs.some(([, b]) => b !== pairs[0][1])
      )
        correlation = xy / Math.sqrt(xx * yy);
    }
    return { lag, n, correlation };
  });
}
