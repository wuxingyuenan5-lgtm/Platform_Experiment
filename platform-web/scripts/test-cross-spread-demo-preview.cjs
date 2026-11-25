const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('@playwright/test');

async function main() {
  const browser = await chromium.launch({ headless: true });
  const output = path.resolve(__dirname, '../../.codex/previews/cross-spread-market-demo');
  fs.mkdirSync(output, { recursive: true });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1100 },
      reducedMotion: 'reduce',
    });
    const errors = [],
      requests = [];
    page.on('pageerror', (error) => errors.push(error.message));
    page.on('request', (r) => {
      if (/\/api\/|\/login|\/me(?:\?|$)/.test(r.url())) requests.push(r.url());
    });
    await page.goto('http://127.0.0.1:4375/cross-spread-demo.html');
    const demo = page.getByTestId('cross-spread-market-demo');
    await demo.getByRole('heading', { name: '价差研究台 演示数据' }).waitFor();
    await demo.locator('.demo-chart').first().scrollIntoViewIfNeeded();
    await demo.locator('.demo-chart svg').first().waitFor();
    await page.waitForFunction(() =>
      document.querySelector('.demo-chart')?.textContent.includes('空价差成本边界'),
    );
    await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
    await demo.getByRole('button', { name: 'CFD 休市', exact: true }).click();
    assert.equal(await demo.getByTestId('demo-total').innerText(), '— U');
    await demo.getByRole('button', { name: '短时偏离', exact: true }).click();
    await demo.getByRole('button', { name: '统计分析', exact: true }).click();
    const stats = demo.getByTestId('spread-statistics');
    await stats.getByRole('heading', { name: '分位与形态' }).waitFor();
    const count = Number(
      (await stats.getByTestId('stats-sample-count').innerText()).split('/')[0].trim(),
    );
    await demo.getByLabel('研究窗口').selectOption('7');
    assert.ok(
      Number((await stats.getByTestId('stats-sample-count').innerText()).split('/')[0].trim()) <
        count,
    );
    await demo.getByLabel('研究窗口').selectOption('30');
    await stats.getByLabel('统计序列').selectOption('buy');
    await stats.getByLabel('统计单位').selectOption('bps');
    await stats.getByLabel('统计时段').selectOption('亚洲');
    await page.screenshot({ path: path.join(output, 'statistics.png'), fullPage: true });
    const downloadEvent = page.waitForEvent('download');
    await stats.getByRole('button', { name: '导出样本 CSV' }).click();
    const download = await downloadEvent;
    const csv = fs.readFileSync(await download.path(), 'utf8');
    assert.ok(csv.includes('合成演示'));
    assert.ok(csv.includes('买价差 A,bps'));
    await stats.getByRole('button', { name: '波动与稳定性' }).click();
    await stats.getByRole('heading', { name: '回归速度的粗略估计' }).waitFor();
    await stats.getByLabel('滚动统计窗口').selectOption('24');
    await stats.getByRole('status').waitFor();
    await stats.getByLabel('统计时段').selectOption('全部');
    await stats.locator('.statistics-empty').waitFor({ state: 'detached' });
    await page.screenshot({ path: path.join(output, 'stability.png'), fullPage: true });
    await stats.getByRole('button', { name: '时段结构' }).click();
    await stats.getByLabel('统计分组').selectOption('month');
    await stats.getByRole('button', { name: '周四 10点统计', exact: true }).click();
    assert.ok((await stats.locator('.cell-detail').innerText()).includes('周四 10:00'));
    await page.screenshot({ path: path.join(output, 'time-structure.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth + 1);
    await page.screenshot({ path: path.join(output, 'statistics-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1100 });
    await demo.getByRole('button', { name: '回归与时段', exact: true }).click();
    await demo.locator('.demo-chart').first().scrollIntoViewIfNeeded();
    await demo.locator('.demo-chart svg').first().waitFor();
    await demo.getByLabel('事件风险线').selectOption('1');
    await demo.getByLabel('事件最长观察').selectOption('24');
    await demo.getByRole('heading', { name: '期限与方向的条件表现' }).waitFor();
    await page.screenshot({ path: path.join(output, 'events.png'), fullPage: true });
    await demo.getByRole('button', { name: '兑现与持有', exact: true }).click();
    const execution = demo.getByTestId('execution-research');
    await execution.getByLabel('兑现研究数量').fill('20');
    assert.equal(await execution.getByTestId('depth-adjusted-net').innerText(), '—');
    await execution.getByLabel('兑现研究数量').fill('5');
    assert.notEqual(await execution.getByTestId('depth-adjusted-net').innerText(), '—');
    await execution.getByLabel('允许报价时差').selectOption('50');
    assert.equal(await execution.getByTestId('depth-adjusted-net').innerText(), '—');
    await execution.getByLabel('允许报价时差').selectOption('250');
    await execution.getByLabel('CFD 单边滑点预算').fill('');
    assert.equal(await execution.getByTestId('depth-adjusted-net').innerText(), '—');
    await execution.getByLabel('CFD 单边滑点预算').fill('0.15');
    await page.screenshot({ path: path.join(output, 'execution-research.png'), fullPage: true });
    await demo.getByRole('button', { name: '流动性收缩', exact: true }).click();
    assert.equal(await execution.getByTestId('depth-adjusted-net').innerText(), '—');
    await demo.getByRole('button', { name: '短时偏离', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth + 1);
    await page.setViewportSize({ width: 1440, height: 1100 });
    await demo.getByRole('button', { name: '来源与失效条件', exact: true }).click();
    await demo.locator('.demo-chart').scrollIntoViewIfNeeded();
    await demo.locator('.demo-chart svg').waitFor();
    await page.screenshot({ path: path.join(output, 'attribution.png'), fullPage: true });
    await demo.getByRole('button', { name: '价差与净空间', exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true });
    await page.waitForFunction(() => document.documentElement.scrollWidth <= innerWidth + 1);
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, []);
    console.log(
      `PASS: same-component standalone preview, charts, states, 390px layout; zero page errors or API requests. Screenshots: ${output}`,
    );
  } finally {
    await browser.close();
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
