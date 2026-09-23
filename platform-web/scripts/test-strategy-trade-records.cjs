const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vue = require('vue');
const { parse, compileScript } = require('@vue/compiler-sfc');
const { renderToString } = require('vue/server-renderer');
const load = require('./load-strategy-module.cjs')();
const records = load('src/views/strategy/management/composables/strategyTradeRecords.ts');

const order = (changes = {}) => ({
  orderId: 'order-a',
  commandId: 'command-a',
  accountId: 'bybit-live-main',
  instrumentId: 'btc-perp',
  symbol: 'BTCUSDT',
  side: 'sell',
  orderType: 'market',
  quantity: '0.001',
  status: 'filled',
  createdAt: '2026-09-10T03:05:50Z',
  action: 'open',
  instructionId: 'instruction-a',
  ...changes,
});
const fill = (changes = {}) => ({
  fillId: 'fill-a',
  orderId: 'order-a',
  accountId: 'bybit-live-main',
  instrumentId: 'btc-perp',
  symbol: 'BTCUSDT',
  side: 'sell',
  quantity: '0.001',
  price: '110000.00000001',
  fee: null,
  occurredAt: '2026-09-10T03:05:51Z',
  origin: 'venue_execution',
  timeQuality: 'venue_time',
  instructionId: 'instruction-a',
  ...changes,
});

test('shared records preserve intent independently of side, exact money, and per-venue units', () => {
  const data = records.buildTradeRecords(
    [
      order(),
      order({
        orderId: 'order-b',
        action: 'close',
        accountId: 'mt5-main',
        symbol: 'XAUUSD.s',
        quantity: '0.01',
      }),
    ],
    [
      fill(),
      fill({
        fillId: 'fill-b',
        orderId: 'order-b',
        accountId: 'mt5-main',
        symbol: 'XAUUSD.s',
        quantity: '0.01',
        action: 'close',
      }),
    ],
  );
  assert.deepEqual(
    data.orders.rows.map((r) => r.action),
    ['开仓', '平仓'],
  );
  assert.deepEqual(
    data.fills.rows.map((r) => r.quantity),
    ['0.001 BTC', '0.01 手'],
  );
  assert.equal(data.fills.rows[0].price, '110000.00000001');
  assert.equal(data.fills.rows[0].fee, '--');
  assert.equal(data.activity.rows.length, 1);
  assert.equal(data.activity.rows[0].quantity, '2 笔委托 · 2 笔成交');
  assert.equal(data.activity.details['instruction-a'].sections[1].rows.length, 2);
});

test('order details expose realized pnl and native fee, funding, and swap costs', () => {
  const data = records.buildTradeRecords(
    [order({ action: 'close' })],
    [fill({ fee: '1', currency: 'USDT', realizedPnl: '10', swap: '0.2' })],
    [
      { eventType: 'funding', amount: '-0.3', currency: 'USDT', orderId: 'order-a' },
      // A fee event for an order with a native fill fee must not be counted twice.
      { eventType: 'fee', amount: '1', currency: 'USDT', orderId: 'order-a' },
    ],
  );
  const row = data.orders.rows[0];
  assert.equal(row.realizedPnl, '10 USDT');
  assert.match(row.costs, /手续费 1 USDT/);
  assert.match(row.costs, /资金费 -0.3 USDT/);
  assert.match(row.costs, /库存费 0.2 USDT/);
  assert.equal(row.netPnl, '8.9 USDT');
  assert.ok(data.orders.details['order-a'].fields.some((field) => field.label === '资金费'));
});

test('negative fee cash events are presented as positive costs when no fill fee exists', () => {
  const data = records.buildTradeRecords(
    [order()],
    [fill({ fee: null, realizedPnl: null, swap: null })],
    [{ eventType: 'fee', amount: '-0.25', currency: 'USDT', orderId: 'order-a' }],
  );
  assert.equal(data.orders.rows[0].costs, '手续费 0.25 USDT');
  assert.equal(data.orders.rows[0].netPnl, '-0.25 USDT');
});

