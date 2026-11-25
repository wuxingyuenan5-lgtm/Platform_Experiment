const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const vue = require('vue');

function setup(file, names, modules = {}, props = {}) {
  const source = fs.readFileSync(path.resolve(__dirname, '../src/views/hedgeBoard', file), 'utf8');
  const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1];
  const hooks = {};
  const scope = vue.effectScope();
  const exports = {};
  const code = ts.transpileModule(`${script}\nexports.state = { ${names} };`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  scope.run(() =>
    vm.runInNewContext(code, {
      exports,
      AbortController,
      defineProps: () => props,
      defineEmits: () => () => {},
      require: (name) => {
        if (name in modules) return modules[name];
        if (name === '@/hooks/web/chartMotion') return {
          useChartReveal: () => Object.assign(async () => {}, { cancel() {} }),
        };
        if (name === 'vue')
          return {
            ...vue,
            onMounted: (fn) => (hooks.mount = fn),
            onBeforeUnmount: (fn) => (hooks.unmount = fn),
          };
        if (name.includes('useDashboardRefresh'))
          return { useDashboardRefresh: (fn) => (hooks.refresh = fn) };
        if (name === '@vueuse/core') return { useElementSize: () => ({ width: vue.ref(800) }) };
        return {};
      },
    }),
  );
  return {
    ...exports.state,
    hooks,
    close: () => {
      hooks.unmount?.();
      scope.stop();
    },
  };
}

const normalize = (value) => JSON.parse(JSON.stringify(value));
const response = (rows) => ({
  rows: rows.map(([date, correlation]) => ({ date, correlation })),
  note: 'Same interval returns',
  sources: ['https://btc.example', 'https://benchmark.example'],
});

test('combined correlations preserve each pair date and missingness, and isolate a failed pair', async () => {
  let failGold = false;
  const requests = [];
  const s = setup(
    'components/RollingCorrelationPanel.vue',
    'load, rows, lines, window, windowUsed, error, sources',
    {
      '@/api/hedgeResearch': {
        researchRequest: async ({ params }) => {
          requests.push(params);
          if (params.benchmark === 'xau' && failGold) throw new Error('unavailable');
          return params.benchmark === 'ndx'
            ? response([
                ['2026-01-01', '0.5'],
                ['2026-01-03', null],
              ])
            : response([
                ['2026-01-02', '0.7'],
                ['2026-01-03', '-0.1'],
              ]);
        },
      },
    },
  );
  try {
    await s.load();
    assert.deepEqual(normalize(s.rows.value), [
      { date: '2026-01-01', ndx: '0.5' },
      { date: '2026-01-02', xau: '0.7' },
      { date: '2026-01-03', ndx: null, xau: '-0.1' },
    ]);
    assert.equal(s.lines.value.length, 2);
    assert.equal(s.sources.value.filter((item) => item.url === 'https://btc.example').length, 1);
    failGold = true;
    s.window.value = 30;
    await s.load();
    assert.equal(s.windowUsed.value, 30);
    assert.deepEqual(
      Array.from(s.lines.value, (line) => line.key),
      ['ndx'],
    );
    assert.equal(
      s.rows.value.every((row) => !Object.hasOwn(row, 'xau')),
      true,
    );
    assert.match(s.error.value, /XAUUSD/);
    const before = requests.length;
    s.window.value = 9;
    await s.load();
    assert.equal(requests.length, before);
    assert.equal(s.windowUsed.value, 30);
  } finally {
    s.close();
  }
});

