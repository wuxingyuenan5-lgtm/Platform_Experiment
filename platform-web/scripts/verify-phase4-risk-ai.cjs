const fs = require('fs');
const path = require('path');

const { chromium } = require(path.join(process.cwd(), 'node_modules', '@playwright', 'test'));

const origin = 'http://127.0.0.1:4373';
const outDir = path.join(process.cwd(), 'test-results', 'phase4-restoration');
fs.mkdirSync(outDir, { recursive: true });

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

function assertContains(text, required, label) {
  for (const item of required) {
    if (!text.includes(item)) throw new Error(`${label} missing ${item}`);
  }
}

function assertNoEngineeringCopy(text, label) {
  const forbidden =
    /Provider|Owner|Sample|Non-actionable|Live Write|static_design|source|asOf|actionable|Prompt|Token|API|Runtime|模型名|数据接入|组件名|正式组件/;
  if (forbidden.test(text)) throw new Error(`${label} exposes engineering copy`);
}

function assertNoFakeExecutionCopy(text) {
  if (/已提交交易所|等待成交|执行成功|成交成功|成交确认|开仓完成|下单成功/.test(text)) {
    throw new Error('domestic overseas execution exposes false execution success copy');
  }
}

function pushPageError(errors, error) {
  if (error.message === 'canceled') return;
  errors.push(`pageerror:${error.message}`);
}

function json(route, payload) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  });
}

async function setupGlobalFixtures(page) {
  await page.route(/\/risk\/api\/v1\/risk-records\/(?:\?.*)?$/, (route) =>
    json(route, [
      {
        id: 1,
        title: 'global risk notice',
        content: 'fixture',
        status: 'resolved',
        severity: 'low',
      },
    ]),
  );
  await page.route(/\/notifications\/api\/v1\/messages\/(?:\?.*)?$/, (route) =>
    json(route, [
      {
        id: 1,
        title: 'global notification',
        content: 'fixture',
        status: 'read',
        read: true,
      },
    ]),
  );
}

async function checkNoOverflow(page, label) {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    return Math.max(0, doc.scrollWidth - doc.clientWidth);
  });
  if (overflow > 2) throw new Error(`${label} horizontal overflow ${overflow}px`);
}

async function checkDomesticExecution(browser, width, height, errors) {
  const page = await browser.newPage({ viewport: { width, height }, locale: 'zh-CN' });
  await setupGlobalFixtures(page);
  page.on('pageerror', (error) => pushPageError(errors, error));
  page.on('requestfailed', (request) => errors.push(`requestfailed:${request.url()}`));
  page.on('request', (request) => {
    if (request.url().includes('/undefined/')) errors.push(`undefined-request:${request.url()}`);
  });

  await login(page);
  await page.goto(`${origin}/#/strategy/platform?desk=domesticOverseas`, {
    waitUntil: 'domcontentloaded',
  });
  await page.locator('.section-switcher').getByRole('button', { name: '交易执行' }).click();
  await page.waitForSelector('[data-testid="domestic-overseas-execution-workspace"]');
  const workspace = page.locator('[data-testid="domestic-overseas-execution-workspace"]');
  let text = await workspace.innerText();
  assertContains(
    text,
    [
      '资产水平（CNY）',
      '仓位平衡',
      '74.58% VS 空 25.42%',
      '沪金',
      '伦敦金',
      '账户信息',
      'AUM',
      '杠杆',
      '可用资金率',
      '预付比率',
      '汇率',
    ],
    'domestic execution account area',
  );
  if ((await workspace.locator('.gauge-shell').count()) < 2)
    throw new Error('domestic execution account area does not render restored gauge shells');
  assertContains(text, ['提交复核', '待复核'], 'domestic review workflow');
  assertNoFakeExecutionCopy(text);
  await checkNoOverflow(page, `domestic execution ${width}x${height}`);

  await page.screenshot({
    path: path.join(outDir, `domestic-account-${width}x${height}.png`),
    fullPage: false,
  });

  await page.getByRole('button', { name: /^刷新$/ }).click();
  await page.waitForSelector('text=账户、汇率和两侧价格已刷新。', { timeout: 5000 });

  if (width === 1366) {
    await page.locator('label:has-text("数量") input').first().fill('2');
    await page.getByRole('button', { name: '策略开仓' }).click();
    await page.getByTestId('domestic-submit-review').click();
    await page.locator('.trade-modal__dialog').getByRole('button', { name: '提交复核' }).click();
    await page.waitForSelector('text=状态为待复核', { timeout: 5000 });
    text = await workspace.innerText();
    assertContains(text, ['待复核', '复核记录已生成'], 'domestic submitted review state');
    assertNoFakeExecutionCopy(text);
    await page.screenshot({
      path: path.join(outDir, 'domestic-review-submitted-1366x768.png'),
      fullPage: false,
    });
  }
  await page.close();
}

