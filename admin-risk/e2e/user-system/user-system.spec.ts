import { randomUUID } from 'node:crypto';

import {
  expect,
  test,
  type APIRequestContext,
  type APIResponse,
  type Browser,
  type Page,
} from '@playwright/test';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';
const SESSION_COOKIE_NAME = 'vg_session';

interface AuthenticationResponse {
  user: {
    userId: string;
    username: string;
    role: 'ceo' | 'tech_lead' | 'employee' | 'member';
  };
  permissions: string[];
  csrfToken: string;
}

interface UserSummary {
  userId: string;
  username: string;
  email?: string | null;
  contactMasked: boolean;
  role?: string | null;
  requestedRole?: string | null;
  rowVersion: number;
}

interface UserPage {
  items: UserSummary[];
}

interface ManagedUserResponse {
  user: UserSummary;
  resetTicket: string;
}

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for the user-system browser E2E suite`);
  return value;
}

function absoluteUrl(path: string): string {
  if (!path.startsWith('/api/')) return `${FRONTEND_ORIGIN}/#${path}`;
  return new URL(path, FRONTEND_ORIGIN).toString();
}

async function jsonResponse<T>(response: APIResponse): Promise<T> {
  const body = await response.text();
  expect(response.ok(), `${response.status()} ${response.statusText()}\n${body}`).toBeTruthy();
  return body ? (JSON.parse(body) as T) : (undefined as T);
}

async function loginWithUi(page: Page, username: string, password: string): Promise<void> {
  await page.goto(absoluteUrl('/login'));
  await expect(page.getByText('欢迎登录', { exact: true })).toBeVisible();
  await page.getByPlaceholder('请输入账号').fill(username);
  await page.getByPlaceholder('请输入密码').fill(password);
  const loginResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/auth/login') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '登录', exact: true }).click();
  expect((await loginResponse).ok()).toBeTruthy();
  await expect(page).not.toHaveURL(/\/login(?:\?|$)/, { timeout: 20_000 });
}

async function getAuthentication(page: Page): Promise<AuthenticationResponse> {
  return jsonResponse<AuthenticationResponse>(
    await page.request.get(absoluteUrl('/api/v1/auth/me')),
  );
}

async function sessionMutation<T>(
  page: Page,
  csrfToken: string,
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  data?: object,
): Promise<T> {
  return jsonResponse<T>(
    await page.request.fetch(absoluteUrl(path), {
      method,
      data,
      headers: {
        Origin: FRONTEND_ORIGIN,
        'X-CSRF-Token': csrfToken,
      },
    }),
  );
}

async function resetManagedPassword(
  request: APIRequestContext,
  username: string,
  resetTicket: string,
  password: string,
): Promise<void> {
  await jsonResponse(
    await request.post(absoluteUrl('/api/v1/auth/reset-password'), {
      headers: { Origin: FRONTEND_ORIGIN },
      data: {
        username,
        resetTicket,
        newPassword: password,
        newPasswordConfirmation: password,
      },
    }),
  );
}

