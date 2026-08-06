import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

import { test } from '@playwright/test';

const targetFiles = [
  'src/access/browserRouteCapabilities.ts',
  'src/components/ProductDataState/RestoredProductDataBanner.vue',
  'src/data/sample/newsCalendar.ts',
  'src/data/sample/spreadCarry.ts',
  'src/views/dashboard/index.vue',
  'src/views/financialAi/index.vue',
  'src/views/log/operate/index.vue',
  'src/views/monitor/index.vue',
  'src/views/newsCalendar/index.vue',
  'src/views/risk/detail/index.vue',
  'src/views/risk/home/networth.vue',
  'src/views/risk/product/modules/networthPie.vue',
  'src/views/risk/profile/security/modules.tsx',
  'src/views/settings/index.vue',
  'src/views/strategy/funding-carry/components/Chart.vue',
  'src/views/strategy/funding-carry/components/Detail.vue',
  'src/views/strategy/funding-carry/components/Market.vue',
  'src/views/strategy/funding-carry/components/Order.vue',
  'src/views/strategy/funding-carry/index.vue',
  'src/views/strategy/management/components/NetValue.vue',
  'src/views/strategy/management/components/NetValue/CurveGrid.vue',
  'src/views/strategy/management/components/Records.vue',
  'src/views/strategy/spread-carry/components/Overview.vue',
  'src/views/strategy/spread-carry/components/SpreadHeader.vue',
  'src/views/strategy/spread-carry/components/Statistics.vue',
  'src/views/strategy/spread-carry/index.vue',
];

test('export repository-configured formatting for restored sources', async ({ browserName }, testInfo) => {
  void browserName;
  const frontendRoot = path.resolve(__dirname, '../..');
  const archivePath = path.join(
    frontendRoot,
    'test-results/platform-visual/formatted-sources.tar.gz',
  );

  execFileSync('pnpm', ['exec', 'prettier', '--write', ...targetFiles], {
    cwd: frontendRoot,
    stdio: 'inherit',
  });

  mkdirSync(path.dirname(archivePath), { recursive: true });
  execFileSync('tar', ['-czf', archivePath, ...targetFiles], {
    cwd: frontendRoot,
    stdio: 'inherit',
  });

  await testInfo.attach('formatted-sources', {
    path: archivePath,
    contentType: 'application/gzip',
  });
});