test('clock conflict displays order confirmation explicitly and retains immutable source in details', () => {
  const data = records.buildTradeRecords(
    [order({ action: 'close' })],
    [
      fill({
        occurredAt: '2026-09-10T06:06:04.734Z',
        orderConfirmedAt: '2026-09-10T03:06:07.493Z',
        timeQuality: 'source_clock_conflict',
      }),
    ],
  );
  const row = data.fills.rows[0];
  assert.equal(row.time, '2026-09-10 11:06:07');
  assert.equal(row.timeLabel, '订单确认时间');
  assert.equal(row.timeWarning, '原始成交时间冲突');
  assert.ok(data.fills.details['fill-a'].fields.some((f) => f.value === '2026-09-10 14:06:04'));
  assert.equal(row.action, '平仓');
});

test('unowned monitoring records stay visible without inferring open/close or fabricating time', () => {
  const data = records.buildTradeRecords(
    [
      order({
        action: null,
        instructionId: null,
        timeQuality: 'source_clock_unverified',
        accountId: 'mt5-monitor',
      }),
    ],
    [
      fill({
        action: null,
        instructionId: null,
        timeQuality: 'source_clock_unverified',
      }),
    ],
  );
  assert.equal(data.orders.rows[0].action, '开平待核对');
  assert.equal(data.orders.rows[0].time, '--');
  assert.equal(data.fills.rows[0].time, '--');
  assert.equal(data.activity.rows.length, 1);
});

test('Beijing calendar filtering handles midnight, excludes unknown dates, and searches hidden IDs', () => {
  const row = {
    _timestamp: '2026-09-09T16:00:00Z',
    _search: 'native-123',
    _action: 'close',
    status: '已成交',
    venue: 'MT5',
  };
  const filters = {
    startDate: '2026-09-10',
    endDate: '2026-09-10',
    action: 'close',
    status: '已成交',
    venue: 'MT5',
    search: 'native-123',
  };
  assert.equal(records.recordDate(row), '2026-09-10');
  assert.equal(records.recordMatches(row, filters), true);
  assert.equal(
    records.recordMatches({ ...row, _timestamp: '2026-09-09T15:59:59Z' }, filters),
    false,
  );
  assert.equal(records.recordMatches({ ...row, _timestamp: '' }, filters), false);
  assert.equal(records.recordMatches(row, { ...filters, startDate: '2026-09-11' }), false);
  assert.equal(records.recordMatches(row, { ...filters, action: 'open' }), false);
});

test('fills outside the loaded order window still group by their own instruction without joining strangers', () => {
  const data = records.buildTradeRecords(
    [],
    [fill(), fill({ fillId: 'fill-b', orderId: 'other', instructionId: 'instruction-b' })],
  );
  assert.equal(data.activity.rows.length, 2);
});

function component() {
  const filename = path.resolve(
    __dirname,
    '../src/views/strategy/management/components/StrategyRecordsPanel.vue',
  );
  const { descriptor } = parse(fs.readFileSync(filename, 'utf8'), { filename });
  const output = compileScript(descriptor, { id: 'records-test', inlineTemplate: true });
  const code = ts.transpileModule(output.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const mod = { exports: {} };
  new Function('require', 'module', 'exports', code)(
    (name) => (name.includes('strategyTradeRecords') ? records : require(name)),
    mod,
    mod.exports,
  );
  return mod.exports.default;
}

test('shared panel renders opening/closing labels and search controls with identifiers behind details', async () => {
  const panel = component();
  const tables = records.buildTradeRecords([order()], [fill()]);
  const html = await renderToString(
    vue.createSSRApp({
      render: () =>
        vue.h(panel, {
          tabs: [{ key: 'fills', label: '逐笔成交' }],
          activeTab: 'fills',
          tables,
        }),
    }),
  );
  assert.match(html, /开仓/);
  assert.match(html, /北京时间/);
  assert.match(html, /aria-expanded="false"/);
  assert.doesNotMatch(html, /instruction-a|order-a|fill-a/);
  const positions = await renderToString(
    vue.createSSRApp({
      render: () =>
        vue.h(panel, {
          tabs: [{ key: 'positions', label: '当前持仓' }],
          activeTab: 'positions',
          tables: {
            positions: {
              columns: [{ key: 'instrumentId', label: '标的' }],
              rows: [{ instrumentId: 'BTCUSDT' }],
            },
          },
        }),
    }),
  );
  assert.match(positions, /BTCUSDT/);
});
