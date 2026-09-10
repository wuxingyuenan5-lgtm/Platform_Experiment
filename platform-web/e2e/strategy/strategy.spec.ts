import { expect, test, type Page } from '@playwright/test';
import type { FundingPositionGroup } from '../../src/api/platform/fundingWorkspace';

async function login(page: Page, username = 'e2e_ceo') {
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill(username);
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

test('CEO sees native account assets, read-only accounts and unbound BL without sample PnL', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await login(page);
  await page.goto('/#/strategy/management?desk=dip&section=capital');
  await expect(page.getByTestId('strategy-management-original-structure')).toBeVisible();
  const assets = page.getByTestId('strategy-kpi-grid');
  await expect(assets.getByText('全账户总资产', { exact: true })).toBeVisible();
  await expect(assets.getByText('12,500.00 USD', { exact: true })).toBeVisible();
  await expect(page.getByText('统一交易账户', { exact: true })).toBeVisible();
  await expect(page.getByText('理财', { exact: true })).toBeVisible();
  await expect(page.getByText('仅读取', { exact: true })).toBeVisible();
  await page.goto('/#/strategy/management?desk=shortLineTraderL&section=capital');
  await expect(page.getByText('交易账户权益', { exact: true }).first()).toBeVisible();
  await page.goto('/#/strategy/management?desk=shortLineTraderW&section=capital');
  await expect(page.getByText('暂未绑定账号', { exact: true }).first()).toBeVisible();
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
    ).toBeTruthy();
    await expect(page.getByText('暂未绑定账号', { exact: true }).first()).toBeVisible();
  }
  await page.screenshot({
    path: test.info().outputPath('strategy-unbound-bl.png'),
    animations: 'disabled',
  });
  expect(errors).toEqual([]);
});

test('strategy categories remain visible and curve precision defaults to daily', async ({
  page,
}) => {
  await login(page);
  await page.goto('/#/strategy/management?desk=funding&section=pnl');
  await expect(page.getByRole('heading', { name: '基差收益', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '现货附加收益', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: '现货借贷成本', exact: true })).toBeVisible();
  const precision = page.getByLabel('收益曲线时间精度');
  await expect(precision).toHaveValue('day');
  for (const value of ['week', 'hour', '5min', 'day']) {
    await precision.selectOption(value);
    await expect(precision).toHaveValue(value);
  }
  await page.getByRole('button', { name: '跨所价差', exact: true }).click();
  for (const name of [
    'XAUT/XAU价差损益',
    '永续/现货价差损益',
    'USDT/USD偏离损益',
    '腿间持仓损益',
    '库存费',
    '资费',
    '累计交易成本',
    '执行偏差',
  ]) {
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  }
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.evaluate(
      () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
    );
    await expect(
      page.getByRole('heading', { name: 'XAUT/XAU价差损益', exact: true }),
    ).toBeVisible();
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
      .toBeTruthy();
    await page.screenshot({
      path: test.info().outputPath(`pnl-${width}.png`),
      animations: 'disabled',
    });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await precision.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: test.info().outputPath('restored-pnl-categories.png'),
    fullPage: true,
    animations: 'disabled',
  });
});

test('CEO leverage uses session client, confirms once and retains form while reading back', async ({
  page,
}) => {
  let leverage = '20';
  const writes: Array<{ leverage: string }> = [];
  await page.route('**/api/v1/trading/cross-spread/leverage', async (route) => {
    if (route.request().method() === 'POST') {
      expect(route.request().headers()['x-csrf-token']).toBeTruthy();
      const body = route.request().postDataJSON();
      expect(Object.keys(body)).toEqual(['leverage']);
      writes.push(body);
      leverage = body.leverage;
    }
    await route.fulfill({
      json: {
        accountId: 'bound-account',
        symbol: 'XAUTUSDT',
        leverage,
        source: 'isolated_fixture',
      },
    });
  });
  await login(page);
  await page.goto('/#/strategy/platform?desk=crossSpread&section=execution');
  const input = page.getByLabel('Bybit 杠杆', { exact: true });
  await expect(page.getByText('当前杠杆 20x', { exact: false })).toBeVisible();
  await expect(input).toHaveValue('50');
  await input.fill('12.5');
  await page.getByRole('button', { name: '应用到交易所', exact: true }).click();
  await page
    .getByRole('dialog')
    .getByRole('button', { name: /取\s*消/ })
    .click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  expect(writes).toEqual([]);
  await page.getByRole('button', { name: '应用到交易所', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '应用到交易所', exact: true }).click();
  await expect(page.getByText('交易所已确认 XAUTUSDT 为 12.5x。', { exact: true })).toBeVisible();
  expect(writes).toEqual([{ leverage: '12.5' }]);
  await expect(input).toHaveValue('12.5');
  await page.getByRole('button', { name: '刷新', exact: true }).click();
  await expect(page.getByText('当前杠杆 12.5x', { exact: false })).toBeVisible();
  await expect(input).toHaveValue('12.5');
});