test('superseded correlation requests cannot overwrite the latest window', async () => {
  const pending = [];
  const s = setup(
    'components/RollingCorrelationPanel.vue',
    'load, rows, window, windowUsed, loading',
    {
      '@/api/hedgeResearch': {
        researchRequest: ({ params, signal }) =>
          new Promise((resolve) => pending.push({ params, signal, resolve })),
      },
    },
  );
  try {
    const first = s.load();
    s.window.value = 30;
    const second = s.load();
    pending.slice(2).forEach((request) => request.resolve(response([['2026-01-02', '0.3']])));
    await second;
    pending.slice(0, 2).forEach((request) => request.resolve(response([['2026-01-01', '0.1']])));
    await first;
    assert.equal(pending[0].signal.aborted, true);
    assert.equal(s.windowUsed.value, 30);
    assert.equal(s.rows.value[0].date, '2026-01-02');
    assert.equal(s.loading.value, false);
  } finally {
    s.close();
  }
});

test('halving range clamps both handles, keeps cursor in view, and survives data refresh', async () => {
  let lastDay = 1200;
  const s = setup(
    'components/BitcoinHalvingPanel.vue',
    'selectWindow, setRangeStart, setRangeEnd, rangeStart, rangeEnd, maxDay, cursorDay, path, cycles',
    {
      '@/api/hedgeResearch': {
        getCryptoDashboardV1: async () => ({
          groups: {
            halvingCycles: [2012, 2016, 2020, 2024].map((year) => ({
              seriesId: String(year),
              qualityFlags: [`base_date:${year}-01-01`, 'halving_block:210000'],
              observations: [0, lastDay].map((day) => ({
                date: new Date(Date.UTC(year, 0, 1) + day * 86400000).toISOString().slice(0, 10),
                value: '100',
              })),
            })),
          },
        }),
      },
    },
  );
  const input = (fn, value) => {
    const target = { value: String(value) };
    fn({ currentTarget: target });
    return target.value;
  };
  try {
    await s.hooks.refresh();
    await vue.nextTick();
    assert.equal(s.rangeEnd.value, 1095);
    input(s.setRangeStart, 200);
    input(s.setRangeEnd, 600);
    s.cursorDay.value = 500;
    assert.equal(input(s.setRangeStart, 900), '599');
    await vue.nextTick();
    assert.equal(s.cursorDay.value, 599);
    assert.equal(input(s.setRangeEnd, 0), '600');
    assert.equal(s.path(s.cycles.value[0]).includes('NaN'), false);
    s.selectWindow(0);
    input(s.setRangeStart, 200);
    input(s.setRangeEnd, 600);
    lastDay++;
    await s.hooks.refresh();
    await vue.nextTick();
    assert.equal(s.maxDay.value, 1201);
    assert.equal(s.rangeStart.value, 200);
    assert.equal(s.rangeEnd.value, 600);
    s.selectWindow(365);
    await vue.nextTick();
    assert.equal(s.rangeStart.value, 0);
    assert.equal(s.rangeEnd.value, 365);
    assert.equal(s.cursorDay.value <= 365, true);
    s.selectWindow(0);
    lastDay++;
    await s.hooks.refresh();
    assert.equal(s.rangeEnd.value, 1202);
  } finally {
    s.close();
  }
});

test('correlation legend visibility survives range and row updates', async () => {
  const props = vue.reactive({
    title: 'Correlations',
    rows: [{ date: '2026-01-01', ndx: '.1', xau: '.2' }],
    lines: [
      { key: 'ndx', name: 'BTC / 纳指', unit: '相关系数', color: 'blue' },
      { key: 'xau', name: 'BTC / XAUUSD', unit: '相关系数', color: 'gold' },
    ],
  });
  let option;
  const selected = { 'BTC / 纳指': false, 'BTC / XAUUSD': true };
  const s = setup(
    'aShare/components/FinancingChart.vue',
    'element, range',
    {
      '@/hooks/web/useECharts': {
        useECharts: () => ({
          getInstance: () => ({ getOption: () => ({ legend: [{ selected }] }) }),
          setOptions: (value) => {
            option = value;
          },
        }),
      },
    },
    props,
  );
  try {
    s.element.value = {};
    await new Promise(setImmediate);
    await vue.nextTick();
    await vue.nextTick();
    assert.deepEqual(normalize(option.legend.selected), selected);
    s.range.value = 90;
    await vue.nextTick();
    await vue.nextTick();
    assert.equal(option.legend.selected['BTC / 纳指'], false);
    props.rows = [...props.rows, { date: '2026-01-02', ndx: '.2', xau: null }];
    await vue.nextTick();
    await vue.nextTick();
    assert.equal(option.legend.selected['BTC / 纳指'], false);
    assert.deepEqual(Array.from(option.series[1].data), [0.2, null]);
  } finally {
    s.close();
  }
});

