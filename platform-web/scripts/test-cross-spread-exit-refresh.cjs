const assert = require('node:assert/strict');
const test = require('node:test');
const createLoader = require('./load-strategy-module.cjs');
const vue = require('vue');

function positionState() {
  const updatedAt = '2026-09-09T12:00:00Z';
  const exitPlans = vue.ref(['LONG_SPREAD', 'SHORT_SPREAD'].map((direction, index) => ({
    planId: `group-${index}`, status: 'active', direction, quantityOz: '1',
    entrySpread: index ? '-4.94' : '-3.22', mt5PositionId: `ticket-${index}`,
    takeProfitSpread: index ? '-9' : '6', stopLossSpread: index ? '4' : '-30',
    createdAt: updatedAt, updatedAt,
  })));
  const snapshot = vue.ref({
    status: 'available', asOf: '2026-09-09T12:30:00Z',
    bybit: { positions: [] }, mt5: { positions: [] },
    positionOverview: {
      groups: exitPlans.value.map((plan, index) => ({
        planId: plan.planId, planUpdatedAt: updatedAt, quantityOz: '1', openTime: updatedAt,
        bybitEntryPrice: index ? '4390.5' : '4392.9', mt5EntryPrice: index ? '4395.44' : '4396.12',
        bybitPnlUsdt: index ? '-4.6' : '2.1', mt5PnlUsdt: index ? '3.35' : '-2.9',
        totalPnlUsdt: index ? '-1.25' : '-0.8', dataQualityState: 'complete', reason: null,
      })),
      bybitPnlUsdt: '-2.5', mt5PnlUsdt: '0.45', totalPnlUsdt: '-2.05',
      dataQualityState: 'complete', asOf: '2026-09-09T12:30:00Z',
    },
  });
  const state = createLoader()(
    'src/views/strategy/spread-carry/composables/useCrossSpreadPositions.ts',
  ).useCrossSpreadPositions({
    exitPlans, snapshot, observability: vue.ref(null),
    quantityRules: vue.computed(() => ({ mt5Multiplier: 100 })),
    longSpread: vue.computed(() => -3), shortSpread: vue.computed(() => -3.2),
    snapshotStatusText: vue.computed(() => '双边真实行情'),
  });
  return { ...state, snapshot, exitPlans };
}

test('opposite groups with zero native net position show owned costs, PnL and exact backend totals', () => {
  const state = positionState();
  assert.deepEqual(state.overviewRows.value.map((row) => [row.pnl, row.legPnl, row.detail]), [
      ['-0.80', 'BY: +2.10 | MT5: -2.90', 'BY: 4,392.90 | MT5: 4,396.12 · Ticket ticket-0'],
      ['-1.25', 'BY: -4.60 | MT5: +3.35', 'BY: 4,390.50 | MT5: 4,395.44 · Ticket ticket-1'],
  ]);
  assert.equal(state.overviewPnl.value.totalPnlUsdt, '-2.05');
  assert.equal(state.overviewPnl.value.bybitPnlUsdt, '-2.5');
  assert.equal(state.overviewPnl.value.mt5PnlUsdt, '0.45');
  assert.equal(state.overviewRows.value[0].holdingTime, '30 分钟');
});

test('partial-close version changes suppress stale valuation until its matching read arrives', () => {
  const state = positionState();
  state.exitPlans.value[0].quantityOz = '0.5';
  state.exitPlans.value[0].updatedAt = '2026-09-09T12:31:00Z';
  assert.equal(state.overviewRows.value[0].pnl, '--');
  assert.equal(state.overviewRows.value[1].pnl, '-1.25');
  assert.equal(state.overviewPnl.value, null);
  const overview = state.snapshot.value.positionOverview;
  Object.assign(overview.groups[0], {
    quantityOz: '0.5', planUpdatedAt: '2026-09-09T12:31:00Z',
    bybitPnlUsdt: '1.05', mt5PnlUsdt: '-1.45', totalPnlUsdt: '-0.4',
  });
  Object.assign(overview, { bybitPnlUsdt: '-3.55', mt5PnlUsdt: '1.9', totalPnlUsdt: '-1.65' });
  assert.equal(state.overviewRows.value[0].pnl, '-0.40');
  assert.equal(state.overviewPnl.value.totalPnlUsdt, '-1.65');
});

test('a missing leg never becomes zero or silently disappears from the combined total', () => {
  const state = positionState();
  const overview = state.snapshot.value.positionOverview;
  Object.assign(overview.groups[1], {
    mt5PnlUsdt: null, totalPnlUsdt: null, dataQualityState: 'partial', reason: '持仓数据待更新',
  });
  Object.assign(overview, { mt5PnlUsdt: null, totalPnlUsdt: null, dataQualityState: 'partial' });
  assert.equal(state.overviewRows.value[0].pnl, '-0.80');
  assert.equal(state.overviewRows.value[1].pnl, '--');
  assert.equal(state.overviewPnl.value.totalPnlUsdt, null);
  assert.equal(state.overviewPnl.value.bybitPnlUsdt, '-2.5');
  state.snapshot.value.positionOverview = null;
  assert.equal(state.overviewPnl.value, null);
  assert.ok(state.overviewRows.value.every((row) => row.pnl === '--'));
});

