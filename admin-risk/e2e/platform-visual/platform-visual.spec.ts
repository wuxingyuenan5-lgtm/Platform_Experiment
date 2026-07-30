import fs from 'node:fs';
import path from 'node:path';

import { expect, test, type Browser, type Page } from '@playwright/test';

import { mockPlatformVisualRoutes } from './platformVisualFixtures';

const FRONTEND_ORIGIN = 'http://127.0.0.1:4373';
const EVIDENCE_ROOT = path.resolve(process.cwd(), 'test-results/platform-visual/evidence');

const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'laptop-1024', width: 1024, height: 768 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
] as const;

type AuthenticatedRole = 'employee' | 'ceo' | 'member';

interface VisualPage {
  key: string;
  route: string;
  marker: string;
  markerKind?: 'heading' | 'text';
  evidenceSource: string;
}

const EMPLOYEE_PAGES: readonly VisualPage[] = [
  {
    key: 'home',
    route: '/home/index',
    marker: '全球变量',
    markerKind: 'heading',
    evidenceSource: 'static product content',
  },
  {
    key: 'research-macro',
    route: '/hedge-board/macro',
    marker: '市场预期与事件概率',
    markerKind: 'heading',
    evidenceSource: 'deterministic research fixture; not a real Provider acceptance result',
  },
  {
    key: 'research-a-share',
    route: '/hedge-board/a-share',
    marker: '大盘表现',
    markerKind: 'heading',
    evidenceSource: 'deterministic A-share/Shenwan fixture; not a real Provider acceptance result',
  },
  {
    key: 'strategy-funding',
    route: '/strategy/platform?desk=funding',
    marker: '资费',
    evidenceSource: 'isolated Platform API and fake Runtime; Live Write disabled',
  },
  {
    key: 'strategy-cross-spread',
    route: '/strategy/platform?desk=crossSpread',
    marker: '跨所价差',
    evidenceSource: 'isolated Platform API and fake Runtime; Live Write disabled',
  },
  {
    key: 'strategy-management',
    route: '/strategy/management',
    marker: '策略管理',
    evidenceSource: 'local strategy fixtures plus isolated Platform API; Live Write disabled',
  },
  {
    key: 'risk-detail',
    route: '/risk/detail',
    marker: '风控总览',
    evidenceSource: 'deterministic operations fixture and isolated browser role',
  },
  {
    key: 'operations-monitor',
    route: '/monitor/index',
    marker: '系统监控',
    evidenceSource: 'deterministic health fixture',
  },
  {
    key: 'finance-overview',
    route: '/finance/index',
    marker: '财务概览',
    evidenceSource: 'deterministic operational projection fixture; not formal accounting evidence',
  },
  {
    key: 'data-overview',
    route: '/data/index',
    marker: '数据管理',
    evidenceSource: 'deterministic account and NAV chart fixture',
  },
  {
    key: 'reports',
    route: '/reports/index',
    marker: '报表',
    evidenceSource: 'deterministic risk and notification fixture',
  },
];

const CEO_PAGES: readonly VisualPage[] = [
  {
    key: 'user-management',
    route: '/risk/users',
    marker: '用户管理',
    evidenceSource: 'isolated seeded CEO browser Session; no API-Key or Live Write authority',
  },
];

const MEMBER_PAGES: readonly VisualPage[] = [
  {
    key: 'member-account',
    route: '/account/index',
    marker: '个人账号',
    evidenceSource: 'isolated seeded member holding/NAV read model using Decimal strings',
  },
];

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for the full-platform visual suite`);
  return value;
}

function absoluteUrl(route: string): string {
  return `${FRONTEND_ORIGIN}/#${route}`;
}

