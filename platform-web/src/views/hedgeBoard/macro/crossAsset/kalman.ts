import { atr, type Bar } from './engine';
// © BackQuant. TypeScript adaptation of supplied Pine v5 indicators. MPL-2.0.
export const KALMAN_OVERLAYS = ['price', 'hull'] as const;
export type KalmanOverlay = (typeof KALMAN_OVERLAYS)[number];
export const KALMAN_NAMES: Record<KalmanOverlay, string> = {
  price: 'Kalman Price Filter',
  hull: 'Kalman Hull Supertrend',
};
export const HULL_ATR_PERIOD = 12;
type Trend = -1 | 0 | 1;
export type KalmanPoint = { value: number | null; trend: Trend; signal?: -1 | 1 };
const PROCESS_NOISE = 0.01,
  MEASUREMENT_NOISE = 3;
function kalman(initial: number) {
  let estimate = initial,
    covariance = 1;
  return (price: number, noise = MEASUREMENT_NOISE) => {
    const predicted = covariance + PROCESS_NOISE,
      gain = predicted / (predicted + noise);
    estimate += gain * (price - estimate);
    covariance = (1 - gain) * predicted;
    return estimate;
  };
}
export function kalmanPrice(bars: Bar[]): KalmanPoint[] {
  if (!bars.length) return [];
  const update = kalman(bars[0].c);
  let previous: number | undefined,
    trend: Trend = 0;
  return bars.map((bar) => {
    const value = update(bar.c);
    if (previous !== undefined) {
      if (value > previous) trend = 1;
      if (value < previous) trend = -1;
    }
    previous = value;
    return { value, trend };
  });
}
export function kalmanHullSupertrend(bars: Bar[]): KalmanPoint[] {
  if (!bars.length) return [];
  const update = kalman(bars[0].c),
    volatility = atr(bars, HULL_ATR_PERIOD),
    factor = 1.7;
  let upper = 0,
    lower = 0,
    direction: -1 | 1 = 1,
    trend: Trend = 0;
  return bars.map((bar, i) => {
    update(bar.c);
    const half = update(bar.c, MEASUREMENT_NOISE / 2),
      full = update(bar.c),
      baseline = update(2 * half - full, Math.round(Math.sqrt(MEASUREMENT_NOISE))),
      width = volatility[i];
    if (width === null) return { value: null, trend };
    const previousClose = bars[i - 1].c,
      nextUpper = baseline + factor * width,
      nextLower = baseline - factor * width,
      previousDirection = direction,
      wasUpper = previousDirection === 1 || upper === lower;
    upper = nextUpper < upper || previousClose > upper ? nextUpper : upper;
    lower = nextLower > lower || previousClose < lower ? nextLower : lower;
    if (volatility[i - 1] !== null)
      direction = wasUpper ? (bar.c > upper ? -1 : 1) : bar.c < lower ? 1 : -1;
    const signal = direction === previousDirection ? undefined : direction === -1 ? 1 : -1;
    if (signal !== undefined) trend = signal;
    return { value: direction === -1 ? lower : upper, trend, signal };
  });
}
