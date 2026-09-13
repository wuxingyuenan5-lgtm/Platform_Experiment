import type {
  StrategyPnlCalendar,
  StrategyPnlCalendarCell,
  StrategyPnlCalendarMode,
  StrategyPnlCalendarTone,
  StrategyPnlDayPoint,
} from '@/data/sample/strategy';

/**
 * 盈亏日历：把后端逐日读数聚合成日/月两级视图。
 *
 * 只做区间求和与按日复利，不重建口径、不补零：某日 `pnl` 为 null 时不显示 0，
 * 而是在悬浮说明里给出后端判定的原因。切日时区固定 UTC，与后端
 * `dailyPnl[].date` 一致，避免浏览器本地时区把跨夜交易日挪到相邻格。
 */

export interface PnlCalendarCursor {
  year: number;
  /** 1-12；月视图不使用 */
  month: number;
}

const weekdayLabels = ['日', '一', '二', '三', '四', '五', '六'];

const qualityNotes: Record<string, string> = {
  baseline: '序列基线，无前一交易日可比',
  missing_history: '资金流核对未覆盖该区间',
  unclassified_flow: '存在未分类资金流水',
  missing_flow_valuation: '缺少资金流估值，不折算汇率',
  invalid_equity: '权益读数无效',
  invalid_capital: '期间资本非正',
};

const pad = (value: number) => String(value).padStart(2, '0');

function todayUtc(): string {
  const now = new Date();
  return `${now.getUTCFullYear()}-${pad(now.getUTCMonth() + 1)}-${pad(now.getUTCDate())}`;
}

function compact(value: number): string {
  const sign = value > 0 ? '+' : value < 0 ? '-' : '';
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 10_000) return `${sign}${(abs / 1_000).toFixed(2)}K`;
  return `${sign}${abs.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function full(value: number, currency: string): string {
  const sign = value > 0 ? '+' : value < 0 ? '-' : '';
  const body = Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}${body}${currency ? ` ${currency}` : ''}`;
}

function percent(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '--';
  const sign = value > 0 ? '+' : value < 0 ? '-' : '';
  return `${sign}${Math.abs(value).toFixed(2)}%`;
}

function toneOf(value: number | null): StrategyPnlCalendarTone {
  if (value == null || !Number.isFinite(value)) return 'unavailable';
  return value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral';
}

