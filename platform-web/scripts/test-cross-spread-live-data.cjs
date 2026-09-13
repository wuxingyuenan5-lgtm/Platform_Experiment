const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

test('cross spread execution workspace clears legacy default spreads', () => {
  const source = read(
    'src/views/strategy/spread-carry/composables/useCrossVenueExecutionWorkspace.ts',
  );
  assert.match(source, /const triggerSpread = ref<[^>]+>\(null\);/);
  assert.match(source, /const acceptableSpread = ref<[^>]+>\(null\);/);
  assert.match(source, /const takeProfitSpread = ref<[^>]+>\(null\);/);
  assert.match(source, /const stopLossSpread = ref<[^>]+>\(null\);/);
  assert.match(source, /const closeLimitSpread = ref<[^>]+>\(null\);/);
  assert.doesNotMatch(source, /const triggerSpread = ref\(-1\);/);
  assert.doesNotMatch(source, /const acceptableSpread = ref\(-1\.1\);/);
  assert.doesNotMatch(source, /const takeProfitSpread = ref\(-1\);/);
  assert.doesNotMatch(source, /const stopLossSpread = ref\(-20\);/);
  assert.doesNotMatch(source, /const closeLimitSpread = ref\(-1\.9\);/);
});

test('cross spread execution surfaces concrete latency and removes stale review header copy', () => {
  const quoteSource = read('src/views/strategy/spread-carry/components/CrossVenueMarketQuotes.vue');
  const pageSource = read('src/views/strategy/spread-carry/index.vue');
  assert.equal(quoteSource.includes('formatLatencyMs'), true);
  assert.doesNotMatch(quoteSource, /return '可用';/);
  assert.doesNotMatch(pageSource, /待复核/);
  assert.doesNotMatch(pageSource, /交易执行<\/strong>/);
});

test('cross spread stop-loss and take-profit controls use stacked execution rows', () => {
  const source = read('src/views/strategy/spread-carry/components/SpreadExecutionCommand.vue');
  assert.equal(source.includes('risk-stack'), true);
  assert.equal(source.includes('field-block--stacked'), true);
  assert.equal(source.includes('stacked-select'), true);
});

test('cross spread open command shows both authoritative account balances above execution mode', () => {
  const commandSource = read(
    'src/views/strategy/spread-carry/components/SpreadExecutionCommand.vue',
  );
  const workspaceSource = read(
    'src/views/strategy/spread-carry/components/CrossVenueExecutionWorkspace.vue',
  );
  const balanceStripIndex = commandSource.indexOf('account-balance-strip');
  const marketModeIndex = commandSource.indexOf('市价开仓');
  assert.ok(balanceStripIndex >= 0 && balanceStripIndex < marketModeIndex);
  assert.equal(commandSource.includes('Bybit 账户权益'), true);
  assert.equal(commandSource.includes('MT5 账户资金'), true);
  assert.equal(commandSource.includes('可用资金'), true);
  assert.equal(
    workspaceSource.includes(':bybit-account-risk="observability?.bybit.accountRisk || null"'),
    true,
  );
  assert.equal(
    workspaceSource.includes(':mt5-account-risk="observability?.mt5.accountRisk || null"'),
    true,
  );
});

test('cross spread leverage uses authenticated platform route without a direct runtime URL', () => {
  const commandSource = read(
    'src/views/strategy/spread-carry/components/SpreadExecutionCommand.vue',
  );
  const workspaceSource = read(
    'src/views/strategy/spread-carry/components/CrossVenueExecutionWorkspace.vue',
  );
  const composableSource = read(
    'src/views/strategy/spread-carry/composables/useCrossVenueExecutionWorkspace.ts',
  );
  assert.equal(commandSource.includes('setCrossSpreadLeverage'), true);
  assert.doesNotMatch(commandSource, /127\.0\.0\.1:8100|accountId: 'bybit-live-main'/);
  assert.doesNotMatch(commandSource, /<span>BY 杠杆<\/span>/);
  assert.doesNotMatch(commandSource, /<span>MT5 杠杆<\/span>/);
  assert.doesNotMatch(workspaceSource, /handle-leverage-input/);
  assert.doesNotMatch(composableSource, /handleLeverageInput/);
});

