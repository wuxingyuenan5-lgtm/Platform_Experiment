const path = require('path');

const { chromium } = require(path.join(process.cwd(), 'node_modules', '@playwright', 'test'));

const origin = 'http://127.0.0.1:4373';

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for authenticated E2E checks`);
  return value;
}

async function login(page) {
  await page.goto(`${origin}/#/login`, { waitUntil: 'domcontentloaded' });
  await page.getByPlaceholder(/账号|账户|请输入账号/).fill(requiredEnv('E2E_CEO_USERNAME'));
  await page.getByPlaceholder(/密码|请输入密码/).fill(requiredEnv('E2E_CEO_PASSWORD'));
  const response = page.waitForResponse((item) => item.url().endsWith('/api/v1/auth/login'));
  await page.getByRole('button', { name: /登录/ }).click();
  if (!(await response).ok()) throw new Error('login failed');
  await page.waitForURL((url) => !url.hash.includes('/login'), { timeout: 20_000 });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 }, locale: 'zh-CN' });
  await login(page);
  await page.goto(`${origin}/#/news-calendar/wealth`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('.wealth-page');
  for (const lock of ['short', 'mid', 'long']) {
    await page.locator('select').nth(2).selectOption(lock);
    await page.waitForTimeout(200);
    const count = await page.locator('.wealth-row').count();
    if (count < 1) throw new Error(`lock filter ${lock} returned no rows`);
    const visibleLockTexts = await page
      .locator('.wealth-row')
      .evaluateAll((rows) => rows.map((row) => row.textContent || ''));
    const expected = lock === 'short' ? '7 天以内' : lock === 'mid' ? '30 天以内' : '长期';
    if (!visibleLockTexts.every((text) => text.includes(expected))) {
      throw new Error(
        `lock filter ${lock} included non-matching rows: ${visibleLockTexts.join(' | ')}`,
      );
    }
  }
  await page.locator('input[placeholder*="搜索"]').fill('NO_MATCH_TERM');
  await page.waitForTimeout(200);
  if (!(await page.locator('.wealth-empty').isVisible())) {
    throw new Error('wealth empty state is not visible');
  }
  await browser.close();
  console.log('news wealth lock filters passed: short, mid, long, empty state');
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
