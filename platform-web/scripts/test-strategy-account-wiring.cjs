const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = process.cwd();
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), 'utf8');

const management = read('src/views/strategy/management/index.vue');
const snapshots = read('src/views/strategy/management/composables/useStrategyAccountSnapshots.ts');
const presentation = read(
  'src/views/strategy/management/composables/strategyFinancialPresentation.ts',
);
const overview = read('src/views/strategy/management/composables/useStrategyManagementOverview.ts');
const overviewState = read(
  'src/views/strategy/management/composables/strategyManagementOverviewState.ts',
);

assert.match(management, /useStrategyAccountSnapshots/);
assert.match(management, /useStrategyManagementOverview/);
assert.match(management, /accountPnlProfiles/);
assert.match(management, /accountCapitalProfiles/);
assert.match(management, /accountOrderProfiles/);
assert.match(overview, /getStrategyManagementOverview/);
assert.match(overview, /useQuery/);
assert.match(overviewState, /resolveManagementDesk/);

for (const [desk, instanceId] of Object.entries({
  funding: 'strategy_funding_arbitrage_instance_default',
  dip: 'strategy_bottom_fishing_instance_default',
  shortLineTraderL: 'strategy_short_term_l_instance_default',
  shortLineTraderW: 'strategy_short_term_w_instance_default',
})) {
  assert.match(snapshots, new RegExp(`${desk}: '${instanceId}'`));
}

assert.match(snapshots, /getStrategyAccountSnapshot/);
assert.match(presentation, /暂未绑定账号/);
assert.match(presentation, /等待首次同步/);
assert.match(presentation, /账户身份校验失败/);
assert.match(presentation, /主账号恢复失败/);
assert.match(snapshots, /financialProfile/);
assert.match(presentation, /原币资产/);
assert.doesNotMatch(snapshots, /venue: 'Bybit'/);
assert.doesNotMatch(snapshots, /Bybit 账户/);
assert.doesNotMatch(snapshots, /2,984,316\.97|511,986\.31|4,502,541\.72/);

console.log('strategy account API wiring checks passed');
