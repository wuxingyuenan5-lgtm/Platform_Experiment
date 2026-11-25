/* Offline pure-computation smoke/regression tests; no browser, network or API required. */
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const ts = require('typescript');
require.extensions['.ts'] = (mod, filename) => {
  const source = require('node:fs').readFileSync(filename, 'utf8');
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true }, fileName: filename }).outputText;
  mod._compile(js, filename);
};
const root = require('node:path').join(__dirname, '..', 'src', 'views', 'hedgeBoard', 'macro', 'crossAsset');
const engine = require(require('node:path').join(root, 'engine.ts'));
const rules = require(require('node:path').join(root, 'rules.ts'));
const filters = require(require('node:path').join(root, 'filters.ts'));
const auxiliary = require(require('node:path').join(root, 'auxiliary.ts'));
const screen = require(require('node:path').join(root, 'assetScreen.ts'));
const kalman = require(require('node:path').join(root, 'kalman.ts'));
const summary = require(require('node:path').join(root, 'summary.ts'));
const bars = (n) => Array.from({ length: n }, (_, i) => { const c = 100 + i / 10 + Math.sin(i / 7); return { t: 1600000000 + i * 86400, o: c - 1, h: c + 1, l: c - 2, c, v: i }; });
assert.deepEqual(engine.validateBars([{ ...bars(1)[0], h: 0 }]), ['ohlcv:0']);
assert.equal(engine.maturity(676, 675).eligible, false);
const input = bars(700), computed = engine.compute(input, true), assessed = rules.classify(computed);
assert.equal(assessed.history.length, input.length);
assert.equal(assessed.current.direction, assessed.current.systems.zlma.direction);
assert.deepEqual(rules.confirmStates(['不足', '多', '多', '多', '震荡', '空', '空', '多'], 3), ['不足', '震荡', '震荡', '多', '震荡', '震荡', '震荡', '震荡']);
assert.equal(auxiliary.rsi(Array(20).fill(100)).at(-1), 50);
assert.equal(auxiliary.computeAuxiliary(input).histogram.slice(0, 59).every((v) => v === null), true);
assert.equal(kalman.kalmanPrice(input).length, input.length);
const security = { symbol: 'AAPL', kind: 'stock', category: '科技', sector: '信息技术' };
const f = { ...screen.defaultAssetScreen(), min: '1000' };
assert.equal(screen.matchesAssetScreen(security, f, null), false);
assert.equal(screen.matchesAssetScreen(security, { ...f, includeUnknown: true }, null), true);
const trends = { '1D': { current: '多', since: 3, events: [{ index: 2, age: 0, t: 3, previous: '空', direction: '多' }] } };
const filters0 = filters.defaultTrendFilters(); filters0.rules['1D'].turn = '多';
assert.equal(filters.matchesTrend(trends, filters0), true);
console.log('cross-asset pure computation tests: ok');

// Golden parity against all 48 offline reference series. This intentionally compares
// pure outputs only; it does not exercise network/API/browser behavior.
const snapshot = require(require('node:path').join(__dirname, '..', '..', 'platform-api', 'app', 'research_templates', 'cross_asset_screening', 'sampleSnapshot.json'));
const GOLDEN = { series: 48, transitions: 3046, insufficient: 1, eligible3: 33, summaryEvents: 9191 };
let paritySeries = 0;
let totalTransitions = 0; let insufficient = 0; let eligible3 = 0; let totalSummaryEvents = 0;
for (const series of snapshot.series) {
  const oursComputed = engine.compute(series.bars, series.lastBarComplete === true);
  const oursClassified = rules.classify(oursComputed, rules.DEFAULT_RULE);
  totalTransitions += filters.transitions(oursClassified.history).length;
  totalSummaryEvents += summary.summarizeSeries(series, false, rules.DEFAULT_RULE).events.length;
  if (oursClassified.current.direction === '不足') insufficient += 1;
  if (oursClassified.current.eligible === 3) eligible3 += 1;
  paritySeries += 1;
}
assert.deepEqual({ series: paritySeries, transitions: totalTransitions, insufficient, eligible3, summaryEvents: totalSummaryEvents }, GOLDEN);
console.log(`golden parity: ${paritySeries} series`);
console.log(`summary events: ${totalSummaryEvents}`);

(async () => {
  const rolling = await import(pathToFileURL(require('node:path').join(root, 'rolling.mjs')).href);
  const base = snapshot.series.find((s) => s.frame === '1D');
  const dayBars = base.bars.slice(0, 15).map((b) => ({ ...b, t: b.t - b.t % 86400 }));
  const calendar = dayBars.map((b) => b.t);
  const rollingSnapshot = { series: [{ ...base, bars: dayBars, lastBarComplete: true }], sessionCalendar: calendar, calendarAnchorThrough: calendar.at(-1) };
  const aggregated = rolling.rollingMonitorSeries(rollingSnapshot, [base.symbol], Date.parse('2026-11-06T20:00:00Z'));
  assert.ok(aggregated.some((s) => s.frame === '3D' && s.bars.length > 0), 'rolling 3D output');
  const missingBars = dayBars.filter((_, i) => i !== 5);
  const missing = rolling.rollingMonitorSeries({ ...rollingSnapshot, series: [{ ...base, bars: missingBars, lastBarComplete: true }] }, [base.symbol], Date.parse('2026-11-06T20:00:00Z'));
  assert.ok(missing.some((s) => (s.rolling?.missing || 0) > 0), 'rolling missing-day evidence');
  console.log('rolling calendar tests: ok');
})().catch((error) => { console.error(error); process.exitCode = 1; });