test('independent sessions do not insert holiday gaps, but explicit missing observations still break', async () => {
  const props = vue.reactive({
    title: 'Correlations', independentDates: true,
    rows: [
      { date: '2026-07-02', ndx: '.1', xau: '.2' },
      { date: '2026-07-03', xau: '.3' },
      { date: '2026-07-06', ndx: '.4', xau: null },
      { date: '2026-07-07', ndx: '.5', xau: '.6' },
    ],
    lines: [
      { key: 'ndx', name: 'NDX', color: 'blue', unit: 'r' },
      { key: 'xau', name: 'XAU', color: 'gold', unit: 'r' },
    ],
  });
  let option;
  const s = setup('aShare/components/FinancingChart.vue', 'element', {
    '@/hooks/web/useECharts': { useECharts: () => ({
      getInstance: () => null, setOptions: (value) => { option = value; },
    }) },
  }, props);
  try {
    s.element.value = {};
    await new Promise(setImmediate);
    assert.deepEqual(normalize(option.series[0].data), [
      ['2026-07-02', .1], ['2026-07-06', .4], ['2026-07-07', .5],
    ]);
    assert.deepEqual(normalize(option.series[1].data), [
      ['2026-07-02', .2], ['2026-07-03', .3], ['2026-07-06', null], ['2026-07-07', .6],
    ]);
    assert.equal(option.series[1].connectNulls, false);
    const tooltip = option.tooltip.formatter([
      { axisValue: '2026-07-06', dataIndex: 1, seriesIndex: 0, marker: '' },
    ]);
    assert.match(tooltip, /2026-07-06/);
    assert.match(tooltip, /0.4/);
    assert.doesNotMatch(tooltip, /2026-07-03/);
  } finally { s.close(); }
});

test('A-share chart refresh retains zoom; changing the chosen range resets it', async () => {
  const props = vue.reactive({
    title: 'A-share cash',
    rows: [{ date: '2026-01-01', cash: '-1' }],
    lines: [{ key: 'cash', name: 'Cash', color: 'red', unit: 'CNY' }],
  });
  let option;
  const s = setup(
    'aShare/components/FinancingChart.vue',
    'element, range',
    {
      '@/hooks/web/chartMotion': { useChartMotionEnabled: () => true },
      '@/hooks/web/useECharts': {
        useECharts: () => ({
          getInstance: () => ({ getOption: () => ({ dataZoom: [{ start: 25, end: 60 }] }) }),
          setOptions: (value) => {
            option = value;
          },
        }),
      },
    },
    props,
  );
  try {
    s.element.value = {};
    await new Promise(setImmediate);
    props.rows = [...props.rows, { date: '2026-01-02', cash: null }];
    await new Promise(setImmediate);
    assert.equal(option.dataZoom[0].start, 25);
    assert.equal(option.dataZoom[0].end, 60);
    assert.deepEqual(Array.from(option.series[0].data), [-1, null]);
    s.range.value = 90;
    await new Promise(setImmediate);
    assert.equal(option.dataZoom[0].start, undefined);
  } finally {
    s.close();
  }
});

