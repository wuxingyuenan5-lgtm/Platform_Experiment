import { expect, test } from '@playwright/test';

test('new cross-spread research page is independent, interactive and responsive', async ({
  page,
}) => {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?\/|localhost(?::\d+)?\/)/, (route) =>
    route.abort(),
  );
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_SHARED_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  await page.goto('/#/strategy/platform?desk=crossSpread&section=analysis');
  await page.getByRole('button', { name: '行情分析 · 新版', exact: true }).click();
  await expect(page).toHaveURL(/section=analysisDemo/);
  const demo = page.getByTestId('cross-spread-market-demo');
  await expect(demo).toBeVisible();
  const writes: string[] = [],
    researchRequests: string[] = [];
  page.on('request', (r) => {
    if (
      ['POST', 'PUT', 'PATCH', 'DELETE'].includes(r.method()) &&
      /\/api\/v1\/(?:research|trading)/.test(r.url())
    )
      writes.push(r.url());
    if (/\/research\/strategies/.test(r.url())) researchRequests.push(r.url());
  });
  await page.reload();
  await expect(demo.getByRole('heading', { name: '价差研究台 演示数据' })).toBeVisible();
  await demo.locator('.demo-chart').first().scrollIntoViewIfNeeded();
  await expect(demo.locator('.demo-chart svg').first()).toBeVisible();
  await expect(demo.locator('.demo-chart').first()).toContainText('空价差成本边界');
  const total = demo.getByTestId('demo-total');
  const before = Number((await total.innerText()).replace(/[^\d.-]/g, ''));
  await demo.getByLabel('研究数量').fill('10');
  await expect
    .poll(async () => Number((await total.innerText()).replace(/[^\d.-]/g, '')))
    .toBeCloseTo(before * 2, 1);
  await demo.getByLabel('研究数量').fill('');
  await expect(total).toHaveText('— U');
  await demo.getByLabel('研究数量').fill('5');
  await demo.getByLabel('持有期').selectOption('72');
  await demo.getByText('调整成本假设与结算事件', { exact: true }).click();
  await expect(demo.getByText('T + 32.5h · 库存费 ×3', { exact: true })).toBeVisible();
  await demo.getByLabel('持有期').selectOption('8');
  await demo.getByRole('button', { name: '流动性收缩', exact: true }).click();
  expect(Number((await total.innerText()).replace(/[^\d.-]/g, ''))).toBeLessThan(0);
  await demo.getByRole('button', { name: 'CFD 休市', exact: true }).click();
  await expect(total).toHaveText('— U');
  await expect(demo.getByText('一侧不可交易', { exact: true })).toBeVisible();
  await demo.getByRole('button', { name: '代币重估', exact: true }).click();
  await expect(total).toHaveText('— U');
  await demo.getByRole('button', { name: '短时偏离', exact: true }).click();
  await demo.getByLabel('图表单位').selectOption('bps');
  await demo.getByLabel('研究窗口').selectOption('90');
  await demo.getByRole('button', { name: '统计分析', exact: true }).click();
  await expect(demo.getByRole('heading', { name: '分位与形态' })).toBeVisible();
  await demo.getByLabel('统计序列').selectOption('sell');
  await demo.getByLabel('统计时段').selectOption('亚洲');
  await demo.getByRole('button', { name: '波动与稳定性', exact: true }).click();
  await demo.getByLabel('滚动统计窗口').selectOption('24');
  await expect(demo.locator('.statistics-empty')).toBeVisible();
  await demo.getByLabel('统计时段').selectOption('全部');
  await expect(demo.locator('.statistics-empty')).toHaveCount(0);
  await demo.getByRole('button', { name: '时段结构', exact: true }).click();
  await demo.getByLabel('统计分组').selectOption('month');
  await expect(demo.getByRole('heading', { name: '分组比较', exact: true })).toBeVisible();
  await demo.getByRole('button', { name: '回归与时段', exact: true }).click();
  await expect(demo.getByRole('heading', { name: '偏离事件明细' })).toBeVisible();
  await demo.getByLabel('事件时段').selectOption('亚洲');
  await expect(demo.locator('.event-kpis')).toContainText('完整事件');
  await demo.getByLabel('事件风险线').selectOption('1');
  await expect(demo.getByRole('heading', { name: '期限与方向的条件表现' })).toBeVisible();
  await demo.getByRole('button', { name: '兑现与持有', exact: true }).click();
  await demo.getByLabel('兑现研究数量').fill('20');
  await expect(demo.getByTestId('depth-adjusted-net')).toHaveText('—');
  await demo.getByLabel('兑现研究数量').fill('5');
  await demo.getByLabel('兑现计划持有期').selectOption('24');
  await expect(demo.getByRole('heading', { name: '休市重开：跳过的不是零波动' })).toBeVisible();
  await demo.getByLabel('兑现计划持有期').selectOption('8');
  await demo.getByRole('button', { name: '来源与失效条件', exact: true }).click();
  await expect(demo.locator('.attribution-total')).toContainText('9.20 点');
  await page.screenshot({ path: test.info().outputPath('attribution.png'), fullPage: true });
  await demo.getByRole('button', { name: '价差与净空间', exact: true }).click();
  await demo.getByText('调整成本假设与结算事件', { exact: true }).click();
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.screenshot({ path: test.info().outputPath('desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(demo.getByTestId('demo-total')).toBeVisible();
  expect(await demo.evaluate((el) => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
  await page.screenshot({ path: test.info().outputPath('mobile.png'), fullPage: true });
  expect(writes).toEqual([]);
  expect(researchRequests).toEqual([]);
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.getByRole('button', { name: '行情分析', exact: true }).click();
  await expect(demo).toHaveCount(0);
  await expect(page.getByRole('heading', { name: '跨所价差走势', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '行情分析 · 新版', exact: true }).click();
  await page.getByRole('button', { name: '资费', exact: true }).click();
  await expect(demo).toHaveCount(0);
  await page.getByRole('button', { name: '行情分析', exact: true }).click();
  await expect(page.getByRole('heading', { name: '单次收益情景', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
