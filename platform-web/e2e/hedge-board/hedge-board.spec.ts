import { expect, test, type Page } from '@playwright/test';

const origin = 'http://127.0.0.1:4437';
const password = process.env.E2E_CEO_PASSWORD!;
async function login(page: Page, username: string) {
  await page.goto(`${origin}/#/login`);
  await page.getByPlaceholder('请输入账号').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  const response = page.waitForResponse(
    (r) => r.url().endsWith('/api/v1/auth/login') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const result = await response;
  expect(result.ok()).toBeTruthy();
  const csrf = (await result.json()).csrfToken;
  await expect(page).not.toHaveURL(/\/login/);
  await page.goto(`${origin}/#/hedge-board/a-share`);
  await expect(page.getByRole('heading', { name: '自选股与核心股票池' })).toBeVisible();
  await expect(page.getByText(/核心池 \d+ 只/)).toBeVisible();
  return csrf;
}
async function mode(page: Page, _csrf: string, value: string) {
  const authentication = await page.request.get(`${origin}/api/v1/auth/me`);
  const csrf = (await authentication.json()).csrfToken;
  const response = await page.request.post('http://127.0.0.1:8437/api/v1/__test__/provider', {
    headers: { Origin: origin, 'X-CSRF-Token': csrf },
    data: { mode: value },
  });
  expect(response.status(), await response.text()).toBe(200);
  await page.reload();
  await expect(page.getByRole('heading', { name: '自选股与核心股票池' })).toBeVisible();
}

test('real API and SQLite: shared core pool, private focus, reload, chart controls and failure feedback', async ({
  browser,
}) => {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const csrf = await login(page, 'e2e_ceo');
  const pool = page.locator('#a-share-watchlist-pool');
  await pool.getByRole('button', { name: '管理核心池', exact: true }).click();
  await page.getByLabel('证券代码', { exact: true }).fill('600000');
  const saved = page.waitForResponse(
    (r) => r.url().endsWith('/stock-pool/add-batch') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '添加到核心池', exact: true }).click();
  expect((await saved).ok()).toBeTruthy();
  await expect(pool.getByText(/核心池 6 只/)).toBeVisible();
  await page.reload();
  await expect(pool.getByText(/核心池 6 只/)).toBeVisible();
  await pool.getByLabel('范围', { exact: true }).selectOption('__focus__');
  await pool.getByRole('button', { name: '添加关注', exact: true }).click();
  await pool.getByLabel('近期关注证券代码').fill('00700 600000');
  await pool.getByRole('button', { name: '保存', exact: true }).click();
  await expect(pool.getByText(/近期关注 2 只/)).toBeVisible();
  await page.reload();
  await expect(pool.getByText(/近期关注 2 只/)).toBeVisible();
  await pool.getByLabel('范围', { exact: true }).selectOption('__focus__');
  await expect(pool.locator('tbody tr')).toHaveCount(2);
  const second = await browser.newContext();
  const employee = await second.newPage();
  await employee.goto(`${origin}/#/login`);
  await employee.getByPlaceholder('请输入账号').fill('e2e_employee_1');
  await employee.getByPlaceholder('请输入密码').fill(password);
  await employee.getByRole('button', { name: '登录', exact: true }).click();
  await expect(employee).not.toHaveURL(/\/login/);
  await employee.goto(`${origin}/#/hedge-board/a-share`);
  await expect(employee.getByText(/核心池 6 只 · 近期关注 0 只/)).toBeVisible();
  await expect(employee.getByRole('button', { name: '管理核心池', exact: true })).toHaveCount(0);
  await second.close();
  await pool.getByLabel('范围', { exact: true }).selectOption('');
  await pool.getByPlaceholder('名称 / 行业 / 代码').fill('600000');
  await pool.locator('tbody tr').getByTitle('从核心股票池移除').click();
  await page.getByRole('button', { name: /^移\s*除$/ }).click();
  await expect(pool.getByText(/核心池 5 只 · 近期关注 2 只/)).toBeVisible();
  await pool.getByPlaceholder('名称 / 行业 / 代码').fill('');
  await pool.getByLabel('范围', { exact: true }).selectOption('__focus__');
  await expect(pool.locator('tbody tr')).toHaveCount(2);
  await pool.locator('tbody').getByRole('button', { name: '腾讯控股', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('heading', { name: '复权收盘价' })).toBeVisible();
  await page.getByLabel('个股日线范围').selectOption('20');
  await expect(page.getByRole('img', { name: '00700复权收盘价，20个交易日' })).toBeVisible();
  await page.keyboard.press('Escape');
  const chart = page
    .locator('.vibe-time-chart')
    .filter({ has: page.getByRole('heading', { name: '市场宽度', exact: true }) });
  await chart.getByRole('button', { name: '全部', exact: true }).click();
  await expect(chart.getByRole('button', { name: '全部', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  const legend = chart.locator('.vibe-legend-btn').first();
  await legend.click();
  await expect(legend).toHaveAttribute('aria-pressed', 'false');
  await legend.click();
  await chart.locator('svg').focus();
  await page.keyboard.press('ArrowLeft');
  await page.screenshot({
    path: test.info().outputPath('desktop-charts.png'),
    animations: 'disabled',
  });
  await mode(page, csrf, 'partial');
  await page.getByRole('button', { name: '更新收盘数据', exact: true }).click();
  await expect(
    page.getByText('部分数据已更新，未完成的内容保留上次有效数据', { exact: true }),
  ).toBeVisible();
  await pool.getByLabel('范围', { exact: true }).selectOption('');
  await expect(pool.getByText('旧数据', { exact: true }).first()).toBeVisible();
  await mode(page, csrf, 'error');
  await page.getByRole('button', { name: '更新收盘数据', exact: true }).click();
  await expect(page.getByText(/更新未完成，已保留上次有效数据/)).toBeVisible();
  await mode(page, csrf, 'ready');
  await page.getByRole('button', { name: '更新收盘数据', exact: true }).click();
  await expect(page.getByText('收盘数据已更新', { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
  await context.close();
});

test('responsive A-share board has readable sections and no page overflow', async ({ page }) => {
  await login(page, 'e2e_ceo');
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1024, height: 768 },
    { width: 768, height: 1024 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewportSize(viewport);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('heading', { name: '自选股与核心股票池' })).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
    ).toBeTruthy();
    const clippedPanels = await page
      .locator(
        '.pool-card, .matrix-wrap, .leader-panel, .stock-filter-panel, .market-terminal__vol-top b',
      )
      .evaluateAll((panels) =>
        panels
          .filter((panel) => {
            const box = panel.getBoundingClientRect();
            return box.width > innerWidth || box.right > innerWidth + 1;
          })
          .map((panel) => {
            const ancestry: string[] = [];
            for (let node: Element | null = panel; node; node = node.parentElement) {
              const box = node.getBoundingClientRect();
              const css = getComputedStyle(node);
              ancestry.push(
                `${node.className}: ${box.width}/${box.right}, min=${css.minWidth}, width=${css.width}, grid=${css.gridTemplateColumns}`,
              );
            }
            return ancestry;
          }),
      );
    expect(clippedPanels).toEqual([]);
    await page.locator('#a-share-index-overview').scrollIntoViewIfNeeded();
    await page.screenshot({
      path: test.info().outputPath(`overview-${viewport.width}.png`),
      animations: 'disabled',
    });
    await page.locator('#a-share-watchlist-pool .matrix-panel').scrollIntoViewIfNeeded();
    await page.screenshot({
      path: test.info().outputPath(`pool-${viewport.width}.png`),
      animations: 'disabled',
    });
  }
});