test('A-share index switching retains named old data while pending, reuses cache, and forces refresh', async () => {
  const requests = [],
    cached = new Map();
  const s = setup('aShare/components/BroadEtfPanel.vue', 'selected, data, label, load', {
    '@/hooks/web/chartMotion': { useChartMotionEnabled: () => true },
    '@/api/hedgeResearch': {
      researchRequest: (request) => new Promise((resolve) => requests.push({ request, resolve })),
    },
    '@/hooks/web/useECharts': { useECharts: () => ({ getInstance: () => null, setOptions() {} }) },
    '../../composables/researchWorkspace': {
      useResearchSnapshots: () => ({
        get: (id) => cached.get(id),
        set: (id, data) => cached.set(id, data),
      }),
    },
    './broadEtfAnalysis': { visiblePeriods: () => [], withMarketCapRatios: rows => rows, numeric: Number },
  });
  const fixture = (key) => ({
    options: [
      { key: 'hs300', label: '沪深300' },
      { key: 'csi500', label: '中证500' },
    ],
    members: [{ code: key }],
    daily: [],
    weekly: [],
    marketCapRatio: { rows: [] },
  });
  const flush = () => new Promise(setImmediate);
  try {
    requests[0].resolve(fixture('first'));
    await flush();
    const initial = s.data.value;
    s.selected.value = 'csi500';
    await flush();
    assert.equal(s.data.value, initial);
    assert.equal(s.label.value, '沪深300');
    requests[1].resolve(fixture('second'));
    await flush();
    assert.equal(s.label.value, '中证500');
    s.selected.value = 'hs300';
    await flush();
    assert.equal(s.data.value, initial);
    assert.equal(requests.length, 2);
    const refresh = s.load(true);
    assert.equal(requests.length, 3);
    requests[2].resolve(fixture('fresh'));
    await refresh;
    await flush();
    assert.equal(s.data.value.members[0].code, 'fresh');
  } finally {
    s.close();
  }
});

test('restored ETF group analysis keeps its own selection and three-year history', async () => {
  const requests = [];
  const s = setup('aShare/components/BroadEtfPanel.vue', 'range, selected, selectedFund, selectFund, selectGroup, selectableFunds', {
    '@/api/hedgeResearch': {researchRequest: async request => {
      requests.push(request.url);
      return {options: [], singleFunds: [{code: 'a', name: 'A', group: 'hs300'}, {code: 'b', name: 'B', group: 'csi500'}], members: [], daily: [], weekly: []};
    }},
    '../../composables/researchWorkspace': {useResearchSnapshots: () => ({get: () => undefined, set() {}})},
    './broadEtfAnalysis': {visiblePeriods: () => [], withMarketCapRatios: rows => rows, numeric: Number},
  });
  const flush = () => new Promise(setImmediate);
  try {
    await flush();
    assert.equal(s.range.value, 1095);
    assert.ok(requests[0].endsWith('broad-etfs/hs300?days=1095'));
    s.selectFund('a'); await flush();
    assert.equal(s.selected.value, 'hs300');
    s.selectGroup('csi500'); await flush();
    assert.equal(s.selectedFund.value, '');
    assert.deepEqual(normalize(s.selectableFunds.value.map(f => f.code)), ['b']);
  } finally {s.close();}
});


test('theme range refresh retains the mounted chart while a different theme clears stale content', async () => {
  const requests = [];
  const s = setup('aShare/components/ThemeEtfPanorama.vue', 'history, range, selectedTheme', {
    '@/api/hedgeResearch': {researchRequest: request => new Promise(resolve => requests.push({request,resolve}))},
    '../../composables/researchWorkspace': {useResearchSnapshots: () => ({get: () => undefined, set() {}})},
  });
  const flush = () => new Promise(setImmediate);
  const fixture = {themes:[{code:'a',series:[]}],funds:[]};
  try {
    requests[0].resolve(fixture); await flush();
    requests[1].resolve(fixture); await flush();
    const original = s.history.value;
    s.range.value = 365; await flush();
    assert.equal(s.history.value, original); // do not unmount the chart or close its fullscreen dialog
    requests[2].resolve(fixture); await flush();
    s.selectedTheme.value = 'b'; await flush();
    assert.equal(s.history.value, undefined); // no prior theme values under a new selection
    requests[3].resolve(fixture); await flush();
  } finally {s.close();}
});
