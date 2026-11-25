const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

const file = path.join(__dirname, '..', 'src/api/platform/crossAssetScreening.ts');
const source = fs.readFileSync(file, 'utf8');
const out = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const moduleExports = {};
const req = (name) => {
  if (name === '../hedgeResearch') return { researchRequest: async () => ({}) };
  return {};
};
new Function('exports', 'require', 'module', '__filename', '__dirname', out)(
  moduleExports,
  req,
  { exports: moduleExports },
  file,
  path.dirname(file),
);

const { validateSnapshot, validateCaps, validateWatchlists, validateBackup } = moduleExports;
const symbols = ['AAA', 'BBB'];
const iso = '2026-11-06T15:10:00Z';
const snapshot = {
  version: 1,
  generatedAt: iso,
  series: [
    {
      symbol: 'AAA',
      tv: 'X:AAA',
      frame: '1D',
      fetchedAt: iso,
      hash: 'h',
      lastBarComplete: true,
      intraday: { quoteAt: iso, receivedAt: iso },
      rolling: {
        asOf: '2026-11-06',
        dailyAsOf: '2026-11-06',
        expectedThrough: '2026-11-06',
        missing: 0,
        currentGap: false,
      },
      bars: [
        { t: 1700000000, o: 1, h: 2, l: 1, c: 1.5, v: 3 },
        { t: 1700086400, o: 1.5, h: 2, l: 1.2, c: 1.8, v: 4 },
      ],
    },
  ],
};
const clean = validateSnapshot(snapshot, symbols);
assert.equal(clean.series[0].intraday, undefined);
assert.equal(clean.series[0].rolling, undefined);
assert.throws(
  () =>
    validateSnapshot(
      {
        ...snapshot,
        series: [
          { ...snapshot.series[0], bars: [{ ...snapshot.series[0].bars[0], t: 1700000000000 }] },
        ],
      },
      symbols,
    ),
  /seconds/,
);
assert.throws(
  () =>
    validateSnapshot(
      {
        ...snapshot,
        series: [
          { ...snapshot.series[0], bars: [snapshot.series[0].bars[1], snapshot.series[0].bars[1]] },
        ],
      },
      symbols,
    ),
  /ordered/,
);
assert.throws(() => validateSnapshot({ ...snapshot, version: 2 }, symbols), /snapshot.version/);
assert.throws(
  () =>
    validateSnapshot(
      {
        ...snapshot,
        series: [{ ...snapshot.series[0], bars: [{ ...snapshot.series[0].bars[0], c: 0 }] }],
      },
      symbols,
    ),
  /OHLCV/,
);
assert.throws(
  () =>
    validateSnapshot({ ...snapshot, series: [snapshot.series[0], snapshot.series[0]] }, symbols),
  /duplicate/,
);
const caps = {
  date: '2026-11-06',
  dates: ['2026-11-06'],
  rows: {},
  total: 0,
  method: 'test',
  checkedAt: null,
};
assert.equal(validateCaps(caps, symbols).date, caps.date);
assert.deepEqual(
  validateWatchlists([{ id: 'x', name: '观察', symbols: ['AAA'] }], symbols)[0].symbols,
  ['AAA'],
);
assert.throws(
  () => validateWatchlists([{ id: 'x', name: '重复', symbols: ['AAA', 'AAA'] }], symbols),
  /duplicate/,
);
const old = validateBackup(
  {
    format: 'wave-monitor-portable',
    version: 1,
    archive: snapshot,
    caps,
    state: {
      watchlists: [{ id: 'x', name: '观察', members: ['AAA'] }],
      favorites: ['AAA'],
      activeWatchlistId: '',
    },
  },
  [{ symbol: 'AAA' }, { symbol: 'BBB' }],
);
assert.equal(old.activeWatchlist, '');
const current = validateBackup(
  {
    format: 'global-variable-cross-asset',
    version: 1,
    snapshot,
    caps,
    watchlists: [],
    activeWatchlist: null,
    preferences: { density: 'compact' },
  },
  [{ symbol: 'AAA' }],
);
assert.equal(current.preferences.density, 'compact');
assert.throws(
  () =>
    validateWatchlists(
      [
        { id: 'x', name: '观察', symbols: [] },
        { id: 'y', name: '观察', symbols: [] },
      ],
      symbols,
    ),
  /watchlists|duplicate/,
);
console.log('cross-asset import validation passed');
const badTime = structuredClone(snapshot);
badTime.series[0].bars[1].t = Math.floor(Date.parse(iso) / 1000) + 1;
assert.throws(() => validateSnapshot(badTime, symbols), /after fetchedAt/);
const badCollection = structuredClone(snapshot);
badCollection.series[0].fetchedAt = '2026-11-07T15:10:00Z';
assert.throws(() => validateSnapshot(badCollection, symbols), /after snapshot/);
const portablePreferences = {
  'wave-monitor-portable:monitor:v2': JSON.stringify({ frame: 'M', groups: ['ema'] }),
  'wave-monitor-portable:monitor-assets:v1': JSON.stringify({ min: '12', unit: 1e9 }),
  'wave-monitor-portable:monitor-filters:v3': JSON.stringify({
    filters: { match: 'any' },
    sort: { by: 'event' },
  }),
};
const restored = validateBackup(
  {
    format: 'wave-monitor-portable',
    version: 1,
    archive: snapshot,
    caps,
    state: { favorites: ['AAA'], watchlists: [], activeWatchlistId: 'favorites' },
    preferences: portablePreferences,
  },
  [{ symbol: 'AAA', kind: 'stock' }],
);
assert.equal(restored.preferences.chart.frame, 'M');
assert.equal(restored.preferences.assetScreen.unit, 1e9);
assert.equal(restored.preferences.filters.match, 'any');
const zeroVolume = structuredClone(snapshot);
zeroVolume.series[0].bars[0].v = 0;
assert.equal(validateSnapshot(zeroVolume, symbols).series[0].bars[0].v, 0);
clean.series[0].bars[0].c = 1.1;
assert.equal(snapshot.series[0].bars[0].c, 1.5);
console.log('cross-asset chronology and portable backup tests passed');
const nativeSnapshot = structuredClone(snapshot);
nativeSnapshot.series[0].bars[0].native = {
  source: 'NashNova',
  macd: { dif: 2, dea: 1.5, histogram: 0.5 },
  rsi: 61,
  estimatedAmount: 12345,
};
const nativeClean = validateSnapshot(nativeSnapshot, symbols);
assert.deepEqual(nativeClean.series[0].bars[0].native, nativeSnapshot.series[0].bars[0].native);
const auxiliary = require('./load-strategy-module.cjs')()(
  'src/views/hedgeBoard/macro/crossAsset/auxiliary.ts',
);
const nativeValues = auxiliary.computeAuxiliary(nativeClean.series[0].bars);
assert.equal(nativeValues.dif[0], 2);
assert.equal(nativeValues.rsi[0], 61);
assert.equal(nativeValues.amount[0], 12345);
nativeSnapshot.series[0].bars[0].native.macd.histogram = 99;
assert.throws(() => validateSnapshot(nativeSnapshot, symbols), /MACD/);
nativeSnapshot.series[0].bars[0].native.macd.histogram = 0.5;
nativeSnapshot.series[0].bars[0].native.rsi = 110;
assert.throws(() => validateSnapshot(nativeSnapshot, symbols), /RSI/);
const holdingBackup = validateBackup(
  {
    format: 'wave-monitor-portable',
    version: 1,
    archive: snapshot,
    caps,
    state: { favorites: [], watchlists: [], holdings: [{ symbol: 'AAA', quantity: 5 }] },
  },
  [{ symbol: 'AAA', kind: 'stock' }],
);
assert.deepEqual(holdingBackup.preferences.holdingSymbols, ['AAA']);
assert.equal(
  holdingBackup.watchlists.some((list) => list.id === 'favorites' && list.symbols.length === 0),
  true,
);
assert.equal(
  validateWatchlists(
    [
      { id: 'favorites', name: '默认自选', symbols: [] },
      ...Array.from({ length: 100 }, (_, i) => ({
        id: 'custom-' + i,
        name: '自选' + i,
        symbols: [],
      })),
    ],
    symbols,
  ).length,
  101,
);
console.log('native indicator and backup holding parity passed');
