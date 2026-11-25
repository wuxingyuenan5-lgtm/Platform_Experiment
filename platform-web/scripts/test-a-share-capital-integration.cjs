const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vue = require('vue');
const { parse, compileScript } = require('@vue/compiler-sfc');
const valuationStats = require('./load-strategy-module.cjs')()('src/views/hedgeBoard/components/indexValuationStats.ts');

function component(file, mocks) {
  const filename = path.resolve(__dirname, '../src/views/hedgeBoard/aShare/components', file);
  const script = compileScript(parse(fs.readFileSync(filename, 'utf8')).descriptor, {
    id: 'capital-integration',
  });
  const code = ts.transpileModule(script.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => {
      if (Object.hasOwn(mocks, name)) return mocks[name];
      if (name === 'vue') return { ...vue, onBeforeUnmount() {} };
      if (name === '../../components/indexValuationStats') return valuationStats;
      if (name.endsWith('.vue') || name.endsWith('VisibleChart')) return {};
      throw new Error('Unexpected dependency: ' + name);
    },
    mod,
    mod.exports,
  );
  return mod.exports.default;
}
const flush = async () => {
  await vue.nextTick();
  await new Promise(setImmediate);
};

test('capital API failure does not block domestic sections and tabs preserve the route query', async () => {
  const route = vue.reactive({
    query: { view: 'capital', section: 'derivatives', retained: 'yes' },
  });
  const ready = [];
  const scope = vue.effectScope();
  const panel = component('CapitalPanel.vue', {
    'vue-router': {
      RouterLink: {},
      useRoute: () => route,
      useRouter: () => ({
        replace: ({ query }) => {
          route.query = query;
        },
      }),
    },
    '@/api/platform/aShareCapital': {
      getAShareCapital: async () => {
        throw new Error('unavailable');
      },
    },
  });
  try {
    const state = scope.run(() =>
      panel.setup(vue.reactive({ refreshKey: 0 }), {
        expose() {},
        emit: (...args) => ready.push(args),
      }),
    );
    await flush();
    assert.equal(state.error.value, '资金面读取失败，请重试');
    assert.equal(state.isDomesticTab.value, true);
    assert.equal(state.tab.value, 'derivatives');
    assert.equal(ready.length, 0, 'domestic load owns its ready event');
    state.tab.value = 'margin';
    assert.equal(state.isDomesticTab.value, true);
    assert.equal(route.query.retained, 'yes');
    state.tab.value = 'others';
    assert.equal(state.isDomesticTab.value, false);
    await state.load();
    assert.equal(ready.length, 1);
    assert.deepEqual(
      state.tabs.map((item) => item.key),
      ['overview', 'etf', 'margin', 'funds', 'others', 'liquidity', 'derivatives'],
    );
    state.tab.value = 'funds';
    assert.equal(state.isIndependentTab.value, true);
    await state.load();
    assert.equal(
      ready.length,
      1,
      'fund holdings own their ready event even when capital data fails',
    );
    route.query = { view: 'funds', retained: 'yes' };
    await flush();
    assert.equal(state.tab.value, 'funds');
    route.query = { view: 'capital', section: 'invalid' };
    await flush();
    assert.equal(state.tab.value, 'overview');
    assert.equal(state.isIndependentTab.value, false);
    for (const section of ['structure', 'research', 'demand']) {
      route.query = { view: 'capital', section };
      await flush();
      assert.equal(state.tab.value, 'overview');
    }
    state.tab.value = 'etf';
    assert.equal(state.isIndependentTab.value, true);
    await state.load();
    assert.equal(ready.length, 1, 'ETF content owns readiness when the capital summary fails');
    state.tab.value = 'derivatives';
    route.query = { view: 'themes' };
    await flush();
    assert.equal(
      state.tab.value,
      'derivatives',
      'leaving the page must not mount a different hidden section',
    );
  } finally {
    scope.stop();
  }
});

test('unlock calendar and institution tables filter and paginate independently after moving together', async () => {
  const table = component('CapitalEventsTable.vue', {});
  const makeSource = (rows) => ({
    label: '测试',
    provider: '原始来源',
    sourceUrl: 'https://example.com',
    status: 'ready',
    isStale: false,
    rows,
  });
  const sources = {
    unlocks: makeSource(
      Array.from({ length: 40 }, (_, i) => ({
        date: `2026-11-${String((i % 20) + 5).padStart(2, '0')}`,
        code: String(i),
        name: '股票' + i,
        amount: i === 0 ? null : '0',
      })),
    ),
    funds: makeSource(
      Array.from({ length: 30 }, (_, i) => ({
        date: '2026-11-04',
        code: String(i),
        name: '基金' + i,
        shares: i === 0 ? null : '0',
      })),
    ),
    buybacks: makeSource([]),
    holders: makeSource([
      { date: '2026-11-04', code: '1', name: '股票1', holder: '张三', direction: '减持' },
      { date: '2026-11-03', code: '2', name: '股票2', holder: '李四', direction: '增持' },
    ]),
  };
  const scope = vue.effectScope();
  try {
    const setup = (title, sourceKeys) =>
      scope.run(() =>
        table.setup(vue.reactive({ title, sourceKeys, sources, asOf: '2026-11-05' }), {
          expose() {},
        }),
      );
    const calendar = setup('解禁日历', ['unlocks']);
    const institution = setup('机构与产业资本', ['funds', 'buybacks', 'holders']);
    assert.equal(calendar.pageRows.value.length, 25);
    assert.equal(institution.pageRows.value.length, 25);
    calendar.page.value = 2;
    institution.query.value = '基金29';
    await flush();
    assert.equal(institution.filteredRows.value.length, 1);
    assert.equal(calendar.page.value, 2);
    assert.equal(calendar.pageRows.value.length, 15);
    assert.equal(institution.cell({ shares: null }, { key: 'shares', numeric: true }), '—');
    assert.equal(institution.cell({ shares: '0' }, { key: 'shares', numeric: true }), '0');
    institution.query.value = '';
    institution.tableKey.value = 'holders';
    await flush();
    institution.direction.value = '减持';
    await flush();
    assert.equal(institution.pageRows.value.length, 1);
    assert.equal(institution.pageRows.value[0].holder, '张三');
    assert.equal(calendar.filteredRows.value.length, 40);
    institution.tableKey.value = 'buybacks';
    await flush();
    assert.equal(institution.pageRows.value.length, 0);
    assert.equal(institution.page.value, 1);
  } finally {
    scope.stop();
  }
});

