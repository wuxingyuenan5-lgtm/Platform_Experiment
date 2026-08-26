const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const component = fs.readFileSync(
  path.join(
    root,
    'src/views/strategy/spread-carry/components/SpreadExecutionCommand.vue',
  ),
  'utf8',
);
const workspace = fs.readFileSync(
  path.join(
    root,
    'src/views/strategy/spread-carry/composables/useCrossVenueExecutionWorkspace.ts',
  ),
  'utf8',
);
const funding = fs.readFileSync(
  path.join(
    root,
    'src/views/strategy/spread-carry/composables/useCrossSpreadFundingTransfer.ts',
  ),
  'utf8',
);
const api = fs.readFileSync(
  path.join(root, 'src/api/platform/crossSpreadFundingTransfer.ts'),
  'utf8',
);

for (const label of ['开仓价差', '平仓价差', '移动双边资金']) {
  assert.match(component, new RegExp(label));
}
assert.match(workspace, /ref<'open' \| 'close' \| 'funding'>\('open'\)/);
assert.match(component, /v-if="executionStage === 'open'"/);
assert.match(component, /v-else-if="executionStage === 'close'"/);
assert.match(component, /useCrossSpreadFundingTransfer\(\)/);
assert.match(funding, /new Decimal\(bybitTransferable\)/);
assert.match(funding, /\.abs\(\)\.div\(2\)/);
assert.match(funding, /Decimal\.min/);
assert.match(funding, /manuallyEdited/);
assert.match(component, /手工换向/);
assert.match(component, /刷新并核对两边余额/);
assert.match(component, /自动划转暂不可用/);
assert.doesNotMatch(component, /打开 Bybit 官方资金页|辅助调拨|一键复制金额/);
assert.match(funding, /quote\.value\?\.mode === 'automated'/);
assert.match(api, /idempotencyKey: string;\s+direction: FundingTransferDirection;\s+amount: string;/);
assert.match(api, /mode: 'automated' \| 'unavailable'/);
assert.doesNotMatch(api, /uid:|accountId:|apiKey:|mt5Login:/i);

console.log('cross-spread funding-transfer template checks passed');
