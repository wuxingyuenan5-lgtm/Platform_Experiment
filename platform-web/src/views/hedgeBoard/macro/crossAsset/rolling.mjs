import { sessionAt } from "./calendar.mjs";

const DAY = 86400;
const date = t => new Date(t * 1000).toISOString().slice(0, 10);
const midnight = t => Math.floor(t / DAY) * DAY;
const week = t => t - ((new Date(t * 1000).getUTCDay() + 6) % 7) * DAY;
const periods = {
  "3D": (_, index) => Math.floor(index / 3),
  "1W": week,
  M: t => date(t).slice(0, 7),
};
const knownSession = t => ["before-open", "open", "after-close"].includes(sessionAt((t + 12 * 3600) * 1000).phase);

function buckets(calendar, period) {
  const groups = new Map();
  calendar.forEach((t, index) => {
    const key = period(t, index);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(t);
  });
  return [...groups.values()];
}

export function rollingMonitorSeries(snapshot, selected, now = Date.now()) {
  if (!snapshot.sessionCalendar?.length) return [];
  const today = Date.parse(sessionAt(now).date) / 1000;
  const sessionDates = new Set(snapshot.sessionCalendar);
  // Extend the same anchored buckets through the next expected sessions, even
  // when SPY's latest saved day has not arrived. Never infer a holiday as a gap.
  for (let t = (snapshot.calendarAnchorThrough ?? snapshot.sessionCalendar.at(-1)) + DAY; t <= today + 10 * DAY; t += DAY) {
    if (knownSession(t)) sessionDates.add(t);
  }
  const calendar = [...sessionDates].sort((a, b) => a - b);
  const session = sessionAt(now);
  const expectedDaily = calendar.findLast(t => t < today || (t === today && session.phase === "after-close"));
  const schedules = Object.entries(periods).map(([frame, period]) => [frame, buckets(calendar, period)]);
  const requested = new Set(selected);
  return snapshot.series.filter(s => s.frame === "1D" && requested.has(s.symbol)).flatMap(daily => {
    const rows = daily.lastBarComplete === true || daily.intraday ? daily.bars : daily.bars.slice(0, -1);
    const byDay = new Map(rows.map(bar => [midnight(bar.t), bar]));
    const latestBar = rows.at(-1);
    if (!latestBar) return [];
    const latest = midnight(latestBar.t);
    const openDay = daily.intraday ? latest : null;
    return schedules.flatMap(([frame, groups]) => {
      const bars = [];
      let asOf, complete, expectedThrough, missing = 0, currentGap = false;
      // Weekly/monthly calendar prefixes may begin mid-period. A three-session
      // bucket starts at the fixed anchor even if earlier history is unavailable.
      for (const [i, group] of groups.entries()) {
        if (i === 0 && frame !== "3D") continue;
        if (group[0] > latest) break;
        const elapsed = group.filter(t => t <= latest);
        const members = elapsed.map(t => byDay.get(t));
        if (members.some(b => !b)) {
          if (group.at(-1) >= latest) currentGap = true;
          if (group.at(-1) >= midnight(daily.bars[0].t)) missing++;
          continue;
        }
        const end = elapsed.at(-1);
        const periodEnd = group.at(-1);
        asOf = end; expectedThrough = periodEnd;
        complete = end === periodEnd && openDay !== end && i < groups.length - 1;
        bars.push({ t: group[0], o: members[0].o, h: Math.max(...members.map(b => b.h)),
          l: Math.min(...members.map(b => b.l)), c: members.at(-1).c, v: members.reduce((n, b) => n + b.v, 0) });
      }
      if (!bars.length) return [];
      return [{ ...daily, frame, bars, lastBarComplete: complete, aggregation: `rolling-daily-${frame}`,
        source: `${daily.source} · 同源日线滚动聚合`, hash: "",
        rolling: { asOf: date(asOf), dailyAsOf: date(latest), expectedThrough: date(expectedThrough),
          expectedDailyAsOf: expectedDaily === undefined ? undefined : date(expectedDaily), missing, currentGap },
        intraday: asOf === openDay ? daily.intraday : undefined }];
    });
  });
}
