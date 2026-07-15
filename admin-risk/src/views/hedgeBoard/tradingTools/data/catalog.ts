import {
  tradingToolCategoryMap,
  type TradingToolCategory,
  type TradingToolCategoryId,
  type TradingToolGroup,
} from './marketTools';

export interface TradingToolCatalogSection {
  id: TradingToolCategoryId | 'crypto';
  title: string;
  groups: TradingToolGroup[];
}

export const tradingToolBoardCatalogMap: Record<'macro' | 'gold' | 'crypto', TradingToolCatalogSection> = {
  macro: {
    id: 'macro',
    title: '宏观工具',
    groups: tradingToolCategoryMap.macro.groups,
  },
  gold: {
    id: 'metal',
    title: '金属工具',
    groups: tradingToolCategoryMap.metal.groups,
  },
  crypto: {
    id: 'crypto',
    title: '加密工具',
    groups: tradingToolCategoryMap.crypto.groups,
  },
};

export function getTradingToolCategory(id: TradingToolCategoryId): TradingToolCategory {
  return tradingToolCategoryMap[id];
}
