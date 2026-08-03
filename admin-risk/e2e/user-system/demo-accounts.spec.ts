import { expect, test, type Browser, type Page } from '@playwright/test';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';

interface AuthenticationResponse {
  user: {
    username: string;
    role: 'ceo' | 'tech_lead' | 'employee' | 'member';
  };
}

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
  const loginResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/auth/login') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  expect((await loginResponse).ok()).toBe(true);
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 20_000 });
}

async function openAccount(
  browser: Browser,
  username: string,
  password: string,
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({ locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await context.newPage();
  await loginWithUi(page, username, password);
  return { page, close: () => context.close() };
}

test('reusable demo accounts cover admin notes, roles and VIP asset views', async ({ browser }) => {
  const password = requiredEnvironment('E2E_CEO_PASSWORD');
  const accounts = [
    { username: 'e2e_ceo', role: 'ceo' },
    { username: 'e2e_tech', role: 'tech_lead' },
    { username: 'e2e_employee_1', role: 'employee' },
    { username: 'e2e_employee_2', role: 'employee' },
    { username: 'e2e_employee_3', role: 'employee' },
    {
      username: 'e2e_vip_1',
      role: 'member',
      marketValue: '100,000 USDT',
      returnValue: '+10,000 USDT',
    },
    {
      username: 'e2e_vip_2',
      role: 'member',
      marketValue: '65,000 USDT',
      returnValue: '-5,000 USDT',
    },
    {
      username: 'e2e_vip_3',
      role: 'member',
      marketValue: '200,000 USDT',
      returnValue: '+20,000 USDT',
    },
  ] as const;

  await test.step('CEO edits a VIP operational note from the user detail drawer', async () => {
    const account = await openAccount(browser, 'e2e_ceo', password);
    try {
      await account.page.goto(absoluteUrl('/risk/users'));
      await expect(account.page.getByText('用户管理', { exact: true }).first()).toBeVisible();
      const search = account.page.getByPlaceholder('搜索用户名、姓名、邮箱或手机号');
      await search.fill('e2e_vip_1');
      await search.press('Enter');
      await expect(account.page.getByText('e2e_vip_1', { exact: true })).toBeVisible();
      await account.page.getByRole('button', { name: '查看详情' }).click();
      await expect(account.page.getByText('运营备注', { exact: true })).toBeVisible();

      const note = `固定账号全流程验收 ${Date.now()}`;
      const noteInput = account.page.getByPlaceholder('例如：朋友介绍，已完成产品说明，下周回访。');
      await noteInput.fill(note);
      const saveResponse = account.page.waitForResponse(
        (response) =>
          response.url().includes('/api/v1/users/') &&
          response.url().endsWith('/admin-note') &&
          response.request().method() === 'PATCH',
      );
      await account.page.getByRole('button', { name: '保存备注' }).click();
      expect((await saveResponse).ok()).toBe(true);
      await expect(noteInput).toHaveValue(note);
    } finally {
      await account.close();
    }
  });

  for (const expected of accounts) {
    await test.step(`${expected.username} can log in with the seeded role`, async () => {
      const account = await openAccount(browser, expected.username, password);
      try {
        const authenticationResponse = await account.page.request.get(
          absoluteUrl('/api/v1/auth/me'),
        );
        expect(authenticationResponse.ok()).toBe(true);
        const authentication = (await authenticationResponse.json()) as AuthenticationResponse;
        expect(authentication.user.username).toBe(expected.username);
        expect(authentication.user.role).toBe(expected.role);

        if (expected.role === 'member') {
          await account.page.goto(absoluteUrl('/account/index'));
          await expect(account.page.getByText('我的资产', { exact: true })).toBeVisible();
          await expect(
            account.page.getByText(expected.marketValue, { exact: true }).first(),
          ).toBeVisible();
          await expect(
            account.page.getByText(expected.returnValue, { exact: true }).first(),
          ).toBeVisible();
          await expect(account.page.getByText('DEMO-USDT · USDT', { exact: true })).toBeVisible();
        } else {
          await account.page.goto(absoluteUrl('/risk/users'));
          await expect(account.page.getByText('用户管理', { exact: true }).first()).toBeVisible();
        }
      } finally {
        await account.close();
      }
    });
  }
});
