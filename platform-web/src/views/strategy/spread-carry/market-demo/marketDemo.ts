// Deterministic synthetic research data. No API, account state or execution side effects.
export type Session = '亚洲' | '欧洲' | '美国';
export type Scenario = 'dislocation' | 'liquidity' | 'closed' | 'repricing';
export type Direction = 'long' | 'short';
export interface Observation {
  time: number;
  mid: number;
  session: Session;
  width?: number;
}
export const SNAPSHOT = Date.parse('2026-11-05T21:30:00+08:00');
export const HOUR = 3_600_000;
export const sessionAt = (time: number): Session => {
  const hour = new Date(time + 8 * HOUR).getUTCHours();
  return hour >= 8 && hour < 16 ? '亚洲' : hour >= 16 && hour < 21 ? '欧洲' : '美国';
};
export function quantile(values: number[], p: number): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const index = (sorted.length - 1) * p;
  const lo = Math.floor(index);
  return sorted[lo] + (sorted[Math.ceil(index)] - sorted[lo]) * (index - lo);
}
export function makeHistory(): Observation[] {
  const rows: Observation[] = [];
  let seed = 73,
    residual = 0;
  const random = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  for (let i = 90 * 48; i >= 1; i--) {
    const time = SNAPSHOT - (i * HOUR) / 2;
    const date = new Date(time + 8 * HOUR);
    // Illustrative shared sessions only; this is not a venue trading calendar.
    if ([0, 6].includes(date.getUTCDay()) || date.getUTCHours() === 6) continue;
    const session = sessionAt(time);
    residual = residual * 0.88 + (random() - 0.5) * 2.4;
    if (random() < 0.024) residual += (random() > 0.5 ? 1 : -1) * (4 + random() * 5);
    rows.push({
      time,
      session,
      mid: { 亚洲: 1.4, 欧洲: 2.2, 美国: 2.8 }[session] + residual,
      width: 0.8 + Math.abs(residual) * 0.08 + (session === '美国' ? 0.25 : 0),
    });
  }
  return rows;
}
export const HISTORY = makeHistory();
export const SCENARIOS: Record<
  Scenario,
  { label: string; mid: number; width: number; valid: boolean; reason: string; basis: number[] }
