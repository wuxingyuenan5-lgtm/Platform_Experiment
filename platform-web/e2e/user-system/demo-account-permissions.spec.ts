import { expect, test, type Browser, type Page } from '@playwright/test';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';
const DEMO_ACCOUNTS = [
  { username: 'e2e_ceo', role: 'ceo', risk: true, write: true },
  { username: 'e2e_tech', role: 'tech_lead', risk: true, write: true },
  { username: 'e2e_employee_1', role: 'employee', risk: true, write: false },
  { username: 'e2e_employee_2', role: 'employee', risk: true, write: false },
  { username: 'e2e_employee_3', role: 'employee', risk: true, write: false },
  { username: 'e2e_vip_1', role: 'member', risk: false, write: false },
  { username: 'e2e_vip_2', role: 'member', risk: false, write: false },
  { username: 'e2e_vip_3', role: 'member', risk: false, write: false },
] as const;

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for demo-account browser acceptance`);
  return value;
}

function absoluteUrl(path: string): string {
  if (!path.startsWith('/api/')) return `${FRONTEND_ORIGIN}/#${path}`;
  return new URL(path, FRONTEND_ORIGIN).toString();
}

async function loginWithUi(page: Page, username: string, password: string): Promise<void> {
  await page.goto(absoluteUrl('/login'));
  await page.getByPlaceholder('请输入账号').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  const response = page.waitForResponse(
    (item) =>
      item.url().endsWith('/api/v1/auth/login') && item.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  expect((await response).ok()).toBe(true);
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 20_000 });
}

async function openAccount(browser: Browser, username: string, password: string) {
  const context = await browser.newContext({
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
  });
  const page = await context.newPage();
  await loginWithUi(page, username, password);
  return { page, close: () => context.close() };
}

async function expectForbiddenPage(page: Page, path: string): Promise<void> {
  await page.goto(absoluteUrl(path));
  await expect(page).toHaveURL(/\/exception\/403|\/403/, { timeout: 20_000 });
}

test('all eight reusable accounts keep self account access and obey risk, URL and API boundaries', async ({
  browser,
}) => {
  const password = requiredEnvironment('E2E_CEO_PASSWORD');

  for (const expected of DEMO_ACCOUNTS) {
    await test.step(expected.username, async () => {
      const account = await openAccount(browser, expected.username, password);
      try {
        const authResponse = await account.page.request.get(absoluteUrl('/api/v1/auth/me'));
        expect(authResponse.ok()).toBe(true);
        const authentication = await authResponse.json();
        expect(authentication.user.username).toBe(expected.username);
        expect(authentication.user.role).toBe(expected.role);

        await account.page.goto(absoluteUrl('/home/index'));
        if (expected.role === 'member') {
          await expect(account.page.getByText(/个人账号|我的资产/).first()).toBeVisible();
          await expect(account.page.getByText('风险管理', { exact: true })).toHaveCount(0);
          await expect(account.page.getByText('用户管理', { exact: true })).toHaveCount(0);
        } else {
          await expect(account.page.getByRole('heading', { name: '全球变量' })).toBeVisible();
          await expect(account.page.getByText('个人账号', { exact: true }).first()).toBeVisible();
          await expect(account.page.getByText('风险管理', { exact: true }).first()).toBeVisible();
        }

        await account.page.goto(absoluteUrl('/strategy/management'));
        await expect(
          account.page.getByTestId('strategy-management-original-structure'),
        ).toBeVisible();
        await expect(
          account.page.getByText('示例策略不可启停、部署或下单', { exact: true }),
        ).toBeVisible();
        if (expected.write) {
          await expect(account.page.getByRole('button', { name: '启停策略' })).toBeDisabled();
          await expect(account.page.getByRole('button', { name: '部署策略' })).toBeDisabled();
        } else {
          await expect(
            account.page.getByText('当前账号为只读权限', { exact: true }),
          ).toBeVisible();
          await expect(account.page.locator('[data-write-action="true"]')).toHaveCount(0);
        }

        await account.page.goto(absoluteUrl('/account/index'));
        await expect(account.page.getByText(/个人账号|我的资产/).first()).toBeVisible();
        await expect(
          account.page.getByText(expected.username, { exact: true }).first(),
        ).toBeVisible();

        const listResponse = await account.page.request.get(absoluteUrl('/api/v1/users'));
        if (!expected.risk) {
          expect(listResponse.status()).toBe(403);
          expect(
            (
              await account.page.request.get(
                absoluteUrl('/api/v1/users?search=e2e_ceo'),
              )
            ).status(),
          ).toBe(403);
          expect(
            (
              await account.page.request.get(
                absoluteUrl('/api/v1/users/not-the-current-member'),
              )
            ).status(),
          ).toBe(403);

          await account.page.goto(absoluteUrl('/account/index?id=e2e_ceo'));
          await expect(
            account.page.getByText(expected.username, { exact: true }).first(),
          ).toBeVisible();
          await expect(account.page.getByText('e2e_ceo', { exact: true })).toHaveCount(0);

          await expectForbiddenPage(account.page, '/risk');
          await expectForbiddenPage(account.page, '/risk/users');
        } else {
          expect(listResponse.ok()).toBe(true);
          await account.page.goto(absoluteUrl('/risk'));
          await expect(account.page).not.toHaveURL(/\/exception\/403|\/403/);
          await account.page.goto(absoluteUrl('/risk/users'));
          await expect(
            account.page.getByText('用户管理', { exact: true }).first(),
          ).toBeVisible();

          if (!expected.write) {
            const targetId = authentication.user.id || authentication.user.userId;
            expect(targetId).toBeTruthy();
            const denied = await account.page.request.patch(
              absoluteUrl(`/api/v1/users/${String(targetId)}/admin-note`),
              { data: { note: 'read-only-role-must-not-write' } },
            );
            expect(denied.status()).toBe(403);
          }
        }
      } finally {
        await account.close();
      }
    });
  }
});
