import { expect, test } from '@playwright/test';

test('overview omits the funding Demo and keeps other capital categories accessible', async ({
  page,
}, testInfo) => {
  await page.route('**/*', (route) =>
    ['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)
      ? route.continue()
      : route.abort(),
  );
  await page.route('**/api/v1/research/a-share/capital', (route) =>
    route.fulfill({
      json: {
        asOf: '2026-11-09',
        sources: {
          issuance: { status: 'ready', rows: [] },
          buybacks: { status: 'ready', rows: [] },
          holders: { status: 'ready', rows: [] },
          unlocks: { status: 'ready', rows: [] },
        },
        macro: {},
        moneyCreditGap: [],
        unlockWeeks: [],
        etf: { rows: [] },
        handbook: {
          source: '隔离验收数据',
          fetchedAt: '2026-11-09T00:00:00Z',
          institutions: [
            { date: '2026-03-31', fund: '1000', insurance: '500', broker: '200' },
            { date: '2026-06-30', fund: '1234', insurance: '567' },
            { date: '2026-09-30', fund: '1500', insurance: '450', broker: '270' },
          ],
          issues: [{ date: '2026-09-01', stock: '100', mixed: '200' }],
          bank: [
            {
              date: '2026-09-30',
              assets: '30.5',
              investmentAssets: '32',
              equityPct: '3.5',
              bonds: '20',
              nonstandard: '2',
              equity: '1.12',
            },
          ],
          residents: [
            { date: '2025-01-31', personal: '100' },
            { date: '2025-02-28', personal: '120' },
          ],
        },
      },
    }),
  );
  await page.goto('/#/hedge-board/a-share?view=capital&section=overview&capitalMode=demo');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const panel = page.getByRole('region', { name: 'A股资金面', exact: true });
  const mode = panel.getByRole('navigation', { name: '资金面数据模式' });
  const change = panel.getByRole('group', { name: '机构持股市值变动', exact: true });
  await expect(change.getByRole('heading')).toHaveCount(1);
  await expect(
    change.locator('header').getByRole('button', { name: '机构持股市值变动' }),
  ).toHaveAttribute('aria-pressed', 'true');
  for (const color of ['#174e76', '#ce9a42']) {
    await expect(change.locator(`.plot svg path[fill="${color}"]`).first()).toBeVisible();
  }
  await change.getByRole('button', { name: '查看数据', exact: true }).click();
  await expect(change.locator('tbody tr')).toHaveCount(1);
  await expect(change.locator('tbody tr')).toContainText('2026-09-30');
  await expect(change.getByRole('cell', { name: '500', exact: true })).toBeVisible();
  await expect(change.getByRole('cell', { name: '-50', exact: true })).toBeVisible();
  await panel.getByLabel('机构角色', { exact: true }).selectOption('broker');
  await expect(change.getByRole('cell', { name: '70', exact: true })).toBeVisible();
  await panel.getByLabel('机构角色', { exact: true }).selectOption('main');
  await panel.getByRole('button', { name: '主要机构披露持股市值', exact: true }).click();
  const institutionValue = panel.getByRole('group', { name: '主要机构披露持股市值', exact: true });
  await expect(institutionValue.getByRole('heading')).toHaveCount(1);
  for (const color of ['#174e76', '#ce9a42']) {
    await expect(institutionValue.locator(`.plot svg path[fill="${color}"]`).first()).toBeVisible();
  }
  await expect(mode).toHaveCount(0);
  await expect(panel.getByRole('heading', { name: '融资余额月变化', exact: true })).toHaveCount(0);
  await expect(panel.locator('.handbook-demo')).toHaveCount(0);
  const demo = panel.getByRole('group', { name: '资金流入流出与供需差额 · Demo', exact: true });
  await expect(demo).toHaveCount(0);
  await panel.getByRole('button', { name: 'ETF跟踪', exact: true }).click();
  await expect(mode).toHaveCount(0);
  await expect(panel.locator('.handbook-demo')).toHaveCount(0);
  const etfTabs = panel.getByRole('navigation', { name: 'ETF研究分类' });
  await expect(etfTabs.getByRole('button')).toHaveText(['ETF总览', '盘中监测', '主题ETF']);
  for (const name of ['ETF总览', '盘中监测', '主题ETF']) {
    await etfTabs.getByRole('button', { name, exact: true }).click();
    await expect(panel.getByRole('region', { name: 'ETF跟踪', exact: true })).toBeVisible();
    await expect(mode).toHaveCount(0);
    await expect(panel.locator('.handbook-demo')).toHaveCount(0);
  }
  await panel.getByRole('button', { name: '两融', exact: true }).click();
  await expect(panel.getByRole('region', { name: '两融变化', exact: true })).toBeVisible();
  await expect(mode).toHaveCount(0);
  await expect(panel.locator('.handbook-demo')).toHaveCount(0);
  await panel.getByRole('button', { name: '公募', exact: true }).click();
  await expect(mode).toHaveCount(0);
  await expect(panel.locator('.handbook-demo')).toHaveCount(2);
  await expect(panel.locator('.demo-directory')).toHaveCount(0);
  const allocation = panel.getByRole('region', {
    name: '行业配置、环比与历史分位 · Demo',
    exact: true,
  });
  const holdings = panel.getByRole('region', {
    name: 'A股前二十大重仓股与季度变化 · Demo',
    exact: true,
  });
  await expect(allocation.locator('tbody tr')).toHaveCount(13);
  await expect(holdings.locator('tbody tr')).toHaveCount(20);
  expect(
    await panel.evaluate((el) =>
      Array.from(el.children)
        .slice(-3)
        .map((c) => c.getAttribute('aria-label')),
    ),
  ).toEqual([
    '扩展研究 · 行业持股偏好',
    '行业配置、环比与历史分位 · Demo',
    'A股前二十大重仓股与季度变化 · Demo',
  ]);
  await allocation.getByRole('button', { name: '按环比排序', exact: true }).click();
  const changes = await allocation
    .locator('tbody tr')
    .evaluateAll((rows) => rows.map((r) => Number(r.children[3].textContent?.replaceAll(',', ''))));
  expect(changes).toEqual([...changes].sort((a, b) => b - a));
  await allocation.getByRole('combobox').selectOption('2025-12-31');
  await expect(allocation.locator('caption')).toContainText('2025-12-31 · Demo · 模拟数据');
  await allocation.getByPlaceholder('证券、行业或机构').fill('电子');
  await expect(allocation.locator('tbody tr')).toHaveCount(1);
  await allocation.getByPlaceholder('证券、行业或机构').clear();
  await holdings.getByPlaceholder('证券、行业或机构').fill('示例证券01');
  await expect(holdings.locator('tbody tr')).toHaveCount(1);
  await holdings.getByPlaceholder('证券、行业或机构').clear();
  await holdings
    .getByRole('button', { name: '放大图表：A股前二十大重仓股与季度变化 · Demo', exact: true })
    .click();
  const expanded = holdings.getByRole('dialog');
  await expect(expanded.locator('caption')).toContainText('Demo · 模拟数据');
  await expanded
    .getByRole('button', { name: '关闭放大：A股前二十大重仓股与季度变化 · Demo', exact: true })
    .click();
  await page.setViewportSize({ width: 1920, height: 1100 });
  await allocation.scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('funds-allocation-demo-desktop.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await holdings.scrollIntoViewIfNeeded();
  const mobileMask = page.locator('.ant-drawer-mask');
  if (await mobileMask.isVisible()) {
    await mobileMask.click({ position: { x: 380, y: 800 } });
    await expect(mobileMask).toBeHidden();
  }
  await holdings.scrollIntoViewIfNeeded();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
  ).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('funds-holdings-demo-mobile.png') });
  await page.setViewportSize({ width: 1920, height: 1100 });
  await panel.getByRole('button', { name: '其他资金', exact: true }).click();
  await expect(mode).toHaveCount(0);
  const categoryNav = panel.getByRole('navigation', { name: '其他资金分类' });
  await expect(categoryNav.locator('button > span')).toHaveText([
    '外资',
    '险资',
    '养老资金',
    '居民资金',
    '私募',
    '产业资本',
    '融资需求',
    '银行理财',
  ]);
  const expectedDemos: Record<string, string[]> = {
    外资: ['外资前十大行业持仓变迁', '外资股票市值及A股市值占比'],
    险资: ['险资行业配置与估值剔除', '新增保费与潜在权益配置'],
    养老资金: ['企业年金积累规模与收益', '职业年金投资运营规模', '社保持股市值与估值剔除变化'],
    居民资金: ['新开户与市场表现'],
    私募: [],
    产业资本: ['产业资本增持、减持与净额'],
    融资需求: ['IPO、再融资、回购与分红'],
    银行理财: [],
  };
  for (const [name, titles] of Object.entries(expectedDemos)) {
    await categoryNav.getByRole('button', { name: new RegExp('^' + name) }).click();
    await expect(mode).toHaveCount(0);
    const demos = panel.locator('.capital-handbook > .handbook-demo');
    await expect(demos).toHaveCount(titles.length + Number(name === '外资'));
    await expect(demos.locator('.analysis-heading h3')).toHaveText(titles);
    if (titles.length) {
      await expect(demos.locator('.demo-badge')).toHaveText(titles.map(() => '模拟数据'));
      expect(
        await panel.locator('.capital-handbook').evaluate(
          (el, count) =>
            Array.from(el.children)
              .slice(-count)
              .every((child) => child.classList.contains('handbook-demo')),
          titles.length,
        ),
      ).toBeTruthy();
    }
    if (name === '外资') {
      const comparison = panel.getByRole('region', {
        name: '外资流量与宏观变量 · Demo',
        exact: true,
      });
      let flow: string | null = null;
      for (const id of ['foreign-pmi', 'foreign-yield', 'foreign-fx', 'foreign-relative']) {
        await comparison
          .locator('header')
          .getByLabel('外资比较变量', { exact: true })
          .selectOption(id);
        await comparison.getByRole('button', { name: '查看数据', exact: true }).click();
        const currentFlow = await comparison
          .locator('tbody tr')
          .first()
          .locator('td')
          .first()
          .textContent();
        if (flow === null) flow = currentFlow;
        expect(currentFlow).toBe(flow);
        await expect(comparison.locator('thead th')).toHaveCount(3);
      }
    }
    if (name === '居民资金') {
      await expect(
        panel.getByRole('heading', { name: '上交所个人A股新开户', exact: true }),
      ).toBeVisible();
      const annual = panel.locator('.capital-bars').filter({ hasText: '个人A股新开户年度累计' });
      await expect(annual).toHaveCount(0);
      await expect(
        panel.getByRole('heading', { name: '个人A股开户季节性', exact: true }),
      ).toHaveCount(0);
    }
    if (name === '银行理财') {
      await expect(panel.getByLabel('银行理财规模摘要', { exact: true })).toContainText('30.5');
      await expect(
        panel.getByRole('heading', { name: '理财权益配置比例', exact: true }),
      ).toBeVisible();
      const history = panel
        .locator('.financing-chart')
        .filter({ hasText: '银行理财存续与投资规模' });
      await expect(history).toHaveCount(0);
      await expect(panel.getByRole('heading', { name: '理财资产配置', exact: true })).toHaveCount(
        0,
      );
    }
  }
  await panel.getByRole('button', { name: '总览', exact: true }).click();
  await expect(mode).toHaveCount(0);
  await expect(demo).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  if (await mobileMask.isVisible()) {
    await mobileMask.click({ position: { x: 380, y: 800 } });
    await expect(mobileMask).toBeHidden();
  }
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
  ).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('capital-overview-mobile.png') });
});