async function checkRiskDetail(browser, errors) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 }, locale: 'zh-CN' });
  await setupGlobalFixtures(page);
  page.on('pageerror', (error) => pushPageError(errors, error));
  page.on('requestfailed', (request) => errors.push(`requestfailed:${request.url()}`));
  page.on('request', (request) => {
    if (request.url().includes('/undefined/')) errors.push(`undefined-request:${request.url()}`);
  });

  await login(page);
  await page.goto(`${origin}/#/risk/detail`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="risk-detail-restored"]');
  await page.waitForTimeout(500);
  let text = await page.locator('[data-testid="risk-detail-restored"]').innerText();
  assertContains(
    text,
    [
      '风险总览',
      '风险维度',
      '风险限额',
      '资产结构快照',
      '异常事件与处理',
      '告警消息',
      '审计日志',
      '账户',
      '策略',
      '持仓',
      '品种',
    ],
    'risk detail',
  );
  assertNoEngineeringCopy(text, 'risk detail');
  await checkNoOverflow(page, 'risk detail');
  await page.screenshot({ path: path.join(outDir, 'risk-detail-1366x768.png'), fullPage: false });

  await page.getByRole('button', { name: '策略' }).click();
  text = await page.locator('[data-testid="risk-detail-restored"]').innerText();
  assertContains(text, ['海内外价差'], 'risk dimension tab');
  await page.getByPlaceholder('查询事件、策略或品种').fill('汇率');
  assertContains(
    await page.locator('[data-testid="risk-detail-restored"]').innerText(),
    ['汇率腿偏移'],
    'risk filter',
  );
  await page.screenshot({
    path: path.join(outDir, 'risk-detail-full-1366x768.png'),
    fullPage: true,
  });
  await page.close();
}

async function checkFinancialAi(browser, errors) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 }, locale: 'zh-CN' });
  await setupGlobalFixtures(page);
  page.on('pageerror', (error) => pushPageError(errors, error));
  page.on('requestfailed', (request) => errors.push(`requestfailed:${request.url()}`));
  page.on('request', (request) => {
    if (request.url().includes('/undefined/')) errors.push(`undefined-request:${request.url()}`);
  });

  await login(page);
  await page.goto(`${origin}/#/financial-ai/index`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('[data-testid="financial-ai-restored"]');
  await page.waitForTimeout(800);
  let text = await page.locator('[data-testid="financial-ai-restored"]').innerText();
  assertContains(
    text,
    [
      '研究问题',
      '分析结果',
      '当前价格概览',
      '主要机构中期预测',
      '情景推演',
      '风险变量',
      '历史记录',
    ],
    'financial AI',
  );
  assertNoEngineeringCopy(text, 'financial AI');
  await checkNoOverflow(page, 'financial AI');
  await page.screenshot({ path: path.join(outDir, 'financial-ai-1366x768.png'), fullPage: false });

  await page.getByRole('button', { name: '情景推演' }).click();
  assertContains(
    await page.locator('[data-testid="financial-ai-restored"]').innerText(),
    ['强势情景', '基准情景', '弱势情景'],
    'financial AI scenarios',
  );
  await page.screenshot({
    path: path.join(outDir, 'financial-ai-result-1366x768.png'),
    fullPage: false,
  });

  await page.getByRole('button', { name: '提交复核' }).click();
  await page.waitForSelector('text=待复核请求', { timeout: 5000 });
  text = await page.locator('[data-testid="financial-ai-restored"]').innerText();
  if (/分析成功|生成成功|已完成分析|正式结果已生成/.test(text))
    throw new Error('financial AI fakes backend analysis success');
  await page.screenshot({
    path: path.join(outDir, 'financial-ai-full-1366x768.png'),
    fullPage: true,
  });
  await page.close();
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const errors = [];
  try {
    await checkDomesticExecution(browser, 1366, 768, errors);
    await checkDomesticExecution(browser, 1920, 1080, errors);
    await checkRiskDetail(browser, errors);
    await checkFinancialAi(browser, errors);
  } finally {
    await browser.close();
  }
  if (errors.length) throw new Error(errors.join(' | '));
  console.log(`phase4 risk/AI checks passed, screenshots=${outDir}`);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
