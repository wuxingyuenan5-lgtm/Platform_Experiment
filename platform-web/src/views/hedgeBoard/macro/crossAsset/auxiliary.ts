import { ema, type Bar, type Frame } from './engine';

export const AUXILIARIES = ['macd', 'rsi', 'volume', 'amount'] as const;
export type Auxiliary = (typeof AUXILIARIES)[number];
export const AUXILIARY_NAMES: Record<Auxiliary, string> = {
  macd: 'MACD',
  rsi: 'RSI',
  volume: '成交量',
  amount: '成交额（估算）',
};
export function rsi(c: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = c.map(() => null);
  let gain = 0,
    loss = 0;
  for (let i = 1; i < c.length; i++) {
    const d = c[i] - c[i - 1],
      up = Math.max(0, d),
      down = Math.max(0, -d);
    if (i <= period) {
      gain += up / period;
      loss += down / period;
    } else {
      gain = (gain * (period - 1) + up) / period;
      loss = (loss * (period - 1) + down) / period;
    }
    if (i >= period) out[i] = gain + loss === 0 ? 50 : (100 * gain) / (gain + loss);
  }
  return out;
}
export function computeAuxiliary(bars: Bar[]) {
  const closes = bars.map((b) => b.c),
    fast = ema(closes, 12),
    slow = ema(closes, 26),
    difference = fast.map((v, i) => v - slow[i]),
    signal = ema(difference, 9),
    dif = difference.map((v, i) => (i >= 59 ? v : null)),
    dea = signal.map((v, i) => (i >= 59 ? v : null)),
    histogram = difference.map((v, i) => (i >= 59 ? v - signal[i] : null)),
    rsiValues = rsi(closes),
    macdSource = bars.map(() => '同源K线计算'),
    rsiSource = bars.map(() => '同源K线计算'),
    amountSource = bars.map(() => '周期收盘价 × 成交量');
  bars.forEach((b, i) => {
    const n = b.native;
    if (n?.source !== 'NashNova') return;
    const m = n.macd;
    if (
      m &&
      [m.dif, m.dea, m.histogram].every(Number.isFinite) &&
      Math.abs(m.dif - m.dea - m.histogram) <= 0.003
    ) {
      dif[i] = m.dif;
      dea[i] = m.dea;
      histogram[i] = m.histogram;
      macdSource[i] = 'NashNova 原生';
    }
    if (typeof n.rsi === 'number' && Number.isFinite(n.rsi) && n.rsi >= 0 && n.rsi <= 100) {
      rsiValues[i] = n.rsi;
      rsiSource[i] = 'NashNova 原生';
    }
  });
  const volume = bars.map((b) => (Number.isFinite(b.v) && b.v >= 0 ? b.v : null)),
    amount = bars.map((b, i) => {
      if (
        b.native?.source === 'NashNova' &&
        typeof b.native.estimatedAmount === 'number' &&
        Number.isFinite(b.native.estimatedAmount) &&
        b.native.estimatedAmount >= 0
      ) {
        amountSource[i] = 'NashNova amount · 估算口径';
        return b.native.estimatedAmount;
      }
      const value = volume[i] == null ? NaN : b.c * volume[i];
      return Number.isFinite(value) && value >= 0 ? value : null;
    });
  return {
    dif,
    dea,
    histogram,
    rsi: rsiValues,
    volume,
    amount,
    macdSource,
    rsiSource,
    amountSource,
  };
}
export function auxiliaryAvailability(bars: Bar[], frame: Frame): Record<Auxiliary, string | null> {
  const short = frame === 'M' && bars.length < 60,
    last = bars.at(-1)?.native;
  return {
    macd: short
      ? `月线历史不足60根（当前${bars.length}根），暂不显示`
      : bars.length < 60 && !last?.macd
      ? `历史不足60根（当前${bars.length}根），暂不显示`
      : null,
    rsi: short
      ? `月线历史不足60根（当前${bars.length}根），暂不显示`
      : bars.length < 15 && last?.rsi == null
      ? `历史不足15根（当前${bars.length}根），暂不显示`
      : null,
    volume: null,
    amount: null,
  };
}
const compact = new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 2 });
export const formatActivity = (value: number) => compact.format(value);
