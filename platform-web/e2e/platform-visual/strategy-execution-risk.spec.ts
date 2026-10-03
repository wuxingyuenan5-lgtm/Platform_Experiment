import { expect, test } from '@playwright/test';

test('Funding exit editor preserves decimal thresholds and server revision across reload', async ({
  page,
}) => {
  let plan: Record<string, unknown> | null = null;
  const patches: unknown[] = [];
  const now = new Date().toISOString();
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const json = (value: unknown) =>
      route.fulfill({ contentType: 'application/json', body: JSON.stringify(value) });
    if (request.method() !== 'GET') {
      expect(url.pathname).toBe('/api/v1/trading/funding/exit-plans/normal-open');
      expect(request.method()).toBe('PATCH');
      const body = request.postDataJSON();
      patches.push(body);
      plan = {
        ...body,
        revision: body.expectedRevision + 1,
        openInstructionId: 'normal-open',
        updatedAt: now,
      };
      return json(plan);
    }
    if (url.pathname.endsWith('/auth/me'))
      return json({
        user: {
          userId: 'fixture-ceo',
          username: 'fixture',
          realName: '隔离验收',
          role: 'ceo',
          status: 'active',
          registeredAt: now,
          rowVersion: 1,
        },
        permissions: ['strategy.read', 'profile.read_self', 'research.read', 'trading.write'],
        session: { sessionId: 'isolated', expiresAt: '2030-01-01T00:00:00Z' },
        csrfToken: 'isolated',
      });
    if (url.pathname.endsWith('/funding/positions'))
      return json([
        {
          instructionId: 'normal-open',
          openInstructionId: 'normal-open',
          batchId: 'normal-batch',
          lifecycleState: 'active',
          isAbnormal: false,
          status: 'completed',
          spotSymbol: 'BTCUSDT',
          perpetualSymbol: 'BTCUSDT',
          remainingClosableQuantity: '1',
          pendingCloseQuantity: '0',
          resultUnknownReservedQuantity: '0',
          residualQuantity: '0',
          asOf: now,
          exitPlan: plan,
        },
      ]);
    if (url.pathname.endsWith('/funding/execution-context'))
      return json({
        spotSymbol: 'BTCUSDT',
        perpetualSymbol: 'BTCUSDT',
        symbolOptions: [],
        dataQualityState: 'complete',
        controlledLiveReadiness: { ready: false },
        quantityStep: { spot: '0.000001', perpetual: '0.001' },
        minimumQuantity: { spot: '0.000001', perpetual: '0.001' },
      });
    return json([]);
  });
  await page.goto('/#/strategy/platform?desk=funding&section=execution');
  const panel = page.getByTestId('funding-exit-settings');
  // Cold Vite module compilation is separate from the editor interaction timeout.
  await expect(panel).toBeVisible({ timeout: 90_000 });
  await panel.getByRole('button', { name: '设置', exact: true }).click();
  await panel.getByLabel('启用价差自动平仓').check();
  await panel.getByLabel('止盈价差（≥）').fill('0.123456789123');
  await panel.getByLabel('止损价差（≤）').fill('-3.123456789123');
  await panel.getByRole('button', { name: '检查设置', exact: true }).click();
  expect(patches).toHaveLength(0);
  await panel.getByRole('button', { name: '确认保存', exact: true }).click();
  await expect(panel).toContainText('设置已保存');
  await page.reload();
  await expect(panel).toContainText('已启用');
  await panel.getByRole('button', { name: '设置', exact: true }).click();
  await expect(panel.getByLabel('止盈价差（≥）')).toHaveValue('0.123456789123');
  await panel.getByLabel('启用价差自动平仓').uncheck();
  await panel.getByRole('button', { name: '检查设置', exact: true }).click();
  await panel.getByRole('button', { name: '确认保存', exact: true }).click();
  await expect(panel).toContainText('未启用');
  expect(patches).toEqual([
    {
      expectedRevision: 0,
      enabled: true,
      takeProfitSpread: '0.123456789123',
      stopLossSpread: '-3.123456789123',
    },
    {
      expectedRevision: 1,
      enabled: false,
      takeProfitSpread: '0.123456789123',
      stopLossSpread: '-3.123456789123',
    },
  ]);
});

