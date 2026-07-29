import type {
  TradingToolCategory,
  TradingToolCategoryId,
  TradingToolGroup,
} from './marketTools';

export type { TradingToolCategoryId } from './marketTools';

export interface TradingToolCatalogSection {
  id: TradingToolCategoryId | 'crypto';
  title: string;
  groups: TradingToolGroup[];
}

export type TradingToolBoardCatalogKey = 'macro' | 'gold' | 'crypto';

const boardCatalogCategoryMap: Record<TradingToolBoardCatalogKey, TradingToolCategoryId> = {
  macro: 'macro',
  gold: 'metal',
  crypto: 'crypto',
};

const boardCatalogTitleMap: Record<TradingToolBoardCatalogKey, string> = {
  macro: '宏观工具',
  gold: '金属工具',
  crypto: '加密工具',
};

async function loadTradingToolCategoryMap() {
  const module = await import('./marketTools');
  return module.tradingToolCategoryMap;
}

export async function loadTradingToolBoardCatalog(
  id: TradingToolBoardCatalogKey,
): Promise<TradingToolCatalogSection> {
  const tradingToolCategoryMap = await loadTradingToolCategoryMap();
  const categoryId = boardCatalogCategoryMap[id];
  return {
    id: id === 'gold' ? 'metal' : id,
    title: boardCatalogTitleMap[id],
    groups: tradingToolCategoryMap[categoryId].groups,
  };
}

export async function loadTradingToolCategory(id: TradingToolCategoryId): Promise<TradingToolCategory> {
  const tradingToolCategoryMap = await loadTradingToolCategoryMap();
  return tradingToolCategoryMap[id];
}