test('cross spread finance composable uses dynamic bindings instead of hardcoded live accounts', () => {
  const source = read('src/views/strategy/management/composables/useCrossSpreadFinance.ts');
  assert.equal(source.includes('getStrategyAccountBindings'), true);
  assert.equal(source.includes('getStrategyAccountSnapshot'), true);
  assert.equal(source.includes('getStrategyPnl'), true);
  assert.equal(source.includes('financialProfile'), true);
  assert.equal(source.includes('accountCapitalProfile'), true);
  assert.equal(source.includes('account?.equityHistory'), true);
  assert.equal(source.includes('isStale: true'), true);
  assert.doesNotMatch(
    source,
    /canonicalStrategyFills|contractMultipliers|getCrossSpreadObservability/,
  );
  assert.doesNotMatch(source, /跨所总权益（Bybit \+ MT5/);
  assert.doesNotMatch(source, /const verifiedHistoryAvailable = computed\(\(\) => false\)/);
  assert.doesNotMatch(source, /const curvePoints = computed<[\s\S]*?>\(\(\) => \[\]\);/);
  assert.doesNotMatch(source, /new Date\(\)\.toISOString\(\)/);
  assert.doesNotMatch(source, /const BYBIT_ACCOUNT_ID = 'bybit-live-main';/);
  assert.doesNotMatch(source, /const MT5_ACCOUNT_ID = 'mt5-live-main';/);
});

test('strategy management wires full cross spread live profiles into pnl and capital views', () => {
  const indexSource = read('src/views/strategy/management/index.vue');
  const pnlSource = read('src/views/strategy/management/components/StrategyPnlPanel.vue');
  assert.equal(
    indexSource.includes("if (activeDesk.value === 'crossSpread') return pnlProfile.value;"),
    true,
  );
  assert.equal(indexSource.includes('liveCapitalProfile'), true);
  assert.equal(pnlSource.includes('liveProfile?: StrategyPnlProfile | null;'), true);
  assert.equal(pnlSource.includes('props.liveProfile'), true);
  assert.doesNotMatch(pnlSource, /liveMetrics\?: Array</);
  assert.doesNotMatch(pnlSource, /liveTotalFund\?: string \| null;/);
});

test('cross spread daily P&L combines the two strategy legs by date', () => {
  const source = read(
    'src/views/strategy/management/composables/useCrossSpreadFinance.ts',
  );
  assert.equal(source.includes('export function mergeCrossDailyPnl'), true);
  assert.equal(source.includes('dailyPnl: mergeCrossDailyPnl(accounts.value)'), true);
  assert.equal(source.includes('const complete = rows.length === snapshots.length'), true);
  assert.equal(source.includes('returnRate:'), true);
});

test('strategy management honors the cross-spread route context before rendering profile data', () => {
  const source = read('src/views/strategy/management/index.vue');
  assert.equal(source.includes('useRoute'), true);
  assert.equal(source.includes('route.query.desk'), true);
  assert.equal(source.includes('router.replace'), true);
  assert.equal(source.includes('route.query.section'), true);
});

test('cross spread execution records preserve result-unknown and leg evidence', () => {
  const source = read('src/views/strategy/management/composables/useCrossSpreadRecords.ts');
  assert.equal(source.includes("result_unknown: '结果未知'"), true);
  assert.equal(source.includes('getExecutionBatches(STRATEGY_INSTANCE_ID)'), true);
  assert.equal(source.includes('getFills(STRATEGY_INSTANCE_ID)'), true);
  assert.equal(source.includes('batchDisplayStatus'), true);
  assert.equal(source.includes("{ key: 'legStatus', label: '双腿状态' }"), true);
  assert.equal(source.includes("{ key: 'failureReason', label: '失败/未知原因' }"), true);
});

