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
const fundingStatusPanelPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'funding-carry',
  'components',
  'FundingStatusPanel.vue',
);
const fundingPositionsPanelPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'funding-carry',
  'components',
  'FundingPositionsPanel.vue',
);
const fundingExecutionPanelPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'funding-carry',
  'components',
  'FundingExecutionPanel.vue',
);

const fundingOrderPanelSource = fs.readFileSync(fundingOrderPanelPath, 'utf8');
const fundingStatusPanelSource = fs.readFileSync(fundingStatusPanelPath, 'utf8');
const fundingPositionsPanelSource = fs.readFileSync(fundingPositionsPanelPath, 'utf8');
const fundingExecutionPanelSource = fs.readFileSync(fundingExecutionPanelPath, 'utf8');

assert(
  fundingOrderPanelSource.includes('FundingStatusPanel'),
  'FundingOrderPanel must mount the extracted FundingStatusPanel.',
);
assert(
  fundingOrderPanelSource.includes('FundingPositionsPanel'),
  'FundingOrderPanel must mount the extracted FundingPositionsPanel.',
);
assert(
  fundingOrderPanelSource.includes('FundingExecutionPanel'),
  'FundingOrderPanel must mount the extracted FundingExecutionPanel.',
);

assert(
  !fundingOrderPanelSource.includes('class="status-feedback"') &&
    !fundingOrderPanelSource.includes('.status-feedback') &&
    !fundingOrderPanelSource.includes('class="rule-list"') &&
    !fundingOrderPanelSource.includes('.rule-list'),
  'FundingOrderPanel must not inline trading-rule or execution-feedback markup/styles.',
);
assert(
  !fundingOrderPanelSource.includes('positionRows') &&
    !fundingOrderPanelSource.includes('class="positions-table"') &&
    !fundingOrderPanelSource.includes('.positions-table') &&
    !fundingOrderPanelSource.includes('class="positions-metric"') &&
    !fundingOrderPanelSource.includes('.positions-metric'),
  'FundingOrderPanel must not inline positions summary markup, styles, or data.',
);
assert(
  !fundingOrderPanelSource.includes('class="order-panel"') &&
    !fundingOrderPanelSource.includes('class="funding-order-grid"') &&
    !fundingOrderPanelSource.includes('class="funding-close-table"') &&
    !fundingOrderPanelSource.includes('.funding-order-grid') &&
    !fundingOrderPanelSource.includes('.funding-close-table') &&
    !fundingOrderPanelSource.includes('.input-with-unit'),
  'FundingOrderPanel must not inline execution order form markup or styles.',
);

assert(
  fundingStatusPanelSource.includes('status-feedback') && fundingStatusPanelSource.includes('rule-list'),
  'FundingStatusPanel must own trading-rule and execution-feedback rendering.',
);
assert(
  fundingPositionsPanelSource.includes('positions-table') && fundingPositionsPanelSource.includes('positionRows'),
  'FundingPositionsPanel must own positions summary rendering and seed rows.',
);
assert(
  fundingExecutionPanelSource.includes('funding-order-grid') &&
    fundingExecutionPanelSource.includes('funding-close-table'),
  'FundingExecutionPanel must own execution order and close-position rendering.',
);

console.log('Funding order layout checks passed.');
