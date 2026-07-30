const fs = require('fs');
const path = require('path');
const assert = require('assert');

const viewRoot = path.join(__dirname, '..', 'src', 'views', 'hedgeBoard');
const hedgeBoardPagePath = path.join(viewRoot, 'index.vue');
const marketTerminalPagePath = path.join(viewRoot, 'components', 'MarketTerminalPage.vue');
const hedgeBoardSubnavPath = path.join(viewRoot, 'components', 'HedgeBoardSubnav.vue');
const hedgeResearchModulePath = path.join(viewRoot, 'components', 'HedgeResearchModule.vue');
const terminalDetailPanelPath = path.join(viewRoot, 'components', 'TerminalDetailPanel.vue');
const marketDetailCatalogPath = path.join(viewRoot, 'nativeData', 'marketDetailCatalog.ts');
const toolGroupSectionPath = path.join(viewRoot, 'tradingTools', 'components', 'ToolGroupSection.vue');
const tradingToolCatalogPath = path.join(viewRoot, 'tradingTools', 'data', 'catalog.ts');
const tradingToolsPagePath = path.join(viewRoot, 'tradingTools', 'index.vue');
const aSharePagePath = path.join(viewRoot, 'aShare', 'index.vue');
const aShareResearchComposablePath = path.join(viewRoot, 'aShare', 'useAShareResearch.ts');
const aShareWatchlistPath = path.join(
  viewRoot,
  'aShare',
  'components',
  'AShareWatchlistSection.vue',
);
const aShareMarketDetailPath = path.join(
  viewRoot,
  'aShare',
  'components',
  'AShareMarketDetailSection.vue',
);
const shenwanSectionPath = path.join(
  viewRoot,
  'aShare',
  'components',
  'ShenwanIndustrySection.vue',
);
const stockSnapshotPath = path.join(
  viewRoot,
  'aShare',
  'components',
  'StockSnapshotSection.vue',
);
const macroExpectationPath = path.join(viewRoot, 'macro', 'MacroExpectationPanel.vue');
const routePath = path.join(__dirname, '..', 'src', 'router', 'routes', 'modules', 'hedge.ts');
const uiGuidelinesPath = path.join(__dirname, '..', 'docs', 'design', 'platform-ui-guidelines.md');

const hedgeBoardSource = fs.readFileSync(hedgeBoardPagePath, 'utf8');
const hedgeBoardSubnavSource = fs.readFileSync(hedgeBoardSubnavPath, 'utf8');
const hedgeResearchModuleSource = fs.readFileSync(hedgeResearchModulePath, 'utf8');
const terminalDetailPanelSource = fs.readFileSync(terminalDetailPanelPath, 'utf8');
const marketDetailCatalogSource = fs.readFileSync(marketDetailCatalogPath, 'utf8');
const tradingToolCatalogSource = fs.readFileSync(tradingToolCatalogPath, 'utf8');
const tradingToolsPageSource = fs.readFileSync(tradingToolsPagePath, 'utf8');
const aSharePageSource = fs.readFileSync(aSharePagePath, 'utf8');
const aShareResearchComposableSource = fs.readFileSync(aShareResearchComposablePath, 'utf8');
const aShareWatchlistSource = fs.readFileSync(aShareWatchlistPath, 'utf8');
const aShareMarketDetailSource = fs.readFileSync(aShareMarketDetailPath, 'utf8');
const shenwanSectionSource = fs.readFileSync(shenwanSectionPath, 'utf8');
const stockSnapshotSource = fs.readFileSync(stockSnapshotPath, 'utf8');
const macroExpectationSource = fs.readFileSync(macroExpectationPath, 'utf8');
const routeSource = fs.readFileSync(routePath, 'utf8');
const uiGuidelinesSource = fs.readFileSync(uiGuidelinesPath, 'utf8');

assert(fs.existsSync(marketTerminalPagePath), 'Expected MarketTerminalPage component to exist.');
assert(fs.existsSync(hedgeBoardSubnavPath), 'Expected HedgeBoardSubnav component to exist.');
assert(fs.existsSync(hedgeResearchModulePath), 'Expected HedgeResearchModule component to exist.');
assert(fs.existsSync(terminalDetailPanelPath), 'Expected TerminalDetailPanel component to exist.');
assert(fs.existsSync(marketDetailCatalogPath), 'Expected market detail catalog to exist.');
assert(fs.existsSync(toolGroupSectionPath), 'Expected ToolGroupSection component to exist.');
assert(fs.existsSync(aSharePagePath), 'Expected dedicated A-share research page to exist.');
assert(fs.existsSync(macroExpectationPath), 'Expected macro expectation panel to exist.');

