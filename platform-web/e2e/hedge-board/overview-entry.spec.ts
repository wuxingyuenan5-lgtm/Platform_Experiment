import { expect, test, type Page } from '@playwright/test';

test('login restores the full A-share link and pending data stays distinct from missing data', async ({
  page,
  browser,
}) => {
  await page.setViewportSize({ width: 1720, height: 1000 });
  const target = '/hedge-board/a-share?view=overview#market';
  await page.goto('/#' + target);
  await expect(page.getByPlaceholder('请输入账号')).toBeVisible();
  const loginQuery = new URL(new URL(page.url()).hash.slice(1), page.url()).searchParams;
  expect(loginQuery.get('redirect')).toBe(target);
  let release!: () => void;
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route('**/research/a-share/dashboard*', async (route) => {
    await held;
    const response = await route.fetch();
    const dashboard = await response.json();
    dashboard.marketHistory = [
      { observedAt: '1990-01-01', csi300Close: '1000' },
      ...(dashboard.marketHistory || []),
    ];
    await route.fulfill({ response, json: dashboard });
  });
  await page.route('**/research/a-share/live-sector-flow*', async (route) => {
    const response = await route.fetch();
    const flow = await response.json();
    const original = flow.rows;
    flow.rows = Array.from({ length: 31 }, (_, index) => ({
      ...original[index % original.length],
      name: `行业${index + 1}`,
    }));
    await route.fulfill({ response, json: flow });
  });
  await page.route('**/research/macro/dashboard-v1*', async (route) => {
    if (new URL(route.request().url()).searchParams.get('groups') !== 'cnTreasury')
      return route.continue();
    await route.fulfill({
      json: {
        groups: {
          cnTreasury: [
            {
              seriesId: 'cn_treasury_10y',
              unit: 'percent',
              latestValue: '1.50',
              observationDate: '2026-11-06',
              source: 'chinabond',
              status: 'ready',
              isStale: false,
              observations: [
                { date: '2026-11-05', value: '1.42' },
                { date: '2026-11-06', value: '1.50' },
              ],
            },
            {
              seriesId: 'cn_treasury_30y',
              unit: 'percent',
              latestValue: '2.03',
              observationDate: '2026-11-06',
              source: 'chinabond',
              status: 'ready',
              isStale: false,
              observations: [
                { date: '2026-11-05', value: '2.04' },
                { date: '2026-11-06', value: '2.03' },
              ],
            },
          ],
        },
      },
    });
  });
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  try {
    await expect(page).toHaveURL((url) => url.hash === '#' + target);
    await expect(page.getByText('正在读取市场总览…')).toBeVisible();
    await expect(page.getByText('暂无市场情绪数据')).toHaveCount(0);
    await expect(page.getByText('20日参与度')).toHaveCount(0);
  } finally {
    release();
  }
  async function expectDatedValue(view: Page) {
    const sentiment = view.getByRole('region', { name: '市场涨跌结构', exact: true });
    await expect(sentiment.locator('.structure-metric strong').first()).toHaveText(/\d+/);
    await expect(sentiment.locator('.research-source-state__time').first()).toHaveText(/源 .*\d/);
    await expect(sentiment).toBeVisible();
  }
  await expectDatedValue(page);
  const structure = page.locator('.market-structure-chart');
  const rangeControls = structure.getByRole('group', { name: '市场涨跌结构历史范围' });
  await expect(rangeControls.getByRole('button')).toHaveText(['近90日', '1年', '3年', '全部']);
  await expect(rangeControls.getByRole('button', { name: '近90日', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await structure.scrollIntoViewIfNeeded();
  await expect(structure.locator('.plot svg')).toBeVisible();
  await expect(structure.locator('.plot')).not.toHaveAttribute('aria-label', /1990-01-01/);
  await expect(structure.locator('input[type="range"]')).toHaveCount(0);
  for (const name of ['1年', '3年', '全部', '近90日']) {
    await rangeControls.getByRole('button', { name, exact: true }).click();
    await expect(rangeControls.getByRole('button', { name, exact: true })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  }
  await rangeControls.getByRole('button', { name: '全部', exact: true }).click();
  const labels = () =>
    structure
      .locator('.plot svg text')
      .allTextContents()
      .then((values) => values.filter((value) => /^\d{2}-\d{2}-\d{2}$/.test(value)).join(','));
  const beforeDrag = await labels();
  const bounds = (await structure.locator('.plot').boundingBox())!;
  await page.mouse.move(bounds.x + 67, bounds.y + bounds.height - 22);
  await page.mouse.down();
  await page.mouse.move(bounds.x + bounds.width * 0.4, bounds.y + bounds.height - 22, {
    steps: 12,
  });
  await page.mouse.up();
  await expect.poll(labels).not.toBe(beforeDrag);
  await rangeControls.getByRole('button', { name: '近90日', exact: true }).click();
  await structure.screenshot({ path: test.info().outputPath('market-structure.png') });
  const funds = page.getByRole('region', { name: '行业资金与成交额', exact: true });
  const sectorPanel = funds.locator('.industry-flow-panel');
  const sectorScroll = funds.getByRole('region', { name: '一级行业资金榜明细', exact: true });
  const turnoverPanel = funds.locator('.turnover-panel');
  const turnoverScroll = funds.getByRole('region', { name: '全市场成交额榜明细', exact: true });
  await expect(sectorScroll.locator('tbody tr')).toHaveCount(31);
  await expect(sectorPanel.getByRole('button', { name: /收起|展开|查看完整/ })).toHaveCount(0);
  await expect(turnoverScroll.locator('tbody tr')).toHaveCount(10);
  expect(
    await turnoverScroll.evaluate((node) => {
      const last = node.querySelector('tbody tr:last-child').getBoundingClientRect();
      return last.bottom <= node.getBoundingClientRect().top + node.clientHeight + 1;
    }),
  ).toBe(true);

  await expect(turnoverPanel.getByRole('button', { name: 'T10', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  const geometry = await funds.evaluate((node) => {
    const rect = (selector) => node.querySelector(selector).getBoundingClientRect();
    const left = rect('.industry-flow-panel'),
      right = rect('.fund-flow-right');
    const rotation = rect('.rotation-panel'),
      turnover = rect('.turnover-panel');
    return {
      leftHeight: left.height,
      rightHeight: right.height,
      rotationBottom: rotation.bottom,
      turnoverTop: turnover.top,
      bottom: node.getBoundingClientRect().bottom,
    };
  });
  expect(Math.abs(geometry.leftHeight - geometry.rightHeight)).toBeLessThan(1);
  expect(geometry.rotationBottom).toBeLessThan(geometry.turnoverTop);
  expect(geometry.bottom).toBeLessThanOrEqual(
    (await page.locator('#a-share-market-detail').boundingBox())!.y,
  );
  const heightBefore = (await funds.boundingBox())!.height;
  await turnoverPanel.getByRole('button', { name: 'T20', exact: true }).click();
  await expect(turnoverScroll.locator('tbody tr')).toHaveCount(20);
  expect((await funds.boundingBox())!.height).toBe(heightBefore);
  expect(await turnoverScroll.evaluate((node) => node.scrollHeight > node.clientHeight)).toBe(true);
  await turnoverScroll.hover();
  await page.mouse.wheel(0, 600);
  await expect.poll(() => turnoverScroll.evaluate((node) => node.scrollTop)).toBeGreaterThan(0);
  await sectorScroll.hover();
  await page.mouse.wheel(0, 600);
  await expect.poll(() => sectorScroll.evaluate((node) => node.scrollTop)).toBeGreaterThan(0);
  expect(
    await funds.evaluate(
      (node) => node.getBoundingClientRect().right <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await turnoverPanel.getByRole('button', { name: 'T10', exact: true }).click();
  await expect(turnoverScroll.locator('tbody tr')).toHaveCount(10);
  await page.setViewportSize({ width: 1440, height: 1200 });
  await sectorScroll.press('Control+Home');
  await funds.screenshot({ path: test.info().outputPath('funds-layout.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  expect(await turnoverScroll.evaluate((node) => node.scrollWidth > node.clientWidth)).toBe(true);
  await page.setViewportSize({ width: 1720, height: 1000 });
  const overview = page.locator('#aShare-market-overview');
  for (const label of ['上证综指', '上证50', '沪深300', '中证1000', '创业板指', '科创50'])
    await expect(
      overview.getByRole('button').filter({ has: page.getByText(label, { exact: true }) }),
    ).toBeVisible();
  const breadth = overview
    .locator('article')
    .filter({ has: page.getByRole('heading', { name: '大盘信息', exact: true }) });
  await expect(breadth.locator('.meta-action')).toHaveCount(3);
  for (const label of ['20日参与度', '50日参与度', '200日参与度', 'iVX50', 'Small/Large'])
    await expect(breadth.getByText(label, { exact: true })).toBeVisible();
  await expect(breadth.locator('.market-terminal__breadth-card')).toHaveCount(3);
  await expect(breadth.locator('.market-terminal__vol-card')).toHaveCount(2);
  const infoCards = breadth.locator('.meta-action, .market-terminal__info-card');
  await expect(infoCards).toHaveCount(10);
  await expect(infoCards.locator(':scope > span').first()).toHaveText('全A成交额');
  expect(
    await infoCards.evaluateAll((nodes) =>
      nodes.map((node) => node.querySelector(':scope > span')?.textContent?.trim()),
    ),
  ).toEqual([
    '全A成交额',
    '百亿成交股',
    '市场宽度',
    'iVX50',
    '中国10Y国债',
    '中国30Y国债',
    '20日参与度',
    '50日参与度',
    '200日参与度',
    'Small/Large',
  ]);
  await expect(breadth.locator('.china-treasury-info-card strong')).toHaveText([
    '1.50%（+8BP）',
    '2.03%（-1BP）',
  ]);
  const cardSizes = await infoCards.evaluateAll((nodes) =>
    nodes.map((node) => {
      const box = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return {
        width: Math.round(box.width),
        height: Math.round(box.height),
        border: style.border,
        radius: style.borderRadius,
        background: style.backgroundColor,
      };
    }),
  );
  for (const size of cardSizes) expect(size).toEqual(cardSizes[0]);
  const overviewGeometry = await overview.evaluate((node) => {
    const performance = node.querySelector('.market-terminal__overview-panel')!;
    const information = node.querySelector('.market-terminal__side-panel')!;
    const cards = performance.querySelectorAll('.market-terminal__market-card');
    return {
      topDifference: Math.abs(
        performance.getBoundingClientRect().top - information.getBoundingClientRect().top,
      ),
      bottomDifference: Math.abs(
        performance.getBoundingClientRect().bottom - information.getBoundingClientRect().bottom,
      ),
      bottomGap:
        performance.getBoundingClientRect().bottom -
        cards[cards.length - 1].getBoundingClientRect().bottom,
      columnGap:
        information.getBoundingClientRect().left - performance.getBoundingClientRect().right,
    };
  });
  expect(overviewGeometry.topDifference).toBeLessThan(2);
  expect(overviewGeometry.bottomDifference).toBeLessThan(2);
  expect(overviewGeometry.bottomGap).toBeLessThan(16);
  expect(overviewGeometry.columnGap).toBeGreaterThan(0);
  console.log('Overview desktop geometry', overviewGeometry);

  await expect(breadth.getByText('市场宽度', { exact: true })).toHaveCount(1);
  for (const name of ['市场情绪', '短线情绪'])
    await expect(page.getByRole('heading', { name, exact: true })).toHaveCount(0);
  for (const label of ['上证综指', '上证50']) {
    const card = overview
      .getByRole('button')
      .filter({ has: page.getByText(label, { exact: true }) });
    await expect(card.locator('em')).not.toContainText('—');
  }
  const summary = page.locator('.structure-summary');
  await expect(summary.locator('.structure-metric')).toHaveCount(7);
  await overview.screenshot({ path: test.info().outputPath('overview-layout.png') });
  const tops = await summary
    .locator('.structure-metric')
    .evaluateAll((nodes) => nodes.map((node) => node.getBoundingClientRect().top));
  expect(Math.max(...tops) - Math.min(...tops)).toBeLessThan(2);
  await breadth
    .getByRole('button')
    .filter({ has: page.getByText('市场宽度', { exact: true }) })
    .click();
  await expect(
    page.getByRole('dialog').getByRole('heading', { name: '市场宽度', exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  await summary.getByRole('button', { name: /连板梯队/ }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog').getByText('2板', { exact: true }).first()).toBeVisible();
  await page.getByRole('button', { name: 'Close', exact: true }).click();

  const fresh = await browser.newContext({ storageState: await page.context().storageState() });
  const view = await fresh.newPage();
  const firstOpen = Date.now();
  await view.goto(page.url(), { waitUntil: 'commit' });
  await expectDatedValue(view);
  const sidebarTypography = (target: Page) =>
    target.locator('.research-sidebar').evaluate((nav) =>
      ['a', 'button'].map((selector) => {
        const style = getComputedStyle(nav.querySelector(selector)!);
        return [style.fontFamily, style.fontSize, style.lineHeight, style.fontWeight];
      }),
    );
  const aShareTypography = await sidebarTypography(view);
  console.log('First authenticated open to dated breadth (ms)', Date.now() - firstOpen);
  await view.getByRole('button', { name: '宏观', exact: true }).click();
  await expect(view.getByRole('heading', { name: '市场总览' })).toBeVisible();
  expect(await sidebarTypography(view)).toEqual(aShareTypography);
  const returnAt = Date.now();
  await view.getByRole('button', { name: 'A股', exact: true }).click();
  await expectDatedValue(view);
  console.log('Market switch to dated breadth (ms)', Date.now() - returnAt);
  await view.setViewportSize({ width: 390, height: 844 });
  await expectDatedValue(view);
  expect(await view.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
  await view.screenshot({ path: test.info().outputPath('overview-mobile-layout.png') });
  await fresh.close();
});
