const fs = require('fs');
const path = require('path');
const assert = require('assert');

const hedgeBoardPagePath = path.join(__dirname, '..', 'src', 'views', 'hedgeBoard', 'index.vue');
const marketTerminalPagePath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'components',
  'MarketTerminalPage.vue',
);
const hedgeBoardSubnavPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'components',
  'HedgeBoardSubnav.vue',
);
const hedgeResearchModulePath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'components',
  'HedgeResearchModule.vue',
);
const terminalDetailPanelPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'components',
  'TerminalDetailPanel.vue',
);
const marketDetailCatalogPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'nativeData',
  'marketDetailCatalog.ts',
);
const toolGroupSectionPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'tradingTools',
  'components',
  'ToolGroupSection.vue',
);
const tradingToolCatalogPath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'tradingTools',
  'data',
  'catalog.ts',
);
const tradingToolsPagePath = path.join(
  __dirname,
  '..',
  'src',
  'views',
  'hedgeBoard',
  'tradingTools',
  'index.vue',
);
const uiGuidelinesPath = path.join(__dirname, '..', 'docs', 'design', 'platform-ui-guidelines.md');

const hedgeBoardSource = fs.readFileSync(hedgeBoardPagePath, 'utf8');
const hedgeBoardSubnavSource = fs.readFileSync(hedgeBoardSubnavPath, 'utf8');
const hedgeResearchModuleSource = fs.readFileSync(hedgeResearchModulePath, 'utf8');
const terminalDetailPanelSource = fs.readFileSync(terminalDetailPanelPath, 'utf8');
const marketDetailCatalogSource = fs.readFileSync(marketDetailCatalogPath, 'utf8');
const tradingToolCatalogSource = fs.readFileSync(tradingToolCatalogPath, 'utf8');
const tradingToolsPageSource = fs.readFileSync(tradingToolsPagePath, 'utf8');
const uiGuidelinesSource = fs.readFileSync(uiGuidelinesPath, 'utf8');

assert(fs.existsSync(marketTerminalPagePath), 'Expected MarketTerminalPage component to exist.');
assert(fs.existsSync(hedgeBoardSubnavPath), 'Expected HedgeBoardSubnav component to exist.');
assert(fs.existsSync(hedgeResearchModulePath), 'Expected HedgeResearchModule component to exist.');
assert(fs.existsSync(terminalDetailPanelPath), 'Expected TerminalDetailPanel component to exist.');
assert(fs.existsSync(marketDetailCatalogPath), 'Expected market detail catalog to exist.');
assert(fs.existsSync(toolGroupSectionPath), 'Expected ToolGroupSection component to exist.');

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
  !hedgeBoardSource.includes('<nav class="module-subnav"') &&
    !hedgeBoardSource.includes('.module-subnav'),
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
    /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+auto\s+minmax\(0,\s*1fr\);/m.test(hedgeResearchModuleSource) &&
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
  hedgeBoardSource.split(/\r?\n/).length <= 4200,
  'Hedge board page exceeded the current lightweight budget; split a component before adding more inline code.',
);
assert(
  uiGuidelinesSource.includes('图表型 widget 标题默认使用 `17px`') &&
    uiGuidelinesSource.includes('图表型 widget 标题 | `17px`') &&
    uiGuidelinesSource.includes('不得叠加在图表绘图区内'),
  'UI guidelines must document 17px centered chart-widget titles and header-only source links.',
);

console.log('Hedge board layout checks passed.');
