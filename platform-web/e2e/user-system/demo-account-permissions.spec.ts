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
    (item) => item.url().endsWith('/api/v1/auth/login') && item.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  expect((await response).ok()).toBe(true);
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 20_000 });
}

async function openAccount(browser: Browser, username: string, password: string) {
  const context = await browser.newContext({ locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await context.newPage();
  await loginWithUi(page, username, password);
  return { page, close: () => context.close() };
}

function findRecord(value: unknown, username: string): Record<string, unknown> | undefined {
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = findRecord(item, username);
      if (found) return found;
    }
    return undefined;
  }
  if (!value || typeof value !== 'object') return undefined;
  const record = value as Record<string, unknown>;
  if (record.username === username) return record;
  for (const item of Object.values(record)) {
    const found = findRecord(item, username);
    if (found) return found;
  }
  return undefined;
}

test('all eight reusable accounts obey menu URL API and personal-account boundaries', async ({ browser }) => {
  const password = requiredEnvironment('E2E_CEO_PASSWORD');
  const expectedUsernames = DEMO_ACCOUNTS.map((item) => item.username);

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
        await expect(account.page.getByRole('heading', { name: '全球变量' })).toBeVisible();

        await account.page.goto(absoluteUrl('/strategy/management'));
        await expect(account.page.getByRole('heading', { name: '策略管理' })).toBeVisible();
        if (expected.write) {
          await expect(account.page.getByText('部署策略（Live Write关闭）')).toBeVisible();
        } else {
          await expect(account.page.getByText('只读权限')).toBeVisible();
        }

        await account.page.goto(absoluteUrl('/account/index'));
        await expect(account.page.getByText(/个人账号|我的资产/).first()).toBeVisible();

        const listResponse = await account.page.request.get(absoluteUrl('/api/v1/users'));
        if (!expected.risk) {
          expect(listResponse.status()).toBe(403);
          await account.page.goto(absoluteUrl('/risk/users'));
          await expect(account.page).toHaveURL(/\/exception\/403|\/403/, { timeout: 20_000 });
        } else {
          expect(listResponse.ok()).toBe(true);
          const payload = await listResponse.json();
          const serialized = JSON.stringify(payload);
          for (const username of expectedUsernames) expect(serialized).toContain(username);

          await account.page.goto(absoluteUrl('/risk/users'));
          await expect(account.page.getByText('用户管理', { exact: true }).first()).toBeVisible();

          if (!expected.write) {
            const target = findRecord(payload, 'e2e_vip_1');
            expect(target?.id).toBeTruthy();
            const denied = await account.page.request.patch(
              absoluteUrl(`/api/v1/users/${String(target?.id)}/admin-note`),
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