test('CEO Cross confirmation is frozen, cancellation is safe and simulation closes through the UI', async ({
  page,
}) => {
  await login(page);
  await page.goto('/#/strategy/platform?desk=crossSpread&section=execution');
  const command = page
    .locator('section')
    .filter({ has: page.getByRole('heading', { name: '价差执行指令', exact: true }) })
    .last();
  const open = command.getByRole('button', { name: '开多价差', exact: true });
  await expect(open).toBeVisible();
  await open.click();
  await expect(page.getByText('确认价差指令', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '取消', exact: true }).click();
  await expect(page.getByText('确认价差指令', { exact: true })).not.toBeVisible();
  await open.click();
  await expect(page.getByText('预检完成，可以确认下单', { exact: true })).toBeVisible();
  const submitted = page.waitForResponse(
    (r) => r.url().includes('/cross-spread/lifecycle/open') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '确认执行', exact: true }).click();
  const result = await submitted;
  expect(result.ok(), await result.text()).toBeTruthy();
  expect(result.request().headers()['x-csrf-token']).toBeTruthy();
  const opened = await result.json();
  expect(opened.executionBatch.status).toBe('hedged');
  await command.getByRole('button', { name: '平仓价差', exact: true }).click();
  await command.getByRole('button', { name: '全平', exact: true }).first().click();
  await expect(page.getByText('预检完成，可以确认下单', { exact: true })).toBeVisible();
  const closing = page.waitForResponse(
    (r) =>
      r.url().includes('/cross-spread/exit-plans/') &&
      r.url().endsWith('/close') &&
      r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '确认执行', exact: true }).click();
  const closed = await closing;
  expect(closed.ok(), await closed.text()).toBeTruthy();
  expect((await closed.json()).exitPlan.status).toBe('closed');
});

test('employee can read strategy accounts but cannot submit funding or Cross orders', async ({
  page,
}) => {
  await login(page, 'e2e_employee_1');
  await page.goto('/#/strategy/platform?desk=funding&section=execution');
  await expect(page.getByRole('button', { name: '提交正套开仓', exact: true })).toBeDisabled();
  await page.goto('/#/strategy/platform?desk=crossSpread&section=execution');
  await page.getByRole('button', { name: '开多价差', exact: true }).click();
  await expect(page.getByText('仅 CEO 可下达交易指令', { exact: true })).toBeVisible();
  await expect(page.getByText('确认价差指令', { exact: true })).not.toBeVisible();
});

test('CEO funding confirms once, reconciles, partially closes and fully closes through the UI', async ({
  page,
}) => {
  await login(page);
  const writes: string[] = [];
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/funding/instructions'))
      writes.push(request.postData() || '');
  });
  await page.goto('/#/strategy/platform?desk=funding&section=execution');
  const panel = page.getByTestId('funding-order-panel');
  await expect(panel).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath('funding-initial.png'),
    animations: 'disabled',
  });
  const submit = panel.getByRole('button', { name: '提交正套开仓', exact: true });
  await expect(submit).toBeEnabled();
  await submit.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByRole('button', { name: '返回修改', exact: true }).click();
  expect(writes).toHaveLength(0);
  await panel.getByLabel('执行数量', { exact: true }).fill('0.5');
  await panel.getByRole('button', { name: '刷新行情', exact: true }).click();
  await expect(submit).toBeEnabled();
  await expect(panel.getByLabel('执行数量', { exact: true })).toHaveValue('0.5');
  await submit.click();
  const submitted = page.waitForResponse(
    (r) => r.url().includes('/funding/instructions') && r.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '确认提交', exact: true }).click();
  const response = await submitted;
  expect(response.status(), await response.text()).toBe(200);
  expect(response.request().headers()['x-csrf-token']).toBeTruthy();
  expect(writes).toHaveLength(1);
  expect(JSON.parse(writes[0]).quantity).toBe('0.5');
  const opened = await response.json();
  const openId = opened.instruction.instructionId;
  async function waitForCompletion(id: string) {
    await expect
      .poll(
        async () => {
          const result = await page.request.get(`/api/v1/trading/funding/instructions/${id}`);
          expect(result.ok(), await result.text()).toBeTruthy();
          return (await result.json()).instruction.status;
        },
        { timeout: 45_000, intervals: [1000] },
      )
      .toBe('completed');
  }
  await waitForCompletion(openId);
  for (const quantity of ['0.2', '0.3']) {
    await page.reload();
    await panel.getByRole('button', { name: '平仓', exact: true }).click();
    await panel.getByRole('button', { name: '选择', exact: true }).first().click();
    await panel.getByLabel('平仓数量', { exact: true }).fill(quantity);
    const close = panel.getByRole('button', { name: '执行组合平仓', exact: true });
    await expect(close).toBeEnabled();
    await close.click();
    const closed = page.waitForResponse(
      (r) => r.url().includes('/funding/instructions') && r.request().method() === 'POST',
    );
    await page.getByRole('button', { name: '确认提交', exact: true }).click();
    const result = await closed;
    expect(result.ok(), await result.text()).toBeTruthy();
    await waitForCompletion((await result.json()).instruction.instructionId);
  }
  const groups = await page.request.get('/api/v1/trading/funding/positions?scope=all');
  const groupData: FundingPositionGroup[] = await groups.json();
  const original = groupData.find((group) => group.instructionId === openId)!;
  expect(Number(original.remainingClosableQuantity)).toBe(0);
  expect(original.lifecycleState).toBe('history');
  expect(writes).toHaveLength(3);
  await page.screenshot({
    path: test.info().outputPath('funding-submitted.png'),
    animations: 'disabled',
  });
});