assert(
  hedgeBoardSource.includes('<MarketTerminalPage') && hedgeBoardSource.includes('MarketTerminalPage from'),
  'Hedge board terminal categories must use MarketTerminalPage.',
);
assert(
  hedgeBoardSource.includes('<HedgeResearchModule') && hedgeBoardSource.includes('HedgeResearchModule from'),
  'Hedge board page must use HedgeResearchModule for research section rendering.',
);
assert(
  hedgeBoardSource.includes('<ToolGroupSection') && hedgeBoardSource.includes('ToolGroupSection from'),
  'Hedge board trading tools must use ToolGroupSection.',
);
assert(
  hedgeBoardSource.includes('TerminalDetailPanel') && hedgeBoardSource.includes('TerminalDetailPanel from'),
  'Hedge board local detail widgets must use TerminalDetailPanel.',
);
assert(
  !hedgeBoardSource.includes("from './nativeData/dashboard'") &&
    !hedgeBoardSource.includes('tradingTools/data/marketTools') &&
    !hedgeBoardSource.includes('tradingTools/data/cryptoTools'),
  'Hedge board must not re-import legacy dashboard or individual trading-tool data files.',
);
assert(
  !hedgeBoardSource.includes('<nav class="module-subnav"') && !hedgeBoardSource.includes('.module-subnav'),
  'Hedge board page must not inline research subnav markup or styles.',
);
assert(
  !hedgeBoardSource.includes('class="research-module"') &&
    !hedgeBoardSource.includes('class="chart-section"') &&
    !hedgeBoardSource.includes('class="widget-card"'),
  'Hedge board page must not inline research module, chart section, or widget card markup.',
);
assert(
  hedgeBoardSubnavSource.includes('module-subnav') && hedgeBoardSubnavSource.includes('defineEmits'),
  'HedgeBoardSubnav must own research subnav rendering and jump event.',
);
assert(
  /\.module-subnav__title-row strong\s*\{[\s\S]*?color:\s*#111827;[\s\S]*?font-size:\s*14px;[\s\S]*?\}/m.test(
    hedgeBoardSubnavSource,
  ) &&
    /\.module-subnav__index\s*\{[\s\S]*?color:\s*#111827;[\s\S]*?font-size:\s*14px;[\s\S]*?\}/m.test(
      hedgeBoardSubnavSource,
    ),
  'HedgeBoardSubnav must keep index and title the same black 14px treatment.',
);
assert(
  hedgeResearchModuleSource.includes('HedgeBoardSubnav') &&
    hedgeResearchModuleSource.includes('widget-card') &&
    hedgeResearchModuleSource.includes('chart-section'),
  'HedgeResearchModule must own research module section and widget rendering.',
);
assert(
  hedgeResearchModuleSource.includes('widget-card--local-chart') &&
    /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto\s+minmax\(0,\s*1fr\);/m.test(
      hedgeResearchModuleSource,
    ) &&
    /grid-column:\s*2;[\s\S]*?justify-self:\s*center;/m.test(hedgeResearchModuleSource) &&
    /grid-column:\s*3;[\s\S]*?justify-self:\s*end;/m.test(hedgeResearchModuleSource) &&
    /\.widget-card--local-chart\s+\.widget-card__title-row h5\s*\{[\s\S]*?font-size:\s*17px;/m.test(
      hedgeResearchModuleSource,
    ),
  'Local chart widget headers must center 17px titles and keep source links in the top-right header action area.',
);
assert(
  !terminalDetailPanelSource.includes('<h3>{{ title }}</h3>') &&
    !terminalDetailPanelSource.includes('.market-terminal__panel-head h3'),
  'TerminalDetailPanel must not render a repeated market-detail title inside widgets.',
);
assert(
  marketDetailCatalogSource.includes("name: '中证 2000'") &&
    marketDetailCatalogSource.includes("label: '板块'") &&
    !marketDetailCatalogSource.includes("label: '板块与主题'"),
  'A-share market detail must preserve CSI 2000 and use the unified board label.',
);
assert(
  !hedgeBoardSource.includes('chart-shell__link-overlay') &&
    !hedgeBoardSource.includes('etf-weekly-panel__link') &&
    hedgeBoardSource.includes("'etf-weekly-flows': ETF_REFERENCE_URL") &&
    hedgeBoardSource.includes("'etf-ytd-summary': ETF_REFERENCE_URL"),
  'ETF source links must be provided through the widget header, not overlaid inside chart shells.',
);
assert(
  tradingToolCatalogSource.includes("await import('./marketTools')") &&
    !tradingToolCatalogSource.includes('tradingToolCategoryMap,'),
  'Trading tool catalog must lazy-load marketTools instead of statically importing generated data.',
);
assert(
  !tradingToolsPageSource.includes('tradingToolCategoryMap') &&
    tradingToolsPageSource.includes('loadTradingToolCategory'),
  'Trading tools page must load categories through the lazy catalog API.',
);

assert(
  routeSource.includes("import('@/views/hedgeBoard/aShare/index.vue')") &&
    routeSource.includes("import('@/views/hedgeBoard/macro/index.vue')"),
  'A-share and macro routes must use the upgraded research pages.',
);
assert(
  aSharePageSource.includes('<AShareBreadthSection') &&
    aSharePageSource.includes('<AShareMarketDetailSection') &&
    aSharePageSource.includes('<ShenwanIndustrySection') &&
    aSharePageSource.includes('<ShortTermEmotionSection') &&
    aSharePageSource.includes('<StockSnapshotSection'),
  'A-share page must orchestrate each natural research boundary through a child component.',
);
const requiredAShareColumns = [
  '名称 / 代码',
  '30日走势',
  '收盘价',
  '成交额',
  '20日波动率',
  '1D',
  'YTD',
  'QTD',
  '1周',
  '1月',
  '1年',
  '52周高',
  '1H',
  '日线',
  '3日线',
  '周线',
];
requiredAShareColumns.forEach((column) => {
  assert(aShareMarketDetailSource.includes(`>${column}<`), `Missing A-share detail column: ${column}`);
});
assert(!aShareMarketDetailSource.includes('>4H<'), 'A-share market detail must not display a 4H column.');
assert(
  shenwanSectionSource.includes('申万二级成交额 Top 10') &&
    shenwanSectionSource.includes('全部申万二级行业') &&
    shenwanSectionSource.includes('个股成交额阈值统计') &&
    !shenwanSectionSource.includes('成分股数') &&
    !shenwanSectionSource.includes('百亿股数') &&
    !shenwanSectionSource.includes('百亿股占比'),
  'Shenwan section must keep the clean Top-10 table and separate threshold statistics.',
);
assert(
  aShareResearchComposableSource.includes('export function normalizeStockCode') &&
    aShareResearchComposableSource.includes("if (stored === null) return [...DEFAULT_WATCHLIST]") &&
    !aShareResearchComposableSource.includes('!Array.isArray(payload) || !payload.length') &&
    aShareResearchComposableSource.includes('const groupIndexes = watchlist.value.reduce<number[]>'),
  'A-share watchlists must preserve stored empty arrays, normalize stock codes and reorder within groups.',
);
assert(
  aShareWatchlistSource.includes('空列表会被正常保留') &&
    aShareWatchlistSource.includes('已在自选股中') &&
    aShareWatchlistSource.includes(':disabled="itemIndex === 0"') &&
    aShareWatchlistSource.includes(':disabled="itemIndex === group.items.length - 1"'),
  'A-share watchlist UI must expose empty persistence, duplicate feedback and bounded move controls.',
);
assert(
  shenwanSectionSource.includes("sortDirection = ref<'asc' | 'desc'>('desc')") &&
    shenwanSectionSource.includes('没有匹配的申万二级行业') &&
    shenwanSectionSource.includes('当前序号') &&
    shenwanSectionSource.includes('重置筛选'),
  'Shenwan complete-industry view must expose sort direction, current result order and empty-filter recovery.',
);
assert(
  aShareResearchComposableSource.includes('let dashboardRequestSequence = 0') &&
    aShareResearchComposableSource.includes('let activeStockCode =') &&
    aShareResearchComposableSource.includes('shanghaiDateStamp') &&
    aShareResearchComposableSource.includes("import { message } from 'ant-design-vue'") &&
    aShareResearchComposableSource.includes("import { copyText } from '@/utils/copyTextToClipboard'"),
  'A-share interactions must guard stale requests and use platform feedback/copy utilities with China-market dates.',
);
assert(
  stockSnapshotSource.includes('expanded[item.key] = false') &&
    stockSnapshotSource.includes("{ key: 'quoteValuation'") &&
    stockSnapshotSource.includes("{ key: 'investorQa'") &&
    !stockSnapshotSource.toLowerCase().includes('ai'),
  'Stock snapshot modules must reset collapsed and remain fixed objective-data flows without AI.',
);
assert(
  macroExpectationSource.includes('市场预期与事件概率') &&
    macroExpectationSource.includes('historyPoints') &&
    !macroExpectationSource.includes('买卖建议'),
  'Macro page must present probability curves without trading recommendations.',
);

assert(
  hedgeBoardSource.split(/\r?\n/).length <= 4200,
  'Hedge board page exceeded the current lightweight budget; split a component before adding more inline code.',
);
assert(
  aSharePageSource.split(/\r?\n/).length <= 360,
  'A-share orchestrator exceeded its lightweight budget; move behavior into a component or composable.',
);
assert(
  uiGuidelinesSource.includes('图表型 widget 标题默认使用 `17px`') &&
    uiGuidelinesSource.includes('图表型 widget 标题 | `17px`') &&
    uiGuidelinesSource.includes('不得叠加在图表绘图区内'),
  'UI guidelines must document 17px centered chart-widget titles and header-only source links.',
);

console.log('Hedge board layout checks passed.');
