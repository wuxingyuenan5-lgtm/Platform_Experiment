const fs = require('fs');
const path = require('path');
const assert = require('assert');

const fundingOrderPanelPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'funding-carry',
  'components',
  'FundingOrderPanel.vue',
);

const fundingOrderPanelSource = fs.readFileSync(fundingOrderPanelPath, 'utf8');

assert(
  fundingOrderPanelSource.includes('status-panel'),
  'FundingOrderPanel must own the trading-rule and execution-feedback panel.',
);

assert(
  fundingOrderPanelSource.includes('status-feedback') &&
    fundingOrderPanelSource.includes('rule-list'),
  'FundingOrderPanel must own trading-rule and execution-feedback rendering.',
);
assert(
  fundingOrderPanelSource.includes('positions-table') &&
    fundingOrderPanelSource.includes('positions-metrics'),
  'FundingOrderPanel must own positions summary rendering.',
);
assert(
  fundingOrderPanelSource.includes('funding-order-grid') &&
    fundingOrderPanelSource.includes('funding-close-table'),
  'FundingOrderPanel must own execution order and close-position rendering.',
);

assert(
  fundingOrderPanelSource.includes('status-feedback') &&
    fundingOrderPanelSource.includes('rule-list') &&
    fundingOrderPanelSource.includes('positions-table') &&
    fundingOrderPanelSource.includes('funding-order-grid') &&
    fundingOrderPanelSource.includes('funding-close-table'),
  'FundingOrderPanel must retain the current funding status, positions, execution, and close sections.',
);

console.log('Funding order layout checks passed.');
