import { expect, test } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

test('cross-asset entry uses real archive API, filters, charts, imports and account-scoped persistence', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  const target = '/#/hedge-board/macro?view=cross-asset-screening';
  await page.goto(target);
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  const archiveResponse = page.waitForResponse((r) =>
    r.url().includes('/research/macro/cross-asset-screening'),
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const response = await archiveResponse;
  expect(response.status()).toBe(200);
  const archive = await response.json();
  expect(archive.snapshot.series).toHaveLength(48);
  const panel = page.locator('section.cross-asset-screening').first();
  const openMatrix = () => panel.getByRole('button', { name: '趋势矩阵', exact: true }).click();
  await openMatrix();
  await expect(panel.getByRole('heading', { name: '跨资产筛选', exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: '跨资产筛选', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await expect(panel.locator('.screening-results')).toContainText('12个符合条件');
  await expect(panel.locator('.screening-source')).toContainText('非实时行情');
  const matrix = panel.getByRole('region', { name: '四周期趋势矩阵' });
  await expect(matrix.locator('tbody tr')).toHaveCount(12);
  const nativeApple = archive.snapshot.series.find((s) => s.symbol === 'AAPL' && s.frame === '1D');
  const appleClose = nativeApple.bars.at(nativeApple.lastBarComplete === true ? -1 : -2).c;
  await expect(
    matrix.locator('tr').filter({ has: page.getByRole('button', { name: 'AAPL', exact: true }) }),
  ).toContainText('参考收盘 $' + appleClose.toFixed(2));
  await panel.getByRole('button', { name: '四周期偏多筛选', exact: true }).click();
  await expect(panel.getByLabel('结构', { exact: true })).toHaveValue('bull');
  await expect(matrix.locator('tbody tr')).toHaveCount(2);
  await panel.getByRole('button', { name: '清除四周期偏多', exact: true }).click();
  await expect(matrix.locator('tbody tr')).toHaveCount(12);
  await panel.getByPlaceholder('代码、名称或分类').fill('NVDA');
  await expect(matrix.locator('tbody tr')).toHaveCount(1);
  await expect(matrix).toContainText('NVDA');
  await panel.getByRole('button', { name: '重置筛选', exact: true }).click();
  await panel.locator('.trend-builder summary').click();
  await panel.getByLabel('日线当前方向', { exact: true }).selectOption('多');
  await panel.getByPlaceholder('保存当前条件').fill('原包对照方案');
  await panel.getByRole('button', { name: '保存为新方案', exact: true }).click();
  await panel.getByLabel('我的趋势方案', { exact: true }).selectOption({ label: '原包对照方案' });
  await panel.getByLabel('趋势方案新名称', { exact: true }).fill('原包对照改名');
  await panel.getByRole('button', { name: '重命名方案', exact: true }).click();
  await expect(panel.getByLabel('我的趋势方案', { exact: true })).toContainText('原包对照改名');
  await panel.getByRole('button', { name: '清除日线条件', exact: true }).click();
  await expect(panel.getByLabel('日线当前方向', { exact: true })).toHaveValue('any');
  await panel.getByRole('button', { name: '用当前条件更新方案', exact: true }).click();
  await panel.getByRole('button', { name: '重置筛选', exact: true }).click();
  await panel.locator('.trend-builder summary').click();
  await panel.getByLabel('资产类型', { exact: true }).selectOption('stock');
  await expect(matrix.locator('tbody tr')).toHaveCount(2);
  await panel.getByRole('button', { name: '重置筛选', exact: true }).click();
  await panel.locator('.screening-watchlists summary').click();
  await panel.getByPlaceholder('例如：跨资产观察').fill('验证清单');
  await panel.getByRole('button', { name: '创建清单', exact: true }).click();
  await expect(matrix).toContainText('暂无符合条件');
  await panel.getByLabel('自选清单', { exact: true }).selectOption('');
  await matrix.getByLabel('选择AAPL', { exact: true }).check();
  await matrix.getByLabel('选择NVDA', { exact: true }).check();
  await panel.getByLabel('自选清单', { exact: true }).selectOption({ label: '验证清单（0）' });
  await panel.getByRole('button', { name: '加入已选 2', exact: true }).click();
  await expect(matrix.locator('tbody tr')).toHaveCount(2);
  await page.reload();
  await openMatrix();
  await expect(matrix.locator('tbody tr')).toHaveCount(2);
  await expect(panel.getByLabel('自选清单', { exact: true })).toHaveValue(/.+/);
  await panel.getByRole('button', { name: '重置筛选', exact: true }).click();

  await matrix.getByRole('button', { name: 'AAPL', exact: true }).click();
  const chartDialog = page.getByRole('dialog').last();
  await expect(chartDialog.locator('.trend-chart svg')).toHaveCount(1);
  const expand = chartDialog.getByRole('button', { name: /^放大图表：/ }).first();
  const chartHost = chartDialog.locator('.trend-chart').first();
  const originalWidth = (await chartHost.boundingBox())!.width;
  await expand.click();
  const fullscreen = page.locator('.screening-chart-expand dialog:modal');
  await expect(fullscreen).toBeVisible();
  await expect(fullscreen.locator('.trend-chart svg')).toHaveCount(1);
  await expect
    .poll(async () => (await chartHost.boundingBox())!.width)
    .toBeGreaterThan(originalWidth);
  await page.keyboard.press('Escape');
  await expect(fullscreen).toHaveCount(0);
  await expect(chartDialog).toBeVisible();
  await expect(expand).toBeFocused();
  await expand.click();
  await page.getByRole('button', { name: /^关闭放大：/ }).click();
  await expect(fullscreen).toHaveCount(0);
  await expect(chartDialog.locator('.trend-chart svg')).toHaveCount(1);

  await chartDialog.getByText('当前判定依据', { exact: false }).scrollIntoViewIfNeeded();
  await expect(chartDialog.getByText('当前判定依据', { exact: false })).toBeVisible();
  await chartDialog.getByLabel('图表标的搜索', { exact: true }).fill('NVDA');
  await expect(chartDialog.getByLabel('图表标的', { exact: true }).locator('option')).toContainText(
    ['AAPL', 'NVDA'],
  );
  await chartDialog.getByLabel('图表标的搜索', { exact: true }).fill('');
  await chartDialog.getByLabel('显示根数', { exact: true }).selectOption('0');
  await chartDialog.getByLabel('MACD', { exact: true }).check();
  await chartDialog.getByLabel('RSI', { exact: true }).check();
  await chartDialog.getByLabel('成交额（估算）', { exact: true }).check();
  await chartDialog.getByLabel('Kalman Price Filter', { exact: true }).check();
  await chartDialog.getByLabel('蜡烛染色', { exact: true }).selectOption('price');
  await chartDialog.getByLabel('四周期同屏', { exact: true }).check();
  for (const host of await chartDialog.locator('.trend-chart').all()) {
    await host.scrollIntoViewIfNeeded();
    await expect(host.locator('svg')).toHaveCount(1);
  }
  await expect(chartDialog.locator('.trend-chart svg')).toHaveCount(4);
  await chartDialog
    .getByText(/日线滚动聚合 · 含未完成周期预览/)
    .first()
    .scrollIntoViewIfNeeded();
  await expect(chartDialog.getByText(/日线滚动聚合 · 含未完成周期预览/).first()).toBeVisible();
  await chartDialog.screenshot({
    path: test.info().outputPath('cross-asset-charts.png'),
    animations: 'disabled',
  });
  await page.keyboard.press('Escape');
  await expect(chartDialog).not.toBeVisible();
  await panel.getByRole('button', { name: '信号历史', exact: true }).click();
  await expect(panel.getByRole('region', { name: '历史信号' }).locator('tbody tr')).toHaveCount(
    100,
  );
  const signalsDownload = page.waitForEvent('download');
  await panel.getByRole('button', { name: '导出筛选信号JSON', exact: true }).click();
  const signalFile = await (await signalsDownload).path();
  const signals = JSON.parse(await fs.readFile(signalFile!, 'utf8'));
  expect(signals.events.length).toBeGreaterThan(100);
  expect(signals.events.every((e) => e.system === 'composite' && !e.provisional)).toBe(true);
  await expect(panel.getByRole('region', { name: '历史信号' })).toContainText('零滞后主方向');
  await expect(panel.getByRole('region', { name: '历史信号' })).toContainText('保守确认');
  const firstSignal = panel.getByRole('region', { name: '历史信号' }).locator('tbody tr').first();
  const observedDate = await firstSignal.locator('td').first().innerText();
  await firstSignal.getByRole('button').click();
  await expect(
    page
      .getByRole('dialog')
      .last()
      .getByText('历史信号观测日 ' + observedDate, { exact: false }),
  ).toBeVisible();
  expect(
    new URL(new URL(page.url()).hash.slice(1), page.url()).searchParams.get('at'),
  ).toBeTruthy();
  await page
    .getByRole('dialog')
    .last()
    .getByText('信号观测日判定依据', { exact: false })
    .scrollIntoViewIfNeeded();
  await expect(
    page.getByRole('dialog').last().getByText('信号观测日判定依据', { exact: false }),
  ).toBeVisible();
  await page
    .getByRole('dialog')
    .last()
    .getByRole('button', { name: '回到最新', exact: true })
    .click();
  await expect(page).toHaveURL((url) => !new URL(url.hash.slice(1), url).searchParams.has('at'));
  await page.getByRole('dialog').last().getByLabel('图表周期', { exact: true }).selectOption('1W');
  await expect(page).toHaveURL(
    (url) => new URL(url.hash.slice(1), url).searchParams.get('frame') === '1W',
  );
  await page.reload();
  await expect(page.getByRole('dialog').last().getByLabel('图表周期', { exact: true })).toHaveValue(
    '1W',
  );
  await expect(
    page.getByRole('dialog').last().getByText('历史信号观测日', { exact: false }),
  ).toHaveCount(0);
  await page.getByRole('dialog').last().locator('.ant-modal-close').click();
  await expect(page.getByRole('dialog')).toHaveCount(0);

  await panel.getByRole('button', { name: '数据质量', exact: true }).click();
  await expect(panel.getByRole('region', { name: '行情数据覆盖' }).locator('tbody tr')).toHaveCount(
    48,
  );
  await panel.getByRole('button', { name: '数据与备份', exact: true }).last().click();
  const backupDownload = page.waitForEvent('download');
  await panel.getByRole('button', { name: '导出完整备份', exact: true }).click();
  const backupPath = await (await backupDownload).path();
  const backup = JSON.parse(await fs.readFile(backupPath!, 'utf8'));
  expect(backup.watchlists.some((w) => w.name === '验证清单' && w.symbols.length === 2)).toBe(true);
  expect(backup.preferences.chart.gridCharts).toBe(true);
  await panel.getByRole('button', { name: '导入完整备份', exact: true }).click();
  await panel.locator('input[type=file]').setInputFiles({
    name: 'backup.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(backup)),
  });
  await expect(panel.getByRole('status')).toContainText('导入完成');
  await panel.getByRole('button', { name: '导入行情JSON', exact: true }).click();
  await panel.locator('input[type=file]').setInputFiles({
    name: 'bad.json',
    mimeType: 'application/json',
    buffer: Buffer.from(
      JSON.stringify({
        ...archive.snapshot,
        series: [archive.snapshot.series[0], archive.snapshot.series[0]],
      }),
    ),
  });
  await expect(panel.getByRole('status')).toContainText('导入未完成');
  await panel.getByRole('button', { name: '趋势矩阵', exact: true }).click();
  await expect(matrix.locator('tbody tr')).toHaveCount(12);
  await page.reload();
  await openMatrix();
  await expect(matrix.locator('tbody tr')).toHaveCount(12);
  const auth = await (await page.request.get('/api/v1/auth/me')).json();
  await page.evaluate(async (account) => {
    const db = await new Promise<IDBDatabase>((resolve, reject) => {
      const req = indexedDB.open('global-variable-cross-asset', 1);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction('market-data', 'readwrite');
      tx.objectStore('market-data').put({ snapshot: { version: 99 }, caps: {} }, account);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
  }, auth.user.userId);
  await page.reload();
  await openMatrix();
  await expect(matrix.locator('tbody tr')).toHaveCount(12);
  await expect(panel.getByRole('status')).toContainText('本地行情格式无效');
  await panel.getByRole('button', { name: '日线转多 · 周月多头', exact: true }).click();
  await panel.locator('.trend-builder summary').click();
  await expect(panel.getByLabel('日线转向事件', { exact: true })).toHaveValue('多');
  await panel.getByRole('button', { name: '重置筛选', exact: true }).click();
  await panel.locator('.trend-builder summary').click();
  await page.locator('.board-workspace__viewport').evaluate((el) => {
    el.scrollTop = 0;
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath('cross-asset-mobile.png'),
    animations: 'disabled',
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: test.info().outputPath('cross-asset-desktop.png'),
    animations: 'disabled',
  });
  await fs.copyFile(
    test.info().outputPath('cross-asset-desktop.png'),
    path.resolve('../.codex/cross-asset-desktop.png'),
  );
  const logoutAuth = await (await page.request.get('/api/v1/auth/me')).json();
  const signout = await page.request.post('/api/v1/auth/logout', {
    headers: { 'X-CSRF-Token': logoutAuth.csrfToken, Origin: 'http://127.0.0.1:4437' },
  });
  expect(signout.ok()).toBe(true);
  await page.goto('/#/login');
  await page.reload();
  await page.getByPlaceholder('请输入账号').fill('e2e_employee_1');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login/);
  await page.goto(target);
  await openMatrix();
  await expect(matrix.locator('tbody tr')).toHaveCount(12);
  await expect(
    panel.getByLabel('自选清单', { exact: true }).locator('option').filter({ hasText: '验证清单' }),
  ).toHaveCount(0);
  await expect(panel.getByText('本地行情格式无效', { exact: false })).toHaveCount(0);
  const secondAuth = await (await page.request.get('/api/v1/auth/me')).json();
  expect(secondAuth.user.userId).not.toBe(auth.user.userId);
  const scopedKeys = await page.evaluate(() =>
    Object.keys(localStorage).filter((key) => key.startsWith('vg:cross-asset-screening:v1:')),
  );
  expect(scopedKeys).toContain('vg:cross-asset-screening:v1:' + auth.user.userId);
  expect(scopedKeys).toContain('vg:cross-asset-screening:v1:' + secondAuth.user.userId);
  expect(errors).toEqual([]);
});
