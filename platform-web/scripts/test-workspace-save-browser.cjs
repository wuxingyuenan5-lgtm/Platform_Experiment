const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { parse, compileScript } = require('@vue/compiler-sfc');
const ts = require('typescript');
const { chromium } = require('@playwright/test');

async function main() {
  const file = path.join(__dirname, '../src/views/dashboard/workspace/PersonalWorkspace.vue');
  const compiled = compileScript(parse(fs.readFileSync(file, 'utf8')).descriptor, {
    id: 'workspace-browser-test', inlineTemplate: true,
  });
  const code = ts.transpileModule(compiled.content, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const vueCode = fs.readFileSync(require.resolve('vue/dist/vue.global.prod.js'));
  const html = `<div id="app"></div><script src="/vue.js"></script><script>
    window.requests = [];
    const initial = {rowVersion: 0, items: [
      {id:'a',type:'chart',title:'A',seriesA:'x',width:1},
      {id:'b',type:'chart',title:'B',seriesA:'y',width:1}
    ]};
    const dependencies = {
      vue: Vue,
      '@/store/modules/user': {useUserStore: () => ({getUserInfo:{userId:'test'},getAuthentication:{permissions:['research.read']}})},
      '@/access/userAccess': {hasPermission: () => true},
      '@/api/workspace': {
        loadWorkspace: async () => JSON.parse(localStorage.getItem('layout') || JSON.stringify(initial)),
        loadSeriesCatalog: async () => [],
        saveWorkspace: (kind, items, rowVersion) => new Promise(resolve => {
          window.requests.push({items:structuredClone(items),rowVersion,resolve});
        })
      },
      './moduleCatalog': {moduleCatalog: () => []},
      'vue-router': {useRouter: () => ({resolve: () => ({matched:[]})})},
      '@/access/routeAccess': {canAccessMatchedRoute: () => true},
    };
    const mod = {exports:{}};
    new Function('require','module','exports',${JSON.stringify(code)})((name) => {
      if (name in dependencies) return dependencies[name];
      if (name.endsWith('.vue')) return {render(){return null}};
      throw new Error('Missing dependency: '+name);
    },mod,mod.exports);
    window.ack = (index) => {
      const r = window.requests[index];
      const response = {items:r.items,rowVersion:r.rowVersion+1};
      localStorage.setItem('layout',JSON.stringify(response));
      r.resolve(response);
    };
    Vue.createApp(mod.exports.default).mount('#app');
  </script>`;
  const server = http.createServer((request, response) => {
    response.setHeader('Content-Type', request.url === '/vue.js' ? 'text/javascript' : 'text/html; charset=utf-8');
    response.end(request.url === '/vue.js' ? vueCode : html);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    await page.getByRole('heading', {name:'A',exact:true}).waitFor();
    await page.getByRole('button', {name:'保存布局',exact:true}).click();
    await page.getByRole('button', {name:'移除',exact:true}).first().click();
    await page.evaluate(() => window.ack(0));
    await page.getByRole('status').filter({hasText:'后续修改尚未保存'}).waitFor();
    assert.equal(await page.getByRole('heading', {name:'A',exact:true}).count(), 0);
    assert.equal(await page.getByRole('heading', {name:'B',exact:true}).count(), 1);
    await page.getByRole('button', {name:'保存布局',exact:true}).click();
    assert.equal(await page.evaluate(() => window.requests[1].rowVersion), 1);
    await page.evaluate(() => window.ack(1));
    await page.getByRole('status').filter({hasText:'已保存到当前账号'}).waitFor();
    await page.reload();
    await page.getByRole('heading', {name:'B',exact:true}).waitFor();
    assert.equal(await page.getByRole('heading', {name:'A',exact:true}).count(), 0);
    assert.deepEqual(errors, []);
    console.log('PASS: real workspace DOM preserves edits during delayed save and reloads next save');
  } finally {
    if (browser) await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
