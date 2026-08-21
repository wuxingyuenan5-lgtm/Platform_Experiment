const fs = require('fs');
const path = require('path');
const assert = require('assert');

const componentPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueExecutionWorkspace.vue',
);
const retiredReplicaPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueExecutionReplica.vue',
);
const workspaceComposablePath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'composables',
  'useCrossVenueExecutionWorkspace.ts',
);
const workspacePath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueExecutionWorkspace.vue',
);
const spreadCarryPagePath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'index.vue',
);
const marketQuotesPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueMarketQuotes.vue',
);
const spreadSummaryPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueSpreadSummary.vue',
);
const spreadChartPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueSpreadChart.vue',
);
const spreadAnalysisPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueSpreadAnalysis.vue',
);
const tradingRulesPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'CrossVenueTradingRules.vue',
);
const positionOverviewPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'SpreadPositionOverview.vue',
);
const confirmModalPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'SpreadExecutionConfirmModal.vue',
);
const executionCommandPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'components',
  'SpreadExecutionCommand.vue',
);
const composablesDir = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'strategy',
  'spread-carry',
  'composables',
);
const requiredComposables = [
  'useCrossSpreadExecution.ts',
  'useCrossSpreadExitPlans.ts',
  'useCrossSpreadFormatting.ts',
  'useCrossSpreadObservability.ts',
  'useCrossSpreadPositions.ts',
];
const pageComposables = requiredComposables.filter(
  (fileName) => fileName !== 'useCrossSpreadFormatting.ts',
);
const requiredSupportFiles = ['crossSpreadFixtures.ts'];
const requiredMapperFiles = ['mapCrossSpreadPositions.ts'];

assert(!fs.existsSync(retiredReplicaPath), 'Retired CrossVenueExecutionReplica must remain removed.');
const source = fs.readFileSync(componentPath, 'utf8');
const workspaceComposableSource = fs.readFileSync(workspaceComposablePath, 'utf8');
const workspaceSource = fs.readFileSync(workspacePath, 'utf8');
const spreadCarryPageSource = fs.readFileSync(spreadCarryPagePath, 'utf8');
const mountedProductSources = [
  source,
  spreadCarryPageSource,
  workspaceSource,
  fs.readFileSync(marketQuotesPath, 'utf8'),
  fs.readFileSync(spreadSummaryPath, 'utf8'),
  fs.readFileSync(spreadChartPath, 'utf8'),
  fs.readFileSync(spreadAnalysisPath, 'utf8'),
  fs.readFileSync(tradingRulesPath, 'utf8'),
  fs.readFileSync(positionOverviewPath, 'utf8'),
  fs.readFileSync(confirmModalPath, 'utf8'),
  fs.readFileSync(executionCommandPath, 'utf8'),
];

const bannedProductCopy = [
  '设计保留',
  '真实执行请',
  '保护口径',
  '下方运行区',
  '原市价',
  '验收面板',
  'LIVE OBSERVABILITY',
  'SYNTHETIC LIFECYCLE',
];

for (const phrase of bannedProductCopy) {
  assert(
    mountedProductSources.every((productSource) => !productSource.includes(phrase)),
    `Product page must not include engineering copy: ${phrase}`,
  );
}

const bannedMountedPanels = [
  'CrossSpreadMarketLifecyclePanel',
  'CrossSpreadLiveObservabilityPanel',
];
for (const panel of bannedMountedPanels) {
  assert(
    !workspaceSource.includes(panel),
    `SpreadExecutionWorkspace must not mount deprecated panel: ${panel}`,
  );
}

assert(
  source.includes("import { useCrossVenueExecutionWorkspace } from '../composables/useCrossVenueExecutionWorkspace';") &&
    source.includes('useCrossVenueExecutionWorkspace()'),
  'CrossVenueExecutionWorkspace must delegate state and effects to its formal composable owner.',
);

const marketQuotesSource = fs.readFileSync(marketQuotesPath, 'utf8');
const spreadSummarySource = fs.readFileSync(spreadSummaryPath, 'utf8');

assert(
  source.includes('CrossVenueMarketQuotes') &&
    source.includes('CrossVenueSpreadSummary') &&
    source.includes('CrossVenueSpreadChart') &&
    source.includes('CrossVenueSpreadAnalysis') &&
    source.includes('CrossVenueTradingRules') &&
    source.includes('SpreadPositionOverview') &&
    source.includes('SpreadExecutionCommand') &&
    source.includes('SpreadExecutionConfirmModal'),
  'Expected formal cross venue workspace to use extracted pure display components.',
);

assert(
  spreadCarryPageSource.includes('CrossVenueExecutionWorkspace') &&
    spreadCarryPageSource.includes('DomesticOverseasExecutionWorkspace') &&
    spreadCarryPageSource.includes('DomesticOverseasMarketInsight'),
  'Expected spread-carry page to mount the formal execution and domestic/overseas workspace components.',
);

for (const fileName of requiredComposables) {
  const composablePath = path.join(composablesDir, fileName);
  assert(fs.existsSync(composablePath), `Expected composable to exist: ${fileName}`);
}

for (const fileName of requiredSupportFiles) {
  const supportPath = path.join(composablesDir, fileName);
  assert(fs.existsSync(supportPath), `Expected support file to exist: ${fileName}`);
  assert(
    workspaceComposableSource.includes(fileName.replace(/\.ts$/, '')),
    `Expected cross venue composable to use support file: ${fileName}`,
  );
}

for (const fileName of requiredMapperFiles) {
  const mapperPath = path.join(composablesDir, fileName);
  assert(fs.existsSync(mapperPath), `Expected mapper file to exist: ${fileName}`);
}

for (const fileName of pageComposables) {
  assert(
    workspaceComposableSource.includes(fileName.replace(/\.ts$/, '')),
    `Expected cross venue formal owner to compose: ${fileName}`,
  );
}

const baseQuoteStatsRule = marketQuotesSource.match(/\.quote-stats\s*\{[\s\S]*?\n  \}/m);
assert(baseQuoteStatsRule, 'Could not find the base .quote-stats rule.');
assert.match(
  baseQuoteStatsRule[0],
  /grid-template-columns:\s*repeat\(4,\s*minmax\(0,\s*1fr\)\);/m,
  'Expected the base quote stats layout to preserve the original 4-column layout.',
);

const compactSummaryRule = spreadSummarySource.match(/\.summary-item--compact strong\s*\{[\s\S]*?\n  \}/m);
assert(compactSummaryRule, 'Could not find the .summary-item--compact strong rule.');
assert.match(
  compactSummaryRule[0],
  /font-size:\s*16px;/m,
  'Expected compact summary metrics to use a unified 16px font size.',
);

const summaryStrongRule = spreadSummarySource.match(/\.summary-item strong\s*\{[\s\S]*?\n  \}/m);
assert(summaryStrongRule, 'Could not find the .summary-item strong rule.');
assert.match(
  summaryStrongRule[0],
  /font-size:\s*16px;/m,
  'Expected summary metrics to align to the same 16px font size.',
);

assert.match(
  spreadSummarySource,
  /\.(?:green|red)[\s\S]*?color:\s*var\(--strategy-text-1\)\s*!important;/m,
  'Expected summary card numbers to override special red/green colors with the default text color.',
);

console.log('Cross spread layout checks passed.');
