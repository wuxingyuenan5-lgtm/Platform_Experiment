import { expect, test } from '@playwright/test';

test('overview contains both calendars directly and viewpoints use workspace scrolling', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1920, height: 1200 });
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    return ['127.0.0.1', 'localhost'].includes(url.hostname) ? route.continue() : route.abort();
  });
  await page.route('**/api/v1/research/**', (route) =>
    route.fulfill({ status: 503, json: { detail: 'Isolated research source unavailable' } }),
  );
  await page.goto('/#/hedge-board/macro?view=macro-market');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const sidebar = page.getByRole('navigation', { name: '宏观研究专题' });
  await expect(sidebar.getByRole('link', { name: '经济日历', exact: true })).toHaveCount(0);
  await expect(sidebar.getByRole('link', { name: '市场总览', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await expect(page.locator('#macro-market')).toBeVisible();
  const events = page.locator('.event-calendar');
  const calendar = page.locator('.macro-calendar-panel');
  await expect(events).toHaveCount(1);
  await expect(calendar).toHaveCount(1);
  await expect(page.getByRole('heading', { name: '宏观日历', exact: true })).toHaveCount(1);
  await expect(
    page.locator('[data-testid="macro-calendar-panel"], #macro-calendar-content'),
  ).toHaveCount(0);
  expect(await calendar.evaluate((el) => el.parentElement?.className)).toBe(
    'board-workspace__content',
  );
  await events.getByRole('button', { name: '添加事件', exact: true }).click();
  await expect(events.getByLabel('事件', { exact: true })).toBeVisible();
  await events.getByRole('button', { name: '取消', exact: true }).click();
  const japan = calendar.getByRole('button', { name: '日本', exact: true });
  await japan.click();
  await expect(japan).toHaveClass(/is-active/);
  await calendar.getByRole('button', { name: '仅高', exact: true }).click();
  await expect(calendar.getByRole('button', { name: '仅高', exact: true })).toHaveClass(
    /is-active/,
  );
  await sidebar.getByRole('link', { name: '宏观详情', exact: true }).click();
  await expect(calendar).toHaveCount(0);
  await expect(events).toHaveCount(0);
  await page.goto('/#/hedge-board/macro?view=calendar');
  await expect(sidebar.getByRole('link', { name: '市场总览', exact: true })).toHaveAttribute(
    'aria-current',
    'page',
  );
  await expect(calendar).toHaveCount(1);
  await sidebar.getByRole('link', { name: '观点跟踪', exact: true }).click();
  await page.getByRole('button', { name: '其他市场观点', exact: true }).click();
  const grid = page.locator('.viewpoints__sources');
  expect(await grid.locator('article').count()).toBeGreaterThan(30);
  const layout = await grid.evaluate((el) => ({
    height: el.clientHeight,
    scrollHeight: el.scrollHeight,
    overflow: getComputedStyle(el).overflowY,
  }));
  expect(layout.height).toBeGreaterThan(600);
  expect(layout.scrollHeight).toBeLessThanOrEqual(layout.height + 1);
  expect(layout.overflow).toBe('visible');
  await grid.locator('article').last().scrollIntoViewIfNeeded();
  expect(
    await page.locator('.board-workspace__viewport').evaluate((el) => el.scrollTop),
  ).toBeGreaterThan(0);
  await page.getByLabel('搜索观点来源').fill('0xWizard');
  await expect(grid.locator('article')).toHaveCount(1);
});
