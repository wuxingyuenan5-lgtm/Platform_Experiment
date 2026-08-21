const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

test('cross spread execution workspace clears legacy default spreads', () => {
  const source = read('src/views/strategy/spread-carry/composables/useCrossVenueExecutionWorkspace.ts');
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

test('cross spread does not present a local leverage input as an executable venue setting', () => {
  const commandSource = read('src/views/strategy/spread-carry/components/SpreadExecutionCommand.vue');
  const workspaceSource = read('src/views/strategy/spread-carry/components/CrossVenueExecutionWorkspace.vue');
  const composableSource = read('src/views/strategy/spread-carry/composables/useCrossVenueExecutionWorkspace.ts');
  assert.equal(commandSource.includes('账户级（只读）'), true);
  assert.doesNotMatch(commandSource, /<span>BY 杠杆<\/span>/);
  assert.doesNotMatch(commandSource, /<span>MT5 杠杆<\/span>/);
  assert.doesNotMatch(workspaceSource, /handle-leverage-input/);
  assert.doesNotMatch(composableSource, /handleLeverageInput/);
});

test('cross spread finance composable uses dynamic bindings instead of hardcoded live accounts', () => {
  const source = read('src/views/strategy/management/composables/useCrossSpreadFinance.ts');
  assert.equal(source.includes('getStrategyAccountBindings'), true);
  assert.equal(source.includes('getEquityHistory'), true);
  assert.equal(source.includes('getTradingPnl'), true);
  assert.equal(source.includes('getCrossSpreadObservability'), true);
  assert.equal(source.includes('数据暂不可用'), true);
  assert.equal(source.includes('跨所总权益（Bybit + MT5，按当前 USDT/USD 折算）'), true);
  assert.equal(source.includes('历史已实现损益接口待对账'), true);
  assert.doesNotMatch(source, /new Date\(\)\.toISOString\(\)/);
  assert.doesNotMatch(source, /const BYBIT_ACCOUNT_ID = 'bybit-live-main';/);
  assert.doesNotMatch(source, /const MT5_ACCOUNT_ID = 'mt5-live-main';/);
});

test('strategy management wires full cross spread live profiles into pnl and capital views', () => {
  const indexSource = read('src/views/strategy/management/index.vue');
  const pnlSource = read('src/views/strategy/management/components/StrategyPnlPanel.vue');
  assert.equal(indexSource.includes(':live-profile="activeDesk === \'crossSpread\' ? pnlProfile : null"'), true);
  assert.equal(indexSource.includes('liveCapitalProfile'), true);
  assert.equal(pnlSource.includes('liveProfile?: StrategyPnlProfile | null;'), true);
  assert.equal(pnlSource.includes('props.liveProfile'), true);
  assert.doesNotMatch(pnlSource, /liveMetrics\?: Array</);
  assert.doesNotMatch(pnlSource, /liveTotalFund\?: string \| null;/);
});

test('strategy management honors the cross-spread route context before rendering profile data', () => {
  const source = read('src/views/strategy/management/index.vue');
  assert.equal(source.includes("useRoute"), true);
  assert.equal(source.includes("route.query.desk === 'crossSpread'"), true);
});

test('cross spread execution records preserve result-unknown and leg evidence', () => {
  const source = read('src/views/strategy/management/composables/useCrossSpreadRecords.ts');
  assert.equal(source.includes("result_unknown: '结果未知'"), true);
  assert.equal(source.includes('batchDisplayStatus'), true);
  assert.equal(source.includes("{ key: 'legStatus', label: '双腿状态' }"), true);
  assert.equal(source.includes("{ key: 'failureReason', label: '失败/未知原因' }"), true);
});