test('domestic views share one read, filter actual contracts and keep missing values', async () => {
  let reads = 0;
  const payload = {
    margin: [],
    basis: [
      { date: '2026-11-03', family: 'IF', contract: 'IF2611', basis: '3', spot: '4000' },
      { date: '2026-11-03', family: 'IF', contract: 'IF2612', basis: '7', spot: '4000' },
      { date: '2026-11-04', family: 'IF', contract: 'IF2611', basis: null, spot: null },
      { date: '2026-11-04', family: 'IH', contract: 'IH2611', basis: '-2', spot: '3000' },
    ],
    iv: {
      rows: [
        {
          date: '2026-11-04',
          underlying: '510300',
          month: '202611',
          value: '20',
          contracts: ['C', 'P'],
        },
        {
          date: '2026-11-04',
          underlying: '510300',
          month: '202612',
          value: '22',
          contracts: ['C2', 'P2'],
        },
      ],
    },
    futuresSource: { status: 'ready' },
  };
  const panel = component('DomesticFinancingPanel.vue', {
    '@/api/hedgeResearch': {
      researchRequest: async () => {
        reads++;
        return payload;
      },
    },
  });
  const props = vue.reactive({ refreshKey: 0, mode: 'margin' });
  const scope = vue.effectScope();
  try {
    const state = scope.run(() => panel.setup(props, { expose() {}, emit() {} }));
    await flush();
    props.mode = 'derivatives';
    await flush();
    assert.equal(reads, 1);
    assert.equal(state.basisRows.value[0].contract, 'IF2611');
    assert.equal(state.basisRows.value[1].basis, null);
    assert.equal(
      state.basisSummary.value[0].value,
      null,
      'missing latest is not silently backdated',
    );
    state.contract.value = 'IF2612';
    await flush();
    assert.deepEqual(
      state.basisRows.value.map((r) => r.basis),
      ['7'],
    );
    state.family.value = 'IH';
    await flush();
    assert.equal(state.contract.value, 'near');
    assert.equal(state.basisRows.value[0].basis, '-2');
    assert.equal(state.ivRows.value[0].iv, '20');
    state.ivMonth.value = '202612';
    await flush();
    assert.equal(state.ivRows.value[0].iv, '22');
    state.underlying.value = '510050';
    await flush();
    assert.equal(state.ivMonth.value, 'near');
    assert.equal(state.ivRows.value.length, 0);
    props.refreshKey++;
    await flush();
    assert.equal(reads, 2);
  } finally {
    scope.stop();
  }
});

test('chart data mode paginates the selected range, preserves null and sorts latest first', async () => {
  const panel = component('FinancingChart.vue', {
    '@/hooks/web/useECharts': {
      useECharts: () => ({ getInstance: () => undefined, setOptions() {} }),
    },
  });
  const scope = vue.effectScope();
  const rows = Array.from({ length: 45 }, (_, i) => ({
    date: new Date(Date.UTC(2026, 8, i + 1)).toISOString().slice(0, 10),
    value: i === 44 ? null : String(i),
    contract: 'IF2611',
  }));
  try {
    const state = scope.run(() =>
      panel.setup(
        vue.reactive({
          title: '基差',
          rows,
          lines: [{ key: 'value', name: '基差', unit: '点', color: '#000' }],
          allowTable: true,
        }),
        { expose() {}, emit() {} },
      ),
    );
    assert.equal(state.tableRows.value.length, 20);
    assert.equal(state.tableRows.value[0].value, null);
    assert.equal(state.format(null), '—');
    assert.equal(state.format('0'), '0');
    assert.equal(state.tablePageCount.value, 3);
    state.tableView.value = true;
    state.tablePage.value = 3;
    assert.equal(state.tableRows.value.length, 5);
    state.selectRange(5);
    await flush();
    assert.equal(state.filtered.value.length, 6);
    assert.equal(state.tablePage.value, 1);
    assert.equal(state.hasContract.value, true);
  } finally {
    scope.stop();
  }
});
