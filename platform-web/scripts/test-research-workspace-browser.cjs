const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const ts = require('typescript');
const { parse, compileScript, compileStyle } = require('@vue/compiler-sfc');
const { chromium } = require('@playwright/test');

const root = path.resolve(__dirname, '..');
const descriptor = parse(
  fs.readFileSync(path.join(root, 'src/views/hedgeBoard/components/ResearchWorkspace.vue'), 'utf8'),
).descriptor;
const transpile = (source) =>
  ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
const code = transpile(
  compileScript(descriptor, { id: 'workspace-check', inlineTemplate: true }).content,
);
const stateCode = transpile(
  fs.readFileSync(path.join(root, 'src/views/hedgeBoard/composables/researchWorkspace.ts'), 'utf8'),
);
const style = compileStyle({
  source: descriptor.styles[0].content,
  id: 'data-v-workspace-check',
  scoped: true,
}).code;
const vueCode = fs.readFileSync(require.resolve('vue/dist/vue.global.prod.js'));
const html = `<style>:root{--strategy-space-3:16px}body{margin:0}${style}
.board-workspace__viewport{height:500px}</style><div id="app"></div><script src="/vue.js"></script><script>
window.user = Vue.reactive({getUserInfo:{userId:'first'}});
const state = {exports:{}};
new Function('require','module','exports',${JSON.stringify(
  stateCode,
)})(() => Vue,state,state.exports);
const sidebar = {emits:['toggle'],setup(_,ctx){return()=>Vue.h('button',{onClick:()=>ctx.emit('toggle')},'toggle')}};
const component = {exports:{}};
new Function('require','module','exports',${JSON.stringify(code)})(name=>({
  vue:Vue,'@/store/modules/user':{useUserStore:()=>window.user},
  './ResearchSidebar.vue':{default:sidebar},'../composables/researchWorkspace':state.exports,
})[name],component,component.exports);
component.exports.default.__scopeId='data-v-workspace-check';
window.current=Vue.ref('one');window.workspace=Vue.ref();window.mounts=[];window.heights={};window.slow=new Set();
const Page={props:['page'],setup(props){
  const account=window.user.getUserInfo.userId;
  const value=state.exports.useResearchViewState('filter','');
  const tall=Vue.ref(!window.slow.has(props.page));
  window.heights[account+':'+props.page]=tall;
  Vue.onMounted(()=>window.mounts.push(account+':'+props.page));
  return()=>Vue.h('section',{style:{height:tall.value?'2200px':'180px'}},[
    Vue.h('input',{'aria-label':'filter','data-page':props.page,value:value.value,onInput:e=>value.value=e.target.value})
  ]);
}};
Vue.createApp({setup:()=>()=>Vue.h(component.exports.default,{
  ref:window.workspace,pages:['one','two','three','four','five'].map(key=>({key,label:key})),
  active:window.current.value,label:'research',contentKey:'cached-pages',
},{default:()=>Vue.h(Vue.KeepAlive,{max:3},{default:()=>Vue.h(Page,{key:window.current.value,page:window.current.value})})})}).mount('#app');
</script>`;

async function main() {
  const server = http.createServer((req, res) => {
    res.setHeader(
      'Content-Type',
      req.url === '/vue.js' ? 'text/javascript' : 'text/html; charset=utf-8',
    );
    res.end(req.url === '/vue.js' ? vueCode : html);
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', (error) => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}`);
    const viewport = page.locator('.board-workspace__viewport');
    const input = page.getByLabel('filter');
    const switchTo = async (name) => {
      await page.evaluate((value) => {
        window.current.value = value;
      }, name);
      await page.locator(`input[data-page="${name}"]`).waitFor();
    };
    await input.fill('alpha');
    await viewport.evaluate((el) => {
      el.scrollTop = 700;
      el.dispatchEvent(new Event('scroll'));
    });
    await switchTo('two');
    await input.fill('beta');
    await switchTo('one');
    assert.equal(await input.inputValue(), 'alpha');
    await page.waitForFunction(() => document.querySelector('main').scrollTop === 700);
    assert.equal(
      await page.evaluate(() => window.mounts.filter((x) => x === 'first:one').length),
      1,
    );
    const width = (await viewport.boundingBox()).width;
    await page.getByRole('button', { name: 'toggle', exact: true }).click();
    assert.equal((await viewport.boundingBox()).width - width, 74);

    await page.evaluate(() => window.slow.add('one'));
    for (const name of ['three', 'four', 'five', 'one']) await switchTo(name);
    assert.equal(await input.inputValue(), 'alpha', 'eviction preserves the shared filter state');
    assert.equal(
      await page.evaluate(() => window.mounts.filter((x) => x === 'first:one').length),
      2,
    );
    assert.equal(await viewport.evaluate((el) => el.scrollTop), 0);
    await page.evaluate(() => {
      window.heights['first:one'].value = true;
    });
    await page.waitForFunction(() => document.querySelector('main').scrollTop === 700);

    await page.evaluate(() => {
      window.user.getUserInfo.userId = 'second';
    });
    await page.waitForFunction(() => document.querySelector('input').value === '');
    assert.equal(await viewport.evaluate((el) => el.scrollTop), 0);
    await page.evaluate(() => {
      window.heights['second:one'].value = true;
    });
    assert.equal(await input.inputValue(), '', 'another account must not recover old filters');
    assert.deepEqual(errors, []);
    console.log(
      'PASS: shared workspace retains cached pages, restores delayed content, collapses, and isolates accounts',
    );
  } finally {
    await browser?.close();
    await new Promise((resolve) => server.close(resolve));
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
