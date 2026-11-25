const assert = require('node:assert/strict');
const test = require('node:test');
const load = require('./load-strategy-module.cjs')({});
const { etfLeadLag } = load('src/views/hedgeBoard/aShare/components/etfLeadLag.ts');

test('share growth leads returns by one session, without compressing a missing session', () => {
  const sessions = Array.from({ length: 48 }, (_, i) =>
    new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10),
  );
  let units = 1,
    price = 1,
    previous = 0;
  const rows = sessions.map((date, i) => {
    const change = ((i * i) % 11) / 100;
    price *= 1 + previous;
    units *= 1 + change;
    previous = change;
    return { date, etf_qfq_close: price, qfq_total_units_yi: units };
  });
  const analyze = (data) => etfLeadLag(data, sessions, sessions[0], sessions.at(-1));
  const pair = analyze(rows).find((row) => row.lag === 1);
  assert.equal(pair.n, 46);
  assert.ok(Math.abs(pair.correlation - 1) < 1e-12);
  assert.notEqual(analyze(rows).find((row) => row.lag === -1).correlation, pair.correlation);
  const gap = analyze(rows.filter((_, i) => i !== 25)).find((row) => row.lag === 1);
  assert.equal(gap.n, 43);
  assert.ok(Math.abs(gap.correlation - 1) < 1e-12);
  assert.ok(analyze(rows.slice(0, 19)).every((row) => row.correlation === null));
  assert.ok(
    analyze(rows.map((row) => ({ ...row, qfq_total_units_yi: 1 }))).every(
      (row) => row.correlation === null,
    ),
  );
});
