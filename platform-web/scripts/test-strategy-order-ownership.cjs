const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vue = require('vue');
const compiler = require('@vue/compiler-sfc');
const { renderToString } = require('vue/server-renderer');
const loadModule = require('./load-strategy-module.cjs');

test('Cross records use owned logical legs and cannot import shared-account Funding positions', async () => {
  const scopes = [];
  const getOwned = async (id) => {
    scopes.push(id);
    return [];
  };
  const load = loadModule({
    '@/api/platform/trading': {
      getOrders: getOwned,
      getFills: getOwned,
      getExecutionBatches: getOwned,
      getStrategyPnl: async () => ({ economicEvents: [] }),
      getCrossSpreadSnapshot: async () => ({
        bybit: {
          symbol: 'XAUTUSDT',
          positions: [
            { symbol: 'BTCUSDT', quantity: '-0.001' },
            // Shared-account exposure in the same symbol must not replace
            // the quantity owned by this strategy's instruction either.
            { symbol: 'XAUTUSDT', quantity: '999' },
          ],
        },
        mt5: { symbol: 'XAUUSD.S', positions: [{ externalId: 'closed-ticket', quantity: '0.01' }] },
        positionOverview: {
          abnormalOrders: [{ planId: 'error', batchId: 'bad', label: '单腿异常' }],
          groups: [
            {
              planId: 'owned',
              direction: 'LONG_SPREAD',
              bybitQuantity: '1',
              mt5Quantity: '0.01',
              mt5PositionId: 'correct-ticket',
              bybitEntryPrice: '4400',
              mt5EntryPrice: '4403',
              bybitPnlUsdt: '1.23',
              mt5PnlUsdt: '-0.02',
            },
            { planId: 'error', bybitQuantity: '1' },
          ],
        },
      }),
    },
  });
  const state = load(
    'src/views/strategy/management/composables/useCrossSpreadRecords.ts',
  ).useCrossSpreadRecords();
  await state.refresh();
  assert.equal(state.error.value, '');
  const rows = state.tables.value.positions.rows;
  assert.equal(rows.length, 2);
  assert.deepEqual(
    rows.map((row) => [row.symbol, row.quantity]),
    [
      ['XAUTUSDT', '1'],
      ['XAUUSD.S', '0.01'],
    ],
  );
  assert.equal(rows[1].ticket, 'correct-ticket');
  assert.ok(rows.every((row) => row.planId === 'owned'));
  assert.ok(scopes.every((id) => id === 'strategy_cross_venue_spread_instance_default'));
});

function component(relative) {
  compiler.registerTS(() => ts);
  const filename = path.resolve(__dirname, '..', relative);
  const { descriptor } = compiler.parse(fs.readFileSync(filename, 'utf8'), { filename });
  const output = compiler.compileScript(descriptor, {
    id: 'ownership-test',
    inlineTemplate: true,
    fs: { fileExists: fs.existsSync, readFile: (name) => fs.readFileSync(name, 'utf8') },
  });
  const code = ts.transpileModule(output.content, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText;
  const mod = { exports: {} };
  const dependencies = (name) => {
    if (name === '@/store/modules/user')
      return { useUserStore: () => ({ authentication: { user: { role: 'ceo' } } }) };
    if (name.startsWith('@/api/')) return {};
    return require(name);
  };
  new Function('require', 'module', 'exports', code)(dependencies, mod, mod.exports);
  return mod.exports.default;
}

test('Cross abnormal card is absent with no owned abnormal orders', async () => {
  const card = component('src/views/strategy/spread-carry/components/SpreadAbnormalOrders.vue');
  const html = await renderToString(
    vue.createSSRApp({ render: () => vue.h(card, { orders: [], busy: false }) }),
  );
  assert.doesNotMatch(html, /abnormal-orders|异常订单/);
});

test('Funding abnormal card appears only for active Funding errors and shows distinct leg quantities', async () => {
  const panel = component('src/views/strategy/funding-carry/components/FundingOrderPanel.vue');
  const props = {
    context: null,
    positionGroups: [],
    pendingDraft: null,
    workspaceState: 'idle',
    submitting: false,
    error: null,
    quantityInput: '',
    closeQuantityInput: '',
    executionPolicy: 'market',
    perpetualLimitPriceInput: '',
    canClose: false,
    notionalInput: '100',
    selectedCloseInstructionId: '',
    selectedCloseGroup: null,
    canSubmit: false,
  };
  const render = () => renderToString(vue.createSSRApp({ render: () => vue.h(panel, props) }));
  assert.doesNotMatch(await render(), /资费异常订单/);
  props.positionGroups = [
    { instructionId: 'old-error', lifecycleState: 'history', isAbnormal: true },
  ];
  assert.doesNotMatch(await render(), /资费异常订单/);
  props.positionGroups = [
    {
      instructionId: 'fee-error',
      batchId: 'funding-batch',
      lifecycleState: 'active',
      isAbnormal: true,
      perpetualSymbol: 'BTCUSDT',
      remainingPerpetualQuantity: '0.001',
      remainingSpotHolding: '0.000999',
      netDeltaQuantity: '-0.000001',
      abnormalReason: '手续费未配平',
      abnormalAction: 'close_group',
    },
  ];
  const html = await render();
  assert.match(html, /资费异常订单/);
  assert.match(html, /0\.000999/);
  assert.match(html, /-0\.000001/);
  assert.match(html, /处理该组合平仓/);
  assert.doesNotMatch(html, /跨所价差异常订单/);
});