function usernameFor(role: AuthenticatedRole): string {
  return {
    employee: 'e2e_employee_1',
    ceo: 'e2e_ceo',
    member: 'e2e_vip_1',
  }[role];
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

async function preparePage(page: Page): Promise<void> {
  await page.route(/^https?:\/\/(?!127\.0\.0\.1(?::\d+)?|localhost(?::\d+)?)/, (route) =>
    route.abort(),
  );
  await mockPlatformVisualRoutes(page);
}

async function openAuthenticatedPage(
  browser: Browser,
  role: AuthenticatedRole,
  viewport: { width: number; height: number },
): Promise<{ page: Page; close: () => Promise<void> }> {
  const context = await browser.newContext({
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    colorScheme: 'light',
    reducedMotion: 'reduce',
    viewport,
  });
  const page = await context.newPage();
  await preparePage(page);
  await loginWithUi(page, usernameFor(role), requiredEnvironment('E2E_SHARED_PASSWORD'));
  return { page, close: () => context.close() };
}

async function waitForMarker(page: Page, definition: VisualPage): Promise<void> {
  const marker =
    definition.markerKind === 'heading'
      ? page.getByRole('heading', { name: definition.marker }).first()
      : page.getByText(definition.marker, { exact: false }).first();
  await expect(marker).toBeVisible({ timeout: 30_000 });
}

async function stabilizePage(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        caret-color: transparent !important;
      }
      .ant-message, .ant-notification { pointer-events: none !important; }
    `,
  });
  await page.keyboard.press('Escape');
  const mask = page.locator('.ant-drawer-mask:visible, .ant-modal-mask:visible').first();
  if (await mask.isVisible().catch(() => false)) await mask.click({ force: true });
  await page
    .locator('.ant-spin-spinning')
    .first()
    .waitFor({ state: 'hidden', timeout: 12_000 })
    .catch(() => undefined);
  await page.waitForTimeout(900);
  await page.evaluate(async () => {
    if ('fonts' in document) await document.fonts.ready;
    window.scrollTo(0, 0);
  });
}

async function capturePage(
  page: Page,
  role: AuthenticatedRole | 'anonymous',
  viewport: (typeof VIEWPORTS)[number],
  definition: VisualPage,
): Promise<void> {
  await page.goto(absoluteUrl(definition.route), { waitUntil: 'domcontentloaded' });
  await waitForMarker(page, definition);
  await stabilizePage(page);

  const layout = await page.evaluate(() => ({
    documentClientWidth: document.documentElement.clientWidth,
    documentScrollWidth: document.documentElement.scrollWidth,
    bodyClientWidth: document.body.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
  }));
  expect(layout.documentScrollWidth).toBeLessThanOrEqual(layout.documentClientWidth + 1);
  expect(layout.bodyScrollWidth).toBeLessThanOrEqual(layout.bodyClientWidth + 1);

  const directory = path.join(EVIDENCE_ROOT, viewport.name, role);
  fs.mkdirSync(directory, { recursive: true });
  const screenshotName = `${definition.key}.png`;
  const screenshotPath = path.join(directory, screenshotName);
  await page.screenshot({ path: screenshotPath, animations: 'disabled' });
  fs.writeFileSync(
    path.join(directory, `${definition.key}.json`),
    JSON.stringify(
      {
        key: definition.key,
        route: definition.route,
        role,
        viewport,
        marker: definition.marker,
        evidenceSource: definition.evidenceSource,
        evidenceClassification:
          'deterministic visual baseline; not production or real Provider acceptance',
        liveWrite: false,
        screenshot: screenshotName,
        layout,
        capturedAt: new Date().toISOString(),
        gitSha: process.env.GITHUB_SHA || null,
      },
      null,
      2,
    ),
    'utf8',
  );
}

for (const viewport of VIEWPORTS) {
  test(`captures public login at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await preparePage(page);
    await capturePage(page, 'anonymous', viewport, {
      key: 'login',
      route: '/login',
      marker: '欢迎登录',
      evidenceSource: 'public authentication UI; no Session',
    });
  });

  test(`captures employee platform surfaces at ${viewport.name}`, async ({ browser }) => {
    const session = await openAuthenticatedPage(browser, 'employee', viewport);
    try {
      for (const definition of EMPLOYEE_PAGES) {
        await test.step(definition.key, () =>
          capturePage(session.page, 'employee', viewport, definition),
        );
      }
    } finally {
      await session.close();
    }
  });

  test(`captures CEO administration surface at ${viewport.name}`, async ({ browser }) => {
    const session = await openAuthenticatedPage(browser, 'ceo', viewport);
    try {
      for (const definition of CEO_PAGES) {
        await capturePage(session.page, 'ceo', viewport, definition);
      }
    } finally {
      await session.close();
    }
  });

  test(`captures member account surface at ${viewport.name}`, async ({ browser }) => {
    const session = await openAuthenticatedPage(browser, 'member', viewport);
    try {
      for (const definition of MEMBER_PAGES) {
        await capturePage(session.page, 'member', viewport, definition);
      }
    } finally {
      await session.close();
    }
  });
}