test('management renders canonical fills and native cash exactly across refreshes', async () => {
  const createLoader = require('./load-strategy-module.cjs');
  const calls = [];
  const fills = ['native-one', 'native-two'].map((externalFillId, index) => ({
    fillId: `scoped-${index}`,
    externalFillId,
    orderId: 'full-order-identity',
    instructionId: 'full-instruction-identity',
    origin: 'venue_execution',
    source: 'bybit',
    instrumentId: 'XAUTUSDT',
    side: 'buy',
    quantity: '0.5',
    price: '100.1',
    fee: index ? null : '0.123456789123456789',
    currency: 'USDT',
  }));
  const load = createLoader({
    '@/api/platform/trading': {
      getOrders: async (id) => {
        calls.push(id);
        return [];
      },
      getFills: async (id) => {
        calls.push(id);
        return fills;
      },
      getExecutionBatches: async () => [],
      // 记录刷新会同时读取跨所快照；本用例只校验成交与原生现金口径，
      // 因此返回结构完整但空仓位的快照，不引入额外持仓行。
      getCrossSpreadSnapshot: async () => ({
        bybit: { symbol: 'XAUTUSDT', positions: [] },
        mt5: { symbol: 'XAUUSD.S', positions: [] },
        positionOverview: { abnormalOrders: [], groups: [] },
      }),
      getStrategyPnl: async () => ({
        economicEvents: [
          {
            externalEventId: 'native-rebate',
            orderId: 'full-order-identity',
            instructionId: 'full-instruction-identity',
            eventType: 'fee',
            amount: '0.02',
            currency: 'USDT',
            source: 'bybit',
          },
        ],
      }),
    },
    '@/api/platform/crossSpreadObservability': {
      getCrossSpreadObservability: async () => ({ bybit: { fills: [...fills, ...fills] } }),
    },
  });
  const { useCrossSpreadRecords } = load(
    'src/views/strategy/management/composables/useCrossSpreadRecords.ts',
  );
  const records = useCrossSpreadRecords();
  for (let refresh = 0; refresh < 2; refresh++) {
    await records.refresh();
    assert.equal(records.error.value, '');
    const rows = records.tables.value.fills.rows;
    assert.equal(rows.length, 2);
    assert.deepEqual(
      rows.map((row) => row.fillId),
      ['native-one', 'native-two'],
    );
    assert.equal(rows[0].fee, '0.123456789123456789 USDT');
    assert.equal(rows[1].fee, '--');
    assert.equal(rows[0].instructionId, 'full-instruction-identity');
    assert.equal(records.tables.value.settlements.rows[0].amount, '0.02 USDT');
  }
  assert.ok(calls.every((id) => id === 'strategy_cross_venue_spread_instance_default'));
});

test('strategy order-information tabs place fills before historical orders', () => {
  const blocks = [
    [
      read('src/views/strategy/management/composables/useCrossSpreadRecords.ts'),
      'const crossSpreadTabs',
    ],
    [
      read('src/views/strategy/management/composables/useStrategyAccountSnapshots.ts'),
      'label: `${labels[desk]}订单信息`',
    ],
    [
      read('src/views/strategy/management/index.vue'),
      'label: `${overview?.strategyName || desk}订单信息`',
    ],
    [read('src/data/sample/strategy/orders.ts'), 'const commonTabs'],
    [read('src/data/sample/strategy/orders.ts'), 'const fundingTabs'],
    [read('src/data/sample/strategy/orders.ts'), 'const twoLegTabs'],
    [
      read('src/views/strategy/spread-carry/components/DomesticOverseasExecutionWorkspace.vue'),
      'const tableTabs',
    ],
  ];
  for (const [source, marker] of blocks) {
    const block = source.slice(source.indexOf(marker), source.indexOf(marker) + 800);
    const fillsIndex = block.indexOf("key: 'fills'");
    const historyIndex = Math.min(
      ...['history', 'orders', 'spotHistory', 'leftHistory', 'contractHistory', 'rightHistory'].map(
        (key) => {
          const index = block.indexOf(`key: '${key}'`);
          return index < 0 ? Number.POSITIVE_INFINITY : index;
        },
      ),
    );
    assert.ok(fillsIndex >= 0, `${marker} must expose fills`);
    assert.ok(fillsIndex < historyIndex, `${marker} must place fills before historical orders`);
  }
});
