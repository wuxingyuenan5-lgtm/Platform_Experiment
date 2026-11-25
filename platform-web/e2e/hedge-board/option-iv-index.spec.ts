import { test, expect } from '@playwright/test';

test('all option IV underlyings show the matching index and preserve same-date gaps', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  const mappings = [
    { code: '000016', name: '上证50', underlyings: ['510050'], close: '2800.12' },
    { code: '000300', name: '沪深300', underlyings: ['510300'], close: '4000.34' },
    { code: '000905', name: '中证500', underlyings: ['510500'], close: '6000.56' },
    { code: '000688', name: '科创50', underlyings: ['588000', '588080'], close: '1200.78' },
  ];
  await page.route('**/research/a-share/financing', (route) =>
    route.fulfill({
      json: {
        margin: [],
        basis: [],
        goldIv: [],
        futuresSource: {},
        iv: {
          rows: [
            {
              date: '2015-02-09',
              underlying: '510050',
              month: '1503',
              value: '30.5',
              contracts: ['old-call', 'old-put'],
            },
            ...mappings.flatMap((item) =>
              item.underlyings.flatMap((underlying) => [
                {
                  date: '2026-11-04',
                  underlying,
                  month: '2611',
                  value: '20.5',
                  contracts: ['call', 'put'],
                },
                {
                  date: '2026-11-05',
                  underlying,
                  month: '2611',
                  value: '21.5',
                  contracts: ['call', 'put'],
                },
                {
                  date: '2026-11-04',
                  underlying,
                  month: '2612',
                  value: '25.5',
                  contracts: ['next-call', 'next-put'],
                },
              ]),
            ),
          ],
        },
        ivIndices: mappings.map((item) => ({
          ...item,
          rows: [{ date: '2026-11-04', close: item.close }],
        })),
      },
    }),
  );
  await page.goto('/#/hedge-board/a-share?view=capital&section=derivatives');
  await page.getByPlaceholder('请输入账号').fill('e2e_ceo');
  await page.getByPlaceholder('请输入密码').fill(process.env.E2E_CEO_PASSWORD!);
  await page.getByRole('button', { name: '登录', exact: true }).click();
  const chart = page.locator('.option-iv-chart');
  for (const item of mappings)
    for (const underlying of item.underlyings) {
      await page.getByLabel('期权标的', { exact: true }).selectOption(underlying);
      await chart.locator('.plot').scrollIntoViewIfNeeded();
      await expect(
        chart.locator('svg text').filter({ hasText: new RegExp('^' + item.name + '$') }),
      ).toBeVisible();
      await expect(chart.locator('svg text').filter({ hasText: /^点$/ })).toBeVisible();
      await chart.getByRole('button', { name: '查看数据', exact: true }).click();
      await expect(chart.locator('thead th').last()).toHaveText(`${item.name}（点）`);
      await expect(chart.locator('tbody tr').first().locator('td').last()).toHaveText('—');
      await expect(chart.locator('tbody tr').last().locator('td').last()).toHaveText(
        Number(item.close).toLocaleString('zh-CN'),
      );
      await page.getByLabel('期权月份', { exact: true }).selectOption('2612');
      await expect(chart.locator('tbody tr')).toHaveCount(1);
      await expect(chart.locator('tbody tr td').nth(1)).toHaveText('25.5');
      await expect(chart.locator('tbody tr td').last()).toHaveText(
        Number(item.close).toLocaleString('zh-CN'),
      );
      await chart.getByRole('button', { name: '图表', exact: true }).click();
    }
  await page.getByLabel('期权标的', { exact: true }).selectOption('510050');
  await chart.getByRole('button', { name: '全部', exact: true }).click();
  await chart.getByRole('button', { name: '查看数据', exact: true }).click();
  await expect(chart.locator('tbody tr')).toHaveCount(3);
  await expect(chart.locator('tbody tr').last().locator('th')).toHaveText('2015-02-09');
  await expect(chart.locator('tbody tr').last().locator('td').nth(1)).toHaveText('30.5');
  await expect(chart.locator('tbody tr').last().locator('td').last()).toHaveText('—');
});