test('capital summary and ETF controls share the workspace header while intraday provenance stays in the chart', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1920, height: 1100 });
  await page.route('**/*', (route) => {
    const url = new URL(route.request().url());
    return ['127.0.0.1', 'localhost'].includes(url.hostname) ? route.continue() : route.abort();
  });
  await page.route('**/api/v1/research/a-share/capital', (route) =>
    route.fulfill({
      json: {
        asOf: '2026-11-08',
        sources: {
          issuance: { status: 'ready', rows: [{ date: '2026-10-01', total: '1442.84' }] },
        },
        macro: {
          cn_margin_financing_balance: {
            latestValue: '22785.14',
            observationDate: '2026-11-05',
            status: 'ready',
          },
          cn_dr007: { latestValue: '1.36', observationDate: '2026-11-02', status: 'stale' },
        },
        etf: { status: 'ready', rows: [{ date: '2026-11-06', value: '47.99' }] },
        broadEtf: {
          status: 'ready',
          date: '2026-11-06',
          basketCount: 220,
          coveredCount: 220,
          flow1Yi: '57.51',
          flow5Yi: '2028.28',
        },
        comparisons: { marginChange5d: '-781.94', etfFlow5d: '1849.52', rateSpreadBp: null },
      },
    }),
  );
  await page.goto('/#/hedge-board/a-share?view=capital&section=etf');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const metrics = page.locator('.capital-panel > .metric-strip');
  await expect(metrics.locator('article')).toHaveCount(4);
  await expect(metrics.locator('article').nth(1)).toContainText('宽基ETF（220只）');
  await expect(metrics.locator('article').nth(1)).toContainText('57.51');
  await expect(metrics.locator('article').nth(1)).toContainText('2,028.28');
  await expect(metrics).not.toContainText('1,849.52');
  const primary = page.getByRole('navigation', { name: '资金面分类' });
  const secondary = page.getByRole('navigation', { name: 'ETF研究分类' });
  await expect(secondary.getByRole('button')).toHaveText(['ETF总览', '盘中监测', '主题ETF']);
  const broadFlow = page.getByRole('region', { name: '宽基ETF资金图表与数据表' });
  await expect(broadFlow.getByRole('heading')).toHaveText('宽基ETF日度净流入与累计净流入');
  await expect(broadFlow.getByRole('button', { name: '1年', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  const navBoxes = await Promise.all([primary.boundingBox(), secondary.boundingBox()]);
  expect(Math.abs(navBoxes[0]!.y - navBoxes[1]!.y)).toBeLessThan(3);
  expect((await metrics.boundingBox())!.y).toBeLessThan(navBoxes[0]!.y);
  await expect(page.getByRole('heading', { name: 'ETF跟踪', exact: true })).toHaveCount(0);
  for (const card of await metrics.locator('article').all()) {
    const note = card.locator('.metric-comparison');
    if (await note.count()) {
      const value = await card.locator('strong').boundingBox();
      const comparison = await note.boundingBox();
      expect(comparison!.x).toBeGreaterThanOrEqual(value!.x + value!.width - 1);
      expect(comparison!.y).toBeLessThan(value!.y + value!.height);
    }
  }
  await secondary.getByRole('button', { name: '盘中监测', exact: true }).click();
  const intraday = page.getByRole('region', { name: '盘中ETF监测' });
  const source = intraday.locator('.intraday-primary-chart .intraday-provenance');
  await expect(source).toContainText('分时截至');
  await expect(intraday.locator('.observation-provenance')).toHaveCount(0);
  await expect(intraday.locator('#chart svg')).toHaveCount(1);
  await primary.getByRole('button', { name: '两融变化', exact: true }).click();
  await expect(secondary).toHaveCount(0);
  await expect(metrics.locator('article')).toHaveCount(4);
  await primary.getByRole('button', { name: 'ETF跟踪', exact: true }).click();
  await expect(secondary.getByRole('button', { name: '盘中监测', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await secondary.getByRole('button', { name: '主题ETF', exact: true }).click();
  await expect(page.getByText('单只ETF完整分析', { exact: true })).toBeVisible();
  await secondary.getByRole('button', { name: '盘中监测', exact: true }).click();
  await page.getByRole('button', { name: '刷新当前页', exact: true }).click();
  await expect(source).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('capital-desktop.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(source).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1),
  ).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('capital-mobile.png') });
});

test('public funds combine size and share changes and reveal fund tracking only after search', async ({
  page,
}) => {
  await page.route('**/*', (route) =>
    ['127.0.0.1', 'localhost'].includes(new URL(route.request().url()).hostname)
      ? route.continue()
      : route.abort(),
  );
  await page.route('**/api/v1/research/a-share/capital', (route) =>
    route.fulfill({
      json: {
        asOf: '2026-11-09',
        sources: { issuance: { status: 'ready', rows: [] } },
        macro: {},
        moneyCreditGap: [],
        unlockWeeks: [],
        etf: { rows: [] },
        institutions: {
          public: {
            provider: '隔离统计',
            status: 'ready',
            rows: [
              {
                date: '2026-08-31',
                basis: 'all',
                stockAssets: '30000',
                mixedAssets: '40000',
                bondAssets: '90000',
                moneyAssets: '100000',
                stockShares: '21000',
                mixedShares: '32000',
              },
              {
                date: '2026-09-30',
                basis: 'all',
                stockAssets: '31000',
                mixedAssets: '42000',
                bondAssets: '95000',
                moneyAssets: '110000',
                stockShares: '22000',
                mixedShares: '33000',
              },
            ],
          },
        },
        handbook: {
          holdings: [{ date: '2026-09-30', name: '电子', code: 'B_009001006006', fund: '12.3' }],
          issues: [
            { date: '2026-09-01', stock: '100', mixed: '200', stockCount: 10, mixedCount: 20 },
          ],
        },
      },
    }),
  );
  await page.route('**/api/v1/research/a-share/mutual-funds?*', (route) =>
    route.fulfill({ json: fundFixture() }),
  );
  await page.route('**/api/v1/research/a-share/mutual-funds', (route) =>
    route.fulfill({ json: fundFixture() }),
  );
  await page.route('**/api/v1/research/a-share/mutual-funds/000001', (route) =>
    route.fulfill({
      json: {
        fund: { code: '000001', name: '查询基金01', type: '股票型', classes: [] },
        status: 'ready',
        attemptedAt: '2026-11-09T00:00:00Z',
        sources: {},
        data: {},
      },
    }),
  );
  function fundFixture() {
    return {
      date: '2026-09-30',
      expectedPeriod: '2026-09-30',
      dates: ['2026-09-30'],
      status: 'ready',
      history: [],
      stocks: Array.from({ length: 25 }, (_, i) => ({
        code: String(i),
        name: '股票' + String(i + 1).padStart(2, '0'),
        market: 'CN',
        valueYuan: '100000000',
        shares: '1000',
      })),
      funds: Array.from({ length: 25 }, (_, i) => ({
        code: String(i + 1).padStart(6, '0'),
        name: '查询基金' + String(i + 1).padStart(2, '0'),
        type: '股票型',
        classes: [],
        date: '2026-09-30',
      })),
    };
  }
  await page.goto('/#/hedge-board/a-share?view=capital&section=funds&capitalMode=demo');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const panel = page.getByRole('region', { name: 'A股资金面', exact: true });
  await expect(panel.getByRole('heading', { name: '规模与份额变化', exact: true })).toBeVisible();
  for (const title of ['公募基金资产净值', '股票与混合基金份额月变化', '新成立股票、混合基金份额'])
    await expect(panel.getByRole('heading', { name: title, exact: true })).toBeVisible();
  for (const title of [
    '股票基金',
    '混合基金',
    '债券基金',
    '货币市场基金',
    '新成立基金数量',
    '权益类基金发行季节性',
    '股票与混合基金份额',
  ])
    await expect(panel.getByRole('heading', { name: title, exact: true })).toHaveCount(0);
  await expect(panel.getByRole('navigation', { name: '资金面数据模式' })).toHaveCount(0);
  const holdingPreference = panel
    .locator('.capital-bars')
    .filter({ hasText: '基金 · 行业持股比例' });
  await expect(holdingPreference).toBeVisible();
  await holdingPreference.scrollIntoViewIfNeeded();
  await expect(holdingPreference.locator('canvas, svg').last()).toBeVisible();
  await expect(
    panel.getByRole('heading', { name: '扩展研究 · 行业持股偏好', exact: true }),
  ).toBeVisible();
  await expect(panel.getByRole('heading', { name: '行业配置', exact: true })).toBeVisible();
  const stocks = panel.getByRole('region', { name: '公募重仓股排行', exact: true });
  await expect(stocks.locator('tbody tr')).toHaveCount(20);
  await panel.getByPlaceholder('名称 / 代码', { exact: true }).fill('股票01');
  await expect(stocks.locator('tbody tr')).toHaveCount(1);
  await panel.getByPlaceholder('名称 / 代码', { exact: true }).clear();
  await expect(stocks.locator('tbody tr')).toHaveCount(20);
  const list = panel.getByRole('region', { name: '基金列表', exact: true });
  await expect(list).toHaveCount(0);
  const search = panel.getByPlaceholder('基金、代码、现任经理');
  await search.fill('查询基金01');
  await expect(list.locator('tbody tr')).toHaveCount(1);
  await list.getByRole('button', { name: /查询基金01/ }).click();
  await expect(panel.getByRole('region', { name: '单基金历史', exact: true })).toContainText(
    '查询基金01',
  );
  await search.clear();
  await expect(list).toHaveCount(0);
  await expect(panel.getByRole('region', { name: '单基金历史', exact: true })).toHaveCount(0);
});
