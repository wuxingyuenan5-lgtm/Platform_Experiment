import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';

import { expect, test } from '@playwright/test';

const targetFiles = [
  'src/access/browserRouteCapabilities.ts',
  'src/access/userAccess.ts',
  'src/api/platform/userSystem.ts',
  'src/components/OptionTranslate/Text.tsx',
  'src/components/ProductDataState/RestoredProductDataBanner.vue',
  'src/components/ProductDataState/RestoredProductSurface.vue',
  'src/components/list/hook/useSearch.ts',
  'src/components/list/list.tsx',
  'src/components/list/props.ts',
  'src/components/list/types/type.ts',
  'src/data/productDataEnvelope.ts',
  'src/data/sample/dashboard/index.ts',
  'src/data/sample/funding/index.ts',
  'src/data/sample/news/index.ts',
  'src/data/sample/spread/index.ts',
  'src/data/sample/strategy/index.ts',
  'src/router/helper/routeHelper.ts',
  'src/router/routes/index.ts',
  'src/store/modules/projectConfig.ts',
  'src/views/dashboard/index.vue',
  'src/views/data/index.vue',
  'src/views/finance/index.vue',
  'src/views/financialAi/index.vue',
  'src/views/log/operate/index.vue',
  'src/views/monitor/index.vue',
  'src/views/newsCalendar/index.vue',
  'src/views/risk/detail/index.vue',
  'src/views/risk/home/components/networth.vue',
  'src/views/risk/product/overview/components/networthPie.vue',
  'src/views/risk/profile/security/modules.tsx',
  'src/views/settings/index.vue',
  'src/views/strategy/funding-carry/components/FundingChartPanel.vue',
  'src/views/strategy/funding-carry/components/FundingDetailPanel.vue',
  'src/views/strategy/funding-carry/components/FundingMarketBoard.vue',
  'src/views/strategy/funding-carry/components/FundingOrderPanel.vue',
  'src/views/strategy/funding-carry/index.vue',
  'src/views/strategy/management/components/StrategyCapitalFinanceBoard.vue',
  'src/views/strategy/management/components/StrategyCapitalNetValueBoard.vue',
  'src/views/strategy/management/components/StrategyCapitalRiskOverview.vue',
  'src/views/strategy/management/components/StrategyCapitalRulePanel.vue',
  'src/views/strategy/management/components/StrategyCurveGrid.vue',
  'src/views/strategy/management/components/StrategyKpiGrid.vue',
  'src/views/strategy/management/components/StrategyPnlPanel.vue',
  'src/views/strategy/management/components/StrategyRecordsPanel.vue',
  'src/views/strategy/management/components/StrategyRuntimePanel.vue',
  'src/views/strategy/management/index.vue',
  'src/views/strategy/spread-carry/components/SpreadAnalysisOverview.vue',
  'src/views/strategy/spread-carry/components/SpreadAnalysisWorkspaceHeader.vue',
  'src/views/strategy/spread-carry/components/SpreadStatisticsSection.vue',
  'src/views/strategy/spread-carry/composables/useCrossSpreadExecution.ts',
  'src/views/strategy/spread-carry/index.vue',
];

test('export repository-configured formatting for restored sources', async ({
  browserName,
}, testInfo) => {
  void browserName;
  const frontendRoot = path.resolve(__dirname, '../..');
  const existingTargetFiles = targetFiles.filter((file) =>
    existsSync(path.join(frontendRoot, file)),
  );
  const archivePath = path.join(
    frontendRoot,
    'test-results/platform-visual/formatted-sources.tar.gz',
  );

  expect(existingTargetFiles).toHaveLength(targetFiles.length);
  execFileSync('pnpm', ['exec', 'prettier', '--write', ...existingTargetFiles], {
    cwd: frontendRoot,
    stdio: 'inherit',
  });

  mkdirSync(path.dirname(archivePath), { recursive: true });
  execFileSync('tar', ['-czf', archivePath, ...existingTargetFiles], {
    cwd: frontendRoot,
    stdio: 'inherit',
  });

  await testInfo.attach('formatted-sources', {
    path: archivePath,
    contentType: 'application/gzip',
  });
});