async function openRolePage(
  browser: Browser,
  username: string,
  password: string,
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({ locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
  const page = await context.newPage();
  await loginWithUi(page, username, password);
  return { page, close: () => context.close() };
}

test('completes isolated four-role browser acceptance without Live Write', async ({
  browser,
  page,
  request,
}) => {
  const ceoUsername = requiredEnvironment('E2E_CEO_USERNAME');
  const ceoPassword = requiredEnvironment('E2E_CEO_PASSWORD');
  const token = randomUUID().replaceAll('-', '').slice(0, 12);
  const memberUsername = `e2e_member_${token}`;
  const techLeadUsername = `e2e_tech_${token}`;
  const employeeUsername = `e2e_employee_${token}`;
  const memberEmail = `${memberUsername}@example.invalid`;
  const memberPassword = `Mm9!${randomUUID()}`;
  const memberNewPassword = `Nn8!${randomUUID()}`;
  const techLeadPassword = `Tt7!${randomUUID()}`;
  const employeePassword = `Ee6!${randomUUID()}`;

  await test.step('public registration is pending and cannot log in', async () => {
    await page.goto(absoluteUrl('/register-apply'));
    await page.getByRole('textbox', { name: /账号$/ }).fill(memberUsername);
    await page.getByPlaceholder('请输入姓名').fill('E2E Member');
    await page.getByRole('textbox', { name: '邮箱' }).fill(memberEmail);
    await page.getByPlaceholder('至少 12 个字符').fill(memberPassword);
    await page.getByPlaceholder('请再次输入密码').fill(memberPassword);
    await page.getByPlaceholder('请简要说明申请用途').fill('GitHub Actions isolated browser acceptance');
    await page.getByRole('checkbox').check();
    await page.getByRole('button', { name: '提交申请' }).click();
    await expect(page).toHaveURL(/\/login$/);

    await page.getByPlaceholder('请输入账号').fill(memberUsername);
    await page.getByPlaceholder('请输入密码').fill(memberPassword);
    const pendingResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/v1/auth/login') && response.request().method() === 'POST',
    );
    await page.getByRole('button', { name: '登录', exact: true }).click();
    expect((await pendingResponse).status()).toBe(403);
    await expect(page.getByText('账号正在等待审核')).toBeVisible();
    await page.getByRole('dialog').getByRole('button', { name: /确\s*认/ }).click();
  });

  let memberUserId = '';
  let techLeadResetTicket = '';
  let employeeResetTicket = '';

  await test.step('CEO approves registration and prepares role and holding fixtures', async () => {
    await loginWithUi(page, ceoUsername, ceoPassword);

    const cookies = await page.context().cookies();
    const sessionCookie = cookies.find((cookie) => cookie.name === SESSION_COOKIE_NAME);
    expect(sessionCookie).toBeDefined();
    expect(sessionCookie?.httpOnly).toBe(true);
    expect(sessionCookie?.sameSite).toBe('Lax');
    expect(sessionCookie?.path).toBe('/');
    expect(await page.evaluate((name) => document.cookie.includes(`${name}=`), SESSION_COOKIE_NAME)).toBe(
      false,
    );

    await page.goto(absoluteUrl('/risk/users'));
    await expect(page.getByText('用户管理', { exact: true }).first()).toBeVisible();

    const authentication = await getAuthentication(page);
    expect(authentication.user.role).toBe('ceo');
    expect(authentication.permissions).not.toContain('*');
    expect(authentication.permissions.some((permission) => permission.includes('live'))).toBe(false);
    const csrfToken = authentication.csrfToken;

    await sessionMutation(page, csrfToken, 'POST', '/api/v1/auth/reauth', {
      password: ceoPassword,
    });

    const pendingUsers = await jsonResponse<UserPage>(
      await page.request.get(
        absoluteUrl(`/api/v1/users?search=${encodeURIComponent(memberUsername)}&pageSize=20`),
      ),
    );
    const pendingMember = pendingUsers.items.find((item) => item.username === memberUsername);
    expect(pendingMember).toBeDefined();
    memberUserId = pendingMember?.userId ?? '';

    await sessionMutation(page, csrfToken, 'POST', `/api/v1/users/${memberUserId}/approve`, {
      finalRole: 'member',
      expectedVersion: pendingMember?.rowVersion,
    });

    const techLead = await sessionMutation<ManagedUserResponse>(
      page,
      csrfToken,
      'POST',
      '/api/v1/users',
      {
        username: techLeadUsername,
        realName: 'E2E Technical Lead',
        email: `${techLeadUsername}@example.invalid`,
        role: 'tech_lead',
      },
    );
    techLeadResetTicket = techLead.resetTicket;

    const employee = await sessionMutation<ManagedUserResponse>(
      page,
      csrfToken,
      'POST',
      '/api/v1/users',
      {
        username: employeeUsername,
        realName: 'E2E Employee',
        email: `${employeeUsername}@example.invalid`,
        role: 'employee',
        department: 'E2E Research',
      },
    );
    employeeResetTicket = employee.resetTicket;

    const now = new Date().toISOString();
    await sessionMutation(page, csrfToken, 'PUT', '/api/v1/users/holdings/funds/fund_default/nav', {
      unitNav: '120.00',
      valuationTime: now,
      currency: 'USDT',
      source: 'manual_admin',
      fundCode: 'E2E-FUND',
    });
    const holding = await sessionMutation<{
      shareQuantity: string;
      marketValue: string;
      cumulativeReturn: string;
      returnRate: string;
    }>(page, csrfToken, 'PUT', `/api/v1/users/${memberUserId}/holdings/fund_default`, {
      shareQuantity: '10.5',
      cumulativeInvested: '1000.00',
      confirmedAt: now,
      asOf: now,
      source: 'manual_admin',
      status: 'active',
    });
    expect(holding.shareQuantity).toBe('10.5');
    expect(holding.marketValue).toBe('1260');
    expect(holding.cumulativeReturn).toBe('260');
    expect(holding.returnRate).toBe('0.26');

    await sessionMutation(page, csrfToken, 'POST', '/api/v1/auth/logout');
    await page.goto(absoluteUrl('/login'));
  });

  await resetManagedPassword(request, techLeadUsername, techLeadResetTicket, techLeadPassword);
  await resetManagedPassword(request, employeeUsername, employeeResetTicket, employeePassword);

  await test.step('technical lead sees regular-user detail but protected roles stay masked', async () => {
    const rolePage = await openRolePage(browser, techLeadUsername, techLeadPassword);
    try {
      await rolePage.page.goto(absoluteUrl('/risk/users'));
      await expect(rolePage.page.getByText('用户管理', { exact: true }).first()).toBeVisible();

      const ceoPage = await jsonResponse<UserPage>(
        await rolePage.page.request.get(
          absoluteUrl(`/api/v1/users?search=${encodeURIComponent(ceoUsername)}`),
        ),
      );
      const ceo = ceoPage.items.find((item) => item.username === ceoUsername);
      expect(ceo?.contactMasked).toBe(true);

      const protectedDetail = await jsonResponse<UserSummary>(
        await rolePage.page.request.get(absoluteUrl(`/api/v1/users/${ceo?.userId}`)),
      );
      expect(protectedDetail.contactMasked).toBe(true);

      const memberDetail = await jsonResponse<UserSummary>(
        await rolePage.page.request.get(absoluteUrl(`/api/v1/users/${memberUserId}`)),
      );
      expect(memberDetail.contactMasked).toBe(false);
      expect(memberDetail.email).toBe(memberEmail);
    } finally {
      await rolePage.close();
    }
  });

  await test.step('employee user directory remains masked', async () => {
    const rolePage = await openRolePage(browser, employeeUsername, employeePassword);
    try {
      await rolePage.page.goto(absoluteUrl('/risk/users'));
      await expect(rolePage.page.getByText('用户管理', { exact: true }).first()).toBeVisible();
      const users = await jsonResponse<UserPage>(
        await rolePage.page.request.get(
          absoluteUrl(`/api/v1/users?search=${encodeURIComponent(memberUsername)}`),
        ),
      );
      expect(users.items).toHaveLength(1);
      expect(users.items[0]?.contactMasked).toBe(true);
    } finally {
      await rolePage.close();
    }
  });

  await test.step('member profile, avatar, holdings, CSRF and session invalidation work in browser', async () => {
    const primaryContext = await browser.newContext({ locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    const secondaryContext = await browser.newContext({ locale: 'zh-CN', timezoneId: 'Asia/Shanghai' });
    try {
      const primaryPage = await primaryContext.newPage();
      const secondaryPage = await secondaryContext.newPage();
      await loginWithUi(primaryPage, memberUsername, memberPassword);
      await loginWithUi(secondaryPage, memberUsername, memberPassword);

      await primaryPage.goto(absoluteUrl('/account/index'));
      await expect(primaryPage.getByText('个人账号', { exact: true }).first()).toBeVisible();
      const sessions = await jsonResponse<{ items: unknown[] }>(
        await primaryPage.request.get(absoluteUrl('/api/v1/me/sessions')),
      );
      expect(sessions.items.length).toBeGreaterThanOrEqual(2);

      const sameSessionTab = await primaryContext.newPage();
      await sameSessionTab.goto(absoluteUrl('/account/index'));
      await expect(sameSessionTab.getByText('个人账号', { exact: true }).first()).toBeVisible();

      const displayNameInput = primaryPage.getByLabel('展示名称');
      await displayNameInput.fill('E2E Display Name');
      const firstProfilePatch = primaryPage.waitForResponse(
        (response) =>
          response.url().endsWith('/api/v1/me') && response.request().method() === 'PATCH',
      );
      await primaryPage.getByRole('button', { name: '保存资料' }).click();
      expect((await firstProfilePatch).ok()).toBe(true);

      await displayNameInput.clear();
      const clearProfilePatch = primaryPage.waitForResponse(
        (response) =>
          response.url().endsWith('/api/v1/me') && response.request().method() === 'PATCH',
      );
      await primaryPage.getByRole('button', { name: '保存资料' }).click();
      expect((await clearProfilePatch).ok()).toBe(true);
      const clearedProfile = await jsonResponse<{ displayName: string | null }>(
        await primaryPage.request.get(absoluteUrl('/api/v1/me')),
      );
      expect(clearedProfile.displayName).toBeNull();

      const avatarUpload = primaryPage.waitForResponse(
        (response) =>
          response.url().endsWith('/api/v1/me/avatar') && response.request().method() === 'POST',
      );
      await primaryPage.locator('input[type="file"]').setInputFiles({
        name: 'e2e-avatar.png',
        mimeType: 'image/png',
        buffer: Buffer.from(
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9ZQmcAAAAASUVORK5CYII=',
          'base64',
        ),
      });
      expect((await avatarUpload).ok()).toBe(true);
      const profileWithAvatar = await jsonResponse<{ avatarKey: string | null }>(
        await primaryPage.request.get(absoluteUrl('/api/v1/me')),
      );
      expect(profileWithAvatar.avatarKey).not.toBeNull();

      const avatarDelete = primaryPage.waitForResponse(
        (response) =>
          response.url().includes('/api/v1/me/avatar?') && response.request().method() === 'DELETE',
      );
      await primaryPage.getByRole('button', { name: '删除头像' }).click();
      expect((await avatarDelete).ok()).toBe(true);
      const profileWithoutAvatar = await jsonResponse<{ avatarKey: string | null }>(
        await primaryPage.request.get(absoluteUrl('/api/v1/me')),
      );
      expect(profileWithoutAvatar.avatarKey).toBeNull();

      await primaryPage.getByRole('tab', { name: '基金持仓' }).click();
      await expect(primaryPage.getByText('Default Internal Fund')).toBeVisible();
      await expect(primaryPage.getByText('E2E-FUND · USDT')).toBeVisible();
      await expect(primaryPage.getByText('1,260 USDT')).toBeVisible();
      await expect(primaryPage.getByText('+260 USDT')).toBeVisible();
      await expect(primaryPage.getByText('26%')).toBeVisible();

      await primaryPage.goto(absoluteUrl('/risk/users'));
      await expect(primaryPage).toHaveURL(/\/exception\/403$/);

      await primaryPage.goto(absoluteUrl('/account/index'));
      await primaryPage.getByRole('button', { name: '修改密码' }).click();
      const passwordDialog = primaryPage.getByRole('dialog', { name: '修改密码' });
      await passwordDialog.getByLabel('当前密码').fill(memberPassword);
      await passwordDialog.getByLabel('新密码', { exact: true }).fill(memberNewPassword);
      await passwordDialog.getByLabel('确认新密码').fill(memberNewPassword);
      const passwordResponse = primaryPage.waitForResponse(
        (response) =>
          response.url().endsWith('/api/v1/me/password') && response.request().method() === 'POST',
      );
      await passwordDialog.getByRole('button', { name: /确.*定/ }).click();
      expect((await passwordResponse).ok()).toBe(true);
      await expect(primaryPage).toHaveURL(/\/login$/);

      await secondaryPage.goto(absoluteUrl('/account/index'));
      await expect(secondaryPage).toHaveURL(/\/login\?redirect=/);

      await loginWithUi(primaryPage, memberUsername, memberNewPassword);
      await primaryPage.goto(absoluteUrl('/account/index'));
      await expect(primaryPage.getByText(memberUsername, { exact: true })).toBeVisible();
    } finally {
      await primaryContext.close();
      await secondaryContext.close();
    }
  });
});