> = {
  dislocation: {
    label: '短时偏离',
    mid: 9.2,
    width: 1.1,
    valid: true,
    reason: '永续溢价扩大，先核对回归时间与成本余量',
    basis: [6.4, 1.6, 0.4, 0.8],
  },
  liquidity: {
    label: '流动性收缩',
    mid: 9.2,
    width: 6.8,
    valid: true,
    reason: '同样的中间价偏离，被两腿点差大幅侵蚀',
    basis: [6.4, 1.6, 0.4, 0.8],
  },
  closed: {
    label: 'CFD 休市',
    mid: 12.6,
    width: 1.1,
    valid: false,
    reason: 'CFD 为停滞报价，暂停当前价差与净空间判断',
    basis: [],
  },
  repricing: {
    label: '代币重估',
    mid: 9.2,
    width: 1.1,
    valid: true,
    reason: '偏离主要来自代币基差，旧中枢不能直接作为回归目标',
    basis: [0.8, 7.2, 0.4, 0.8],
  },
};
export function distribution(rows: Observation[]) {
  const values = rows.map((r) => r.mid);
  const median = quantile(values, 0.5);
  const mad =
    median === null
      ? null
      : quantile(
          values.map((v) => Math.abs(v - median)),
          0.5,
        );
  return {
    median,
    scale: mad === null ? null : mad * 1.4826,
    p10: quantile(values, 0.1),
    p90: quantile(values, 0.9),
    n: rows.length,
  };
}
export interface Episode {
  time: number;
  direction: Direction;
  session: Session;
  entry: number;
  target: number;
  hours: number;
  mae: number;
  status: 'reverted' | 'timeout' | 'censored';
}
export function study(rows: Observation[]) {
  // Fit on earlier observations only. Freeze session centres and thresholds for evaluation.
  const split = Math.floor(rows.length * 0.6);
  const training = rows.slice(0, split),
    evaluation = rows.slice(split);
  const centres = Object.fromEntries(
    (['亚洲', '欧洲', '美国'] as Session[]).map((s) => [
      s,
      distribution(training.filter((r) => r.session === s)),
    ]),
  ) as Record<Session, ReturnType<typeof distribution>>;
  const events: Episode[] = [];
  let active: Episode | null = null,
    armed = true;
  for (let i = 0; i < evaluation.length; i++) {
    const row = evaluation[i],
      model = centres[row.session];
    if (active) {
      const previous = evaluation[i - 1];
      if (row.time - previous.time > HOUR / 2) {
        active.status = 'censored';
        events.push(active);
        active = null;
        armed = false;
      } else {
        active.hours = (row.time - active.time) / HOUR;
        const sign = active.direction === 'long' ? 1 : -1;
        active.mae = Math.max(active.mae, -sign * (row.mid - active.entry));
        if (sign * (row.mid - active.target) >= 0) {
          active.status = 'reverted';
          events.push(active);
          active = null;
        } else if (active.hours >= 24) {
          active.status = 'timeout';
          events.push(active);
          active = null;
        }
      }
      continue;
    }
    if (model.n < 20 || model.median === null || !model.scale || model.scale < 0.05) continue;
    const z = (row.mid - model.median) / model.scale;
    if (Math.abs(z) < 0.5) armed = true;
    if (armed && Math.abs(z) >= 2) {
      active = {
        time: row.time,
        direction: z > 0 ? 'short' : 'long',
        session: row.session,
        entry: row.mid,
        target: model.median,
        hours: 0,
        mae: 0,
        status: 'censored',
      };
      armed = false;
    }
  }
  if (active) events.push(active);
  return { training, evaluation, centres, events };
}
export function eventSummary(events: Episode[]) {
  const complete = events.filter((e) => e.status !== 'censored');
  const reverted = complete.filter((e) => e.status === 'reverted');
  return {
    n: events.length,
    complete: complete.length,
    reverted: reverted.length,
    censored: events.length - complete.length,
    rate: complete.length ? (reverted.length / complete.length) * 100 : null,
    hours: quantile(
      reverted.map((e) => e.hours),
      0.5,
    ),
    mae: quantile(
      complete.map((e) => e.mae),
      0.9,
    ),
  };
}
export interface CostInput {
  direction: Direction;
  mid: number;
  width: number;
  target: number;
  quantity: number;
  hours: number;
  feeBps: number;
  fundingBps: number;
  swap: number;
  buffer: number;
}
export function economics(input: CostInput) {
  const d = input.direction === 'long' ? 1 : -1;
  const entry = input.mid + (d * input.width) / 2;
  const exit = input.target - (d * input.width) / 2;
  const price = d * (exit - entry);
  // Hypothetical event timetable relative to the demo snapshot; not live contract rules.
  const events: { label: string; hour: number; cash: number }[] = [];
  for (const hour of [2.5, 10.5, 18.5, 26.5, 34.5, 42.5, 50.5, 58.5, 66.5]) {
    if (hour <= input.hours)
      events.push({ label: '资金费', hour, cash: (-d * 4000 * input.fundingBps) / 10000 });
  }
  for (const [hour, multiplier] of [
    [8.5, 1],
    [32.5, 3],
    [56.5, 1],
  ]) {
    if (hour <= input.hours)
      events.push({ label: `库存费 ×${multiplier}`, hour, cash: input.swap * multiplier });
  }
  events.sort((a, b) => a.hour - b.hour);
  const funding = events.filter((e) => e.label === '资金费').reduce((a, e) => a + e.cash, 0);
  const swap = events.filter((e) => e.label !== '资金费').reduce((a, e) => a + e.cash, 0);
  const fees = ((4000 * input.feeBps) / 10000) * 2 + 0.06;
  const net = price + funding + swap - fees - input.buffer;
  return {
    entry,
    exit,
    price,
    funding,
    swap,
    fees,
    net,
    total: net * input.quantity,
    events,
    breakEven: input.width + fees + input.buffer - funding - swap,
  };
}