function finite(value: number | null | undefined): number | null {
  if (value == null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function aggregate(points: StrategyPnlDayPoint[]) {
  const hasUnavailable = points.some((point) => finite(point.pnl) === null);
  const valued = points
    .map((point) => ({
      pnl: finite(point.pnl),
      rate: finite(point.rate),
    }))
    .filter((point): point is { pnl: number; rate: number | null } => point.pnl !== null);
  if (!valued.length) return { pnl: null, rate: null, days: 0 };
  const pnl = valued.reduce((sum, point) => sum + point.pnl, 0);
  // 区间收益率按日复利：单日收益率已是「当日盈亏 / 当日实际投入资本」，
  // 相加会放大波动，缺失日不参与也不假设为 0。
  const rated = valued.filter((point) => point.rate !== null);
  const growth = rated.reduce((acc, point) => acc * (1 + (point.rate as number) / 100), 1);
  return {
    pnl,
    rate: rated.length && !hasUnavailable ? (growth - 1) * 100 : null,
    days: valued.length,
  };
}

function blankCell(key: string): StrategyPnlCalendarCell {
  return { key, label: '', amount: '', rateText: '', tone: 'unavailable', title: '' };
}

function dayCell(
  date: string,
  day: number,
  point: StrategyPnlDayPoint | undefined,
  today: string,
): StrategyPnlCalendarCell {
  const pnl = point ? finite(point.pnl) : null;
  const rate = point ? finite(point.rate) : null;
  let title: string;
  if (pnl !== null) {
    title = `${date} · 盈亏 ${full(pnl, '')} · 收益率 ${percent(rate)}`;
    const note = point ? qualityNotes[point.quality] : undefined;
    if (note) title += ` · ${note}`;
  } else if (date > today) {
    title = `${date} · 未到交易日`;
  } else if (point) {
    title = `${date} · ${qualityNotes[point.quality] ?? '暂不可估值'}`;
  } else {
    title = `${date} · 无账户权益读数`;
  }
  return {
    key: date,
    label: String(day),
    amount: pnl === null ? '--' : compact(pnl),
    rateText: pnl === null ? '' : percent(rate),
    tone: toneOf(pnl),
    title,
  };
}

export function buildPnlCalendar(
  points: StrategyPnlDayPoint[],
  currency: string,
  mode: StrategyPnlCalendarMode,
  cursor: PnlCalendarCursor,
): StrategyPnlCalendar {
  const { year, month } = cursor;
  const unit = currency ? `（${currency}）` : '';
  if (mode === 'monthly') {
    const yearPrefix = `${year}-`;
    const yearPoints = points.filter((point) => point.date.startsWith(yearPrefix));
    const { pnl, rate, days } = aggregate(yearPoints);
    const cells: StrategyPnlCalendarCell[] = [];
    for (let index = 1; index <= 12; index += 1) {
      const key = `${yearPrefix}${pad(index)}`;
      const summary = aggregate(points.filter((point) => point.date.startsWith(key)));
      cells.push({
        key,
        label: `${index} 月`,
        amount: summary.pnl === null ? '--' : compact(summary.pnl),
        rateText: percent(summary.rate),
        tone: toneOf(summary.pnl),
        title:
          summary.pnl === null
            ? `${key} · 该月无可估值的交易日`
            : `${key} · 月盈亏 ${full(summary.pnl, currency)} · 收益率 ${percent(
                summary.rate,
              )} · 已确认 ${summary.days} 个交易日`,
      });
    }
    return {
      mode,
      title: `每月盈亏${unit}`,
      currency,
      cursorLabel: `${year}`,
      summaryLabel: `${year} 年盈亏`,
      summaryAmount: pnl === null ? '--' : full(pnl, currency),
      summaryRateText: percent(rate),
      summaryTone: toneOf(pnl),
      note: days
        ? `按 UTC 切月 · 已剔除出入金 · 已确认 ${days} 个交易日`
        : '该年暂无可估值的交易日',
      weekdayLabels: [],
      cells,
      isMonthly: true,
    };
  }

  const monthPrefix = `${year}-${pad(month)}`;
  const firstWeekday = new Date(Date.UTC(year, month - 1, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const today = todayUtc();
  const byDate = new Map(points.map((point) => [point.date, point]));
  const cells: StrategyPnlCalendarCell[] = [];
  for (let lead = 0; lead < firstWeekday; lead += 1) cells.push(blankCell(`lead-${lead}`));
  const monthPoints: StrategyPnlDayPoint[] = [];
  for (let day = 1; day <= daysInMonth; day += 1) {
    const date = `${monthPrefix}-${pad(day)}`;
    const point = byDate.get(date);
    if (point) monthPoints.push(point);
    cells.push(dayCell(date, day, point, today));
  }
  while (cells.length % 7 !== 0) cells.push(blankCell(`tail-${cells.length}`));
  const { pnl, rate, days } = aggregate(monthPoints);
  return {
    mode,
    title: `每日盈亏${unit}`,
    currency,
    cursorLabel: monthPrefix,
    summaryLabel: `${monthPrefix} 月盈亏`,
    summaryAmount: pnl === null ? '--' : full(pnl, currency),
    summaryRateText: percent(rate),
    summaryTone: toneOf(pnl),
    note: days
      ? `按 UTC 切日 · 已剔除出入金 · 已确认 ${days} 个交易日；进行中的当日待资金流核对后显示`
      : '本月暂无可估值的交易日',
    weekdayLabels,
    cells,
    isMonthly: false,
  };
}

/** 以某日为基准平移月份，用于日历左右翻页。 */
export function shiftMonth(cursor: PnlCalendarCursor, delta: number): PnlCalendarCursor {
  const index = cursor.year * 12 + (cursor.month - 1) + delta;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}