test('isolated CEO configures persisted risk and strategy kill switch through the real page', async ({
  page,
}) => {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?\/|localhost(?::\d+)?\/)/, (route) =>
    route.abort(),
  );
  await page.goto('/#/login');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_SHARED_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/);
  await page.goto('/#/strategy/management?desk=funding&section=capital');
  const panel = page.getByTestId('execution-risk-panel');
  await expect(panel).toContainText('使用系统默认值');
  await panel.getByLabel('腿间最长时间（秒）').fill('12');
  await panel.getByLabel('余差名义上限（结算币）').fill('123.456789');
  await panel.getByRole('button', { name: '检查并保存' }).click();
  await expect(panel).toContainText('已有批次保留原参数');
  await panel.getByRole('button', { name: '确认变更', exact: true }).click();
  await expect(panel).toContainText('服务端回执已确认');
  await page.reload();
  await expect(panel).toContainText('使用专属配置');
  await expect(panel.getByLabel('余差名义上限（结算币）')).toHaveValue('123.456789');
  await panel.getByRole('button', { name: '阻断策略执行', exact: true }).click();
  await panel.getByRole('button', { name: '确认变更', exact: true }).click();
  await expect(panel).toContainText('策略执行开关：已阻断');
  await panel.getByRole('button', { name: '解除策略阻断', exact: true }).click();
  await panel.getByRole('button', { name: '确认变更', exact: true }).click();
  await expect(panel).toContainText('策略执行开关：未阻断');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(panel.getByLabel('余差名义上限（结算币）')).toBeVisible();
});

test('Funding recovery retains exact request after lost response and never submits a new close', async ({
  page,
}) => {
  const posts: unknown[] = [];
  let completed = false;
  const now = new Date().toISOString();
  await page.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!['127.0.0.1', 'localhost'].includes(url.hostname)) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const json = (value: unknown) =>
      route.fulfill({ contentType: 'application/json', body: JSON.stringify(value) });
    if (request.method() !== 'GET') {
      expect(url.pathname).toBe(
        '/api/v1/trading/funding/instructions/original-close/recover-close',
      );
      expect(request.method()).toBe('POST');
      posts.push(request.postDataJSON());
      completed = true;
      if (posts.length === 1) return route.abort('connectionreset');
      return json({ instruction: { instructionId: 'original-close', status: 'completed' } });
    }
    if (url.pathname.endsWith('/auth/me'))
      return json({
        user: {
          userId: 'fixture-ceo',
          username: 'fixture',
          realName: '隔离验收',
          role: 'ceo',
          status: 'active',
          registeredAt: now,
          rowVersion: 1,
        },
        permissions: ['strategy.read', 'profile.read_self', 'research.read', 'trading.write'],
        session: { sessionId: 'isolated', expiresAt: '2030-01-01T00:00:00Z' },
        csrfToken: 'isolated',
      });
    if (url.pathname.endsWith('/system/monitor-health'))
      return json({
        accountSync: { status: 'healthy' },
        crossExit: { status: 'healthy' },
        watchdog: { status: 'healthy' },
      });
    if (url.pathname.endsWith('/funding/positions'))
      return json(
        completed
          ? []
          : [
              {
                instructionId: 'original-open',
                batchId: 'original-open-batch',
                lifecycleState: 'active',
                isAbnormal: true,
                abnormalAction: 'finish_close',
                abnormalReason: '永续已平，现货拒单',
                perpetualSymbol: 'BTCUSDT',
                remainingPerpetualQuantity: '0',
                remainingSpotHolding: '0.001999',
                resultUnknownReservedQuantity: '0',
                recoveryCloseInstructionId: 'original-close',
                recoveryIdempotencyKey: 'server-frozen-recovery-key',
                recoverySpotQuantity: '0.001999',
                asOf: now,
              },
            ],
      );
    if (url.pathname.endsWith('/funding/execution-context'))
      return json({
        perpetualSymbol: 'BTCUSDT',
        spotSymbol: 'BTCUSDT',
        symbolOptions: [],
        dataQualityState: 'complete',
        controlledLiveReadiness: { ready: true },
        quantityStep: { spot: '0.000001', perpetual: '0.001' },
        minimumQuantity: { spot: '0.000001', perpetual: '0.001' },
      });
    return json([]);
  });
  await page.goto('/#/strategy/platform?desk=funding&section=execution');
  await page.getByRole('button', { name: '补平原指令剩余现货', exact: true }).click();
  await expect(page.getByRole('group', { name: '确认补平现货' })).toContainText('0.001999');
  await page.getByRole('button', { name: '确认补平现货', exact: true }).click();
  await expect(page.getByText('补平结果尚未确认', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: '确认补平现货', exact: true }).click();
  await expect(page.getByText('原平仓已完成，永续腿未重复下单。', { exact: true })).toBeVisible();
  expect(posts).toEqual([
    { idempotencyKey: 'server-frozen-recovery-key' },
    { idempotencyKey: 'server-frozen-recovery-key' },
  ]);
});
