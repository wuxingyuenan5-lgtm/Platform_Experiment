const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..');
const sourcePath = path.resolve(repoRoot, 'docs', 'trading-tools-bookmarks-review.md');
const targetPath = path.resolve(
  repoRoot,
  'src',
  'views',
  'hedgeBoard',
  'tradingTools',
  'data',
  'marketTools.ts',
);

const categoryIdMap = new Map([
  ['宏观工具', 'macro'],
  ['股市工具', 'equity'],
  ['加密工具', 'crypto'],
  ['金属工具', 'metal'],
  ['量化工具', 'quant'],
  ['综合工具', 'general'],
]);

const categoryDescriptionMap = {
  macro: '利率、流动性、债券、经济数据与跨区域宏观跟踪。',
  equity: '股票、ETF、财报、持仓与市场情绪研究工具。',
  crypto: '链上、衍生品、ETF 资金流与加密市场跟踪工具。',
  metal: '黄金、白银、铜与贵金属产业链跟踪工具。',
  quant: '量化研究、数据接口、策略开发与回测工具。',
  general: '跨品类通用研究、资讯、数据与辅助工具。',
};

function readMarkdown(filePath) {
  const buffer = fs.readFileSync(filePath);
  return new TextDecoder('utf-8').decode(buffer);
}

function normalizeLabel(value) {
  return value.replace(/[：:]+$/, '').trim();
}

function inferCategoryId(title) {
  const direct = categoryIdMap.get(title);
  if (direct) return direct;
  if (title.includes('宏观')) return 'macro';
  if (title.includes('股')) return 'equity';
  if (title.includes('加密')) return 'crypto';
  if (title.includes('金属') || title.includes('黄金') || title.includes('白银') || title.includes('铜')) {
    return 'metal';
  }
  if (title.includes('量化')) return 'quant';
  return 'general';
}

function sanitizeAscii(value) {
  return value
    .toLowerCase()
    .replace(/https?:\/\//g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function inferDomain(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return '';
  }
}

function parseMarkdown(markdown) {
  const lines = markdown.split(/\r?\n/);
  const categories = [];
  let currentCategory = null;
  let currentGroup = null;
  let pendingTool = null;

  function ensureFallbackGroup() {
    if (!currentCategory) return null;
    if (!currentGroup) {
      currentGroup = {
        id: `${currentCategory.id}-group-${currentCategory.groups.length + 1}`,
        title: '未分组',
        description: '来自 Markdown 中未显式归组的条目。',
        tools: [],
      };
      currentCategory.groups.push(currentGroup);
    }
    return currentGroup;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      pendingTool = null;
      continue;
    }

    const categoryMatch = line.match(/^##\s+(.+)$/);
    if (categoryMatch) {
      const title = normalizeLabel(categoryMatch[1]);
      if (title === '使用建议') {
        currentCategory = null;
        currentGroup = null;
        pendingTool = null;
        continue;
      }
      currentCategory = {
        id: inferCategoryId(title),
        title,
        description: categoryDescriptionMap[inferCategoryId(title)],
        groups: [],
      };
      categories.push(currentCategory);
      currentGroup = null;
      pendingTool = null;
      continue;
    }

    const groupMatch = line.match(/^###\s+(.+)$/);
    if (groupMatch && currentCategory) {
      const title = normalizeLabel(groupMatch[1]);
      currentGroup = {
        id: `${currentCategory.id}-group-${currentCategory.groups.length + 1}`,
        title,
        description: `来自 Markdown 分组“${title}”。`,
        tools: [],
      };
      currentCategory.groups.push(currentGroup);
      pendingTool = null;
      continue;
    }

    const linkMatch = line.match(/^-\s+\[(.+?)\]\((.+?)\)\s*$/);
    if (linkMatch && currentCategory) {
      const group = ensureFallbackGroup();
      pendingTool = {
        name: linkMatch[1].trim(),
        url: linkMatch[2].trim(),
        domain: inferDomain(linkMatch[2].trim()),
      };
      group.tools.push(pendingTool);
      continue;
    }

    const domainMatch = line.match(/^-\s*域名[:：]\s*`?([^`\s]+)`?\s*$/);
    if (domainMatch && pendingTool) {
      pendingTool.domain = domainMatch[1].trim();
    }
  }

  const idCounter = new Map();

  for (const category of categories) {
    for (const group of category.groups) {
      group.tools = group.tools.map((tool) => {
        const base = sanitizeAscii(tool.domain || inferDomain(tool.url) || tool.name) || 'tool';
        const key = `${category.id}:${base}`;
        const index = (idCounter.get(key) || 0) + 1;
        idCounter.set(key, index);
        return {
          id: `${category.id}-${base}-${index}`,
          name: tool.name,
          url: tool.url,
          description: `来源：${group.title}`,
          domain: tool.domain || inferDomain(tool.url),
          tags: [category.title.replace(/工具$/, ''), group.title],
        };
      });
    }
  }

  return categories;
}

function buildModule(categories) {
  return `export interface TradingToolLink {
  id: string;
  name: string;
  url: string;
  description: string;
  domain: string;
  tags: string[];
}

export interface TradingToolGroup {
  id: string;
  title: string;
  description: string;
  tools: TradingToolLink[];
}

export interface TradingToolCategory {
  id: string;
  title: string;
  description: string;
  groups: TradingToolGroup[];
}

export type TradingToolCategoryId =
  | 'macro'
  | 'equity'
  | 'crypto'
  | 'metal'
  | 'quant'
  | 'general';

export const tradingToolPageMeta = {
  title: '交易工具',
  eyebrow: 'Trading Toolkit',
  summary: '根据 docs/trading-tools-bookmarks-review.md 自动同步生成。',
} as const;

export const tradingToolCategories: TradingToolCategory[] = ${JSON.stringify(categories, null, 2)};

export const tradingToolCategoryMap = tradingToolCategories.reduce(
  (map, category) => {
    map[category.id as TradingToolCategoryId] = category;
    return map;
  },
  {} as Record<TradingToolCategoryId, TradingToolCategory>,
);
`;
}

const markdown = readMarkdown(sourcePath);
const categories = parseMarkdown(markdown);
fs.writeFileSync(targetPath, buildModule(categories), 'utf8');
console.log(`Synced trading tools from ${path.relative(repoRoot, sourcePath)} -> ${path.relative(repoRoot, targetPath)}`);
