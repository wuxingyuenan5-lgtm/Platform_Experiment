const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const ts = require('typescript');
const vue = require('vue');
const { parse, compileScript } = require('@vue/compiler-sfc');
require.extensions['.ts'] = (mod, file) =>
  mod._compile(
    ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    file,
  );
const root = path.resolve(__dirname, '../src/views/hedgeBoard/macro');
const dataRoot = path.resolve(
  __dirname,
  '../../platform-api/app/research_templates/cross_asset_screening',
);
const read = (file) => JSON.parse(fs.readFileSync(path.join(dataRoot, file), 'utf8'));
const assets = read('assets.json');
const info = {
  snapshot: read('sampleSnapshot.json'),
  assets,
  calendar: read('sampleCalendar.json'),
  caps: {
    date: '2026-10-26',
    rows: Object.fromEntries(
      assets
        .filter((s) => s.kind === 'stock')
        .map((s) => [
          s.symbol,
          { symbol: s.symbol, value: s.cap, currency: 'USD', date: '2026-10-26' },
        ]),
    ),
  },
};
const golden = require('./fixtures/cross-asset-reference.json');
function setup() {
  const file = path.join(root, 'CrossAssetScreener.vue');
  const script = compileScript(parse(fs.readFileSync(file, 'utf8')).descriptor, {
    id: 'cross-asset-workflow',
  }).content;
  const code = ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  global.localStorage = { getItem: () => null, setItem() {} };
  const route = vue.reactive({ query: { view: 'cross-asset-screening' } });
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => {
      if (name === 'vue') return { ...vue, onMounted() {}, onBeforeUnmount() {} };
      if (name === 'ant-design-vue') return {};
      if (name === 'vue-router')
        return {
          useRoute: () => route,
          useRouter: () => ({
            replace({ query }) {
              route.query = query;
              return Promise.resolve();
            },
          }),
        };
      if (name === '@/store/modules/user')
        return { useUserStore: () => ({ getUserInfo: { userId: 'isolated' } }) };
      if (name === '@/api/platform/crossAssetScreening')
        return {
          getCrossAssetScreening: async () => info,
          readScreeningData: async () => null,
          validateWatchlists: (value) => value,
        };
      if (name.endsWith('.vue')) return {};
      if (name.endsWith('rolling.mjs')) return { rollingMonitorSeries: () => [] };
      if (name.startsWith('./')) return require(path.join(root, name + '.ts'));
      throw Error(name);
    },
    mod,
    mod.exports,
  );
  const scope = vue.effectScope();
  const state = scope.run(() => mod.exports.default.setup({}, { expose() {} }));
  return { state, scope, route };
}
const canonical = (events) =>
  JSON.stringify(
    events.map((e) =>
      Object.fromEntries(
        Object.keys(e)
          .sort()
          .map((k) => [k, e[k]]),
      ),
    ),
  );
const digest = (events) => crypto.createHash('sha256').update(canonical(events)).digest('hex');

test('actual page computations match original-package screening and signal golden cases', async () => {
  const s = setup();
  try {
    await s.state.load();
    for (const row of golden.cases) {
      const c = row.settings;
      for (const key of [
        'kind',
        'scope',
        'structure',
        'query',
        'sort',
        'assetScreen',
        'eventSystem',
        'eventFrame',
        'eventSide',
      ])
        s.state[key].value = c[key];
      s.state.trendFilters.value = c.filters;
      assert.deepEqual(
        s.state.rows.value.map((a) => a.symbol),
        row.symbols,
        row.name + ' symbols',
      );
      assert.equal(s.state.events.value.length, row.eventCount, row.name + ' event count');
      assert.equal(digest(s.state.events.value), row.eventHash, row.name + ' full signal identity');
    }
  } finally {
    s.scope.stop();
  }
});

test('presets support safe save, rename, explicit replacement and period reset without changing other conditions', async () => {
  const s = setup();
  try {
    await s.state.load();
    s.state.savePreset('观察');
    const id = s.state.presets.value[0].id;
    s.state.trendFilters.value.rules['1D'].state = '多';
    s.state.savePreset('观察');
    assert.equal(s.state.presets.value.length, 1);
    assert.equal(s.state.presets.value[0].filters.rules['1D'].state, 'any');
    s.state.chosenPreset.value = id;
    s.state.presetRename.value = '周月观察';
    s.state.renamePreset();
    assert.equal(s.state.presets.value[0].name, '周月观察');
    s.state.updatePreset();
    assert.equal(s.state.presets.value[0].filters.rules['1D'].state, '多');
    s.state.trendFilters.value.rules['1W'].state = '空';
    s.state.useChosenPreset();
    assert.equal(s.state.trendFilters.value.rules['1W'].state, 'any');
    s.state.removePreset(id);
    assert.equal(s.state.presets.value.length, 0);
  } finally {
    s.scope.stop();
  }
});

test('historical links, return-to-latest and filtered navigation retain the intended instrument and frame', async () => {
  const s = setup();
  try {
    await s.state.load();
    s.state.openChart('AAPL', '1D', 1705069800);
    await vue.nextTick();
    assert.equal(s.route.query.at, '1705069800');
    s.state.returnToLatest();
    await vue.nextTick();
    assert.equal(s.route.query.at, undefined);
    assert.equal(s.state.signalAt.value, undefined);
    assert.equal(s.state.rolling.value, true);
    s.state.openChart('AAPL', 'M');
    await vue.nextTick();
    assert.equal(s.route.query.frame, 'M');
    s.state.query.value = 'NVDA';
    s.state.stepAsset(1);
    await vue.nextTick();
    assert.equal(s.state.symbol.value, 'NVDA');
    s.state.query.value = 'no-match';
    s.state.stepAsset(1);
    assert.equal(s.state.symbol.value, 'NVDA');
    s.state.scope.value = 'holdings';
    s.state.query.value = '';
    s.state.holdingSymbols.value = ['TLT'];
    assert.deepEqual(
      s.state.rows.value.map((a) => a.symbol),
      ['TLT'],
    );
  } finally {
    s.scope.stop();
  }
});
