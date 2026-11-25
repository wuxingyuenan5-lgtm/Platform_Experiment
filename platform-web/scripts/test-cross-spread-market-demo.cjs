const test = require('node:test');
const assert = require('node:assert/strict');
const a = require('./load-strategy-module.cjs')()(
  'src/views/strategy/spread-carry/market-demo/marketDemo.ts',
);
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);
const base = {
  direction: 'short',
  mid: 9.2,
  width: 1.1,
  target: 2.8,
  quantity: 5,
  hours: 8,
  feeBps: 5.5,
  fundingBps: 1,
  swap: -0.8,
  buffer: 0.3,
};

test('directional bid/ask economics include both quote losses exactly once', () => {
  const short = a.economics(base);
  near(short.entry, 8.65);
  near(short.exit, 3.35);
  near(short.price, 5.3);
  near(short.funding, 0.4);
  near(short.fees, 4.46);
  near(short.net, 0.94);
  near(short.total, 4.7);
  const long = a.economics({ ...base, direction: 'long', mid: -3.6 });
  near(long.entry, -3.05);
  near(long.exit, 2.25);
  near(long.price, 5.3);
  near(long.funding, -0.4);
  near(long.net, 0.14);
  near(a.economics({ ...base, mid: 2.8 }).price, -1.1);
  near(a.economics({ ...base, width: 6.8 }).net, short.net - 5.7);
});

test('cash flow counts settlement events and triple swap without daily prorating', () => {
  assert.equal(a.economics({ ...base, hours: 2 }).events.length, 0);
  assert.equal(a.economics({ ...base, hours: 2.5 }).events.length, 1);
  const oneDay = a.economics({ ...base, hours: 24 });
  near(oneDay.funding, 1.2);
  near(oneDay.swap, -0.8);
  const threeDays = a.economics({ ...base, hours: 72 });
  near(threeDays.funding, 3.6);
  near(threeDays.swap, -4);
  near(a.economics({ ...base, fundingBps: -1 }).funding, -0.4);
  near(a.economics({ ...base, quantity: 10 }).total, a.economics(base).total * 2);
});

test('break-even boundary yields zero net space in either direction', () => {
  for (const direction of ['long', 'short']) {
    const p = { ...base, direction, hours: 72 };
    const result = a.economics(p);
    near(
      a.economics({ ...p, mid: p.target + (direction === 'short' ? 1 : -1) * result.breakEven })
        .net,
      0,
    );
  }
});

test('event study freezes earlier centres and never counts overlapping quotes as events', () => {
  const rows = Array.from({ length: 100 }, (_, i) => ({
    time: (i * a.HOUR) / 2,
    mid: i < 60 ? (i % 2 ? 1 : -1) : i < 66 ? 9 : 0,
    session: '美国',
  }));
  const result = a.study(rows);
  assert.equal(result.centres['美国'].median, 0);
  assert.equal(result.events.length, 1);
  assert.equal(result.events[0].status, 'reverted');
  assert.equal(result.events[0].hours, 3);
  const changed = a.study(rows.map((r, i) => (i >= 60 ? { ...r, mid: 15 } : r)));
  assert.deepEqual(changed.centres, result.centres);
  assert.equal(changed.events[0].status, 'censored');
});

test('event gaps stay censored, timeouts stay in denominator, empty samples remain unknown', () => {
  const rows = Array.from({ length: 200 }, (_, i) => ({
    time: (i * a.HOUR) / 2,
    mid: i < 120 ? (i % 2 ? 1 : -1) : 9,
    session: '美国',
  }));
  const events = a.study(rows).events;
  assert.equal(events.length, 1);
  assert.equal(events[0].status, 'timeout');
  const summary = a.eventSummary(events);
  assert.equal(summary.rate, 0);
  assert.equal(summary.hours, null);
  const gap = a.study(
    rows.map((r, i) => ({ ...r, time: r.time + (i > 122 ? a.HOUR * 48 : 0) })),
  ).events;
  assert.equal(gap[0].status, 'censored');
  assert.equal(a.eventSummary(gap).rate, null);
  assert.equal(a.quantile([], 0.5), null);
});

test('synthetic data and attribution are deterministic and closed quotes have no attribution', () => {
  assert.deepEqual(a.makeHistory(), a.HISTORY);
  for (const scenario of Object.values(a.SCENARIOS)) {
    if (scenario.valid)
      near(
        scenario.basis.reduce((a, b) => a + b, 0),
        scenario.mid,
      );
    else assert.equal(scenario.basis.length, 0);
  }
});