test('the overview renders backend amounts without reparsing rounded row labels', async () => {
  const fs = require('node:fs');
  const path = require('node:path');
  const ts = require('typescript');
  const compiler = require('@vue/compiler-sfc');
  compiler.registerTS(() => ts);
  const filename = path.resolve(__dirname, '../src/views/strategy/spread-carry/components/SpreadPositionOverview.vue');
  const { descriptor } = compiler.parse(fs.readFileSync(filename, 'utf8'), { filename });
  const compiled = compiler.compileScript(descriptor, {
    id: 'pnl-overview-test', inlineTemplate: true,
    fs: { fileExists: fs.existsSync, readFile: (file) => fs.readFileSync(file, 'utf8') },
  });
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)(require, mod, mod.exports);
  const state = positionState();
  const rows = state.overviewRows.value;
  rows[0].pnl = '+999,999.99';
  rows[0].legPnl = 'BY: +111,111.11 | MT5: +222,222.22';
  const props = {
    overviewRows: rows, pnlOverview: state.overviewPnl.value, emptyText: '', longSpread: '-3',
    updateExitPlan: async () => { throw new Error('render must not change plans'); },
  };
  props.pnlOverview.unattributedPositions = [{
    venue: 'mt5', symbol: 'XAUUSD.s', side: 'sell', quantity: '-0.01',
    externalId: 'unattributed-ticket',
  }];
  const html = await require('vue/server-renderer').renderToString(vue.createSSRApp({
    render: () => vue.h(mod.exports.default, props),
  }));
  assert.match(html, /-2\.05 USDT/);
  assert.match(html, />-2\.50<\/em>/);
  assert.match(html, />0\.45<\/em>/);
  assert.match(html, /999,999\.99/);
  assert.doesNotMatch(html, /unattributed-ticket/);
});

test('an unallocated one-leg position remains visible for review', () => {
  const { mapOverviewRows } = createLoader()(
    'src/views/strategy/spread-carry/composables/mapCrossSpreadPositions.ts',
  );
  const rows = mapOverviewRows({
    snapshot: {
      status: 'available',
      bybit: { positions: [{ quantity: '0.4', averagePrice: '101' }] },
      mt5: { positions: [] },
    },
    observability: null,
    quantityRules: { mt5Multiplier: 100 },
    longSpread: 2,
    shortSpread: -2,
    snapshotStatusText: '双边真实行情',
    exitPlans: [],
  });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].exitPlanId, null);
  assert.equal(rows[0].qty, 0.4);
  assert.equal(rows[0].status, '待复核');
});

test('multiple groups retain their identities and do not inherit shared net-position PnL', () => {
  const { mapOverviewRows } = createLoader()(
    'src/views/strategy/spread-carry/composables/mapCrossSpreadPositions.ts',
  );
  const rows = mapOverviewRows({
    snapshot: {
      status: 'available',
      bybit: { positions: [{ quantity: '3', averagePrice: '100' }] },
      mt5: { positions: [{ quantity: '0.03', side: 'sell', averagePrice: '99' }] },
    },
    observability: null,
    quantityRules: { mt5Multiplier: 100 },
    longSpread: 2,
    shortSpread: -2,
    snapshotStatusText: '双边真实行情',
    exitPlans: [1, 2].map((q) => ({
      planId: `plan-${q}`,
      status: 'active',
      direction: 'LONG_SPREAD',
      quantityOz: String(q),
      entrySpread: '2',
      takeProfitSpread: String(q + 4),
      stopLossSpread: null,
      mt5PositionId: `ticket-${q}`,
      createdAt: '2026-09-09T00:00:00Z',
    })),
  });
  assert.deepEqual(
    rows.map((r) => [r.exitPlanId, r.qty, r.currentSpread, r.pnl]),
    [
      ['plan-1', 1, '-2.00', '--'],
      ['plan-2', 2, '-2.00', '--'],
    ],
  );
  assert.equal(new Set(rows.map((r) => r.id)).size, 2);
});

test('exit refresh follows server closure and cannot overwrite a later saved plan', async () => {
  const pending = [];
  const load = createLoader({
    '@/api/platform/crossSpreadLifecycle': {
      getCrossSpreadExitPlans: () =>
        new Promise((resolve, reject) => pending.push({ resolve, reject })),
      updateCrossSpreadExitPlanThresholds: async () => ({
        planId: 'plan-1',
        createdAt: '2026-09-09T00:00:00Z',
        status: 'active',
        takeProfitSpread: '5',
      }),
    },
  });
  const state = load(
    'src/views/strategy/spread-carry/composables/useCrossSpreadExitPlans.ts',
  ).useCrossSpreadExitPlans();
  const oldRead = state.refreshExitPlans();
  await state.updateExitPlanThresholds('plan-1', { takeProfitSpread: '5' });
  pending[0].resolve([{ planId: 'plan-1', status: 'active', takeProfitSpread: null }]);
  await oldRead;
  assert.equal(state.exitPlans.value[0].takeProfitSpread, '5');
  const first = state.refreshExitPlans();
  const second = state.refreshExitPlans();
  pending[2].resolve([{ planId: 'plan-1', status: 'closed', quantityOz: '0' }]);
  await second;
  pending[1].resolve([{ planId: 'plan-1', status: 'active', quantityOz: '1' }]);
  await first;
  assert.equal(state.exitPlans.value[0].status, 'closed');
  const failed = state.refreshExitPlans();
  pending[3].reject(new Error('offline'));
  assert.equal(await failed, 'offline');
  assert.equal(state.exitPlans.value[0].status, 'closed');
});
