export type StrategyId =
  | 'funding'
  | 'crossSpread'
  | 'domesticOverseas'
  | 'dip'
  | 'shortLineTraderL'
  | 'shortLineTraderW';

export type StrategyCategory = 'arbitrage' | 'directional' | 'intraday';
export type StrategyLegModel = 'single' | 'dual' | 'multi';
export type StrategyAccountModel = 'single' | 'dual' | 'multi';

export interface StrategyManifest {
  id: StrategyId;
  name: string;
  shortName: string;
  category: StrategyCategory;
  order: number;

  platform: {
    enabled: boolean;
    analysis: boolean;
    execution: boolean;
  };

  management: {
    enabled: boolean;
    pnl: boolean;
    capital: boolean;
    orders: boolean;
  };

  structure: {
    legModel: StrategyLegModel;
    accountModel: StrategyAccountModel;
  };
}

export const strategyRegistry: readonly StrategyManifest[] = [
  {
    id: 'funding',
    name: '资费套利',
    shortName: '资费',
    category: 'arbitrage',
    order: 10,
    platform: { enabled: true, analysis: true, execution: true },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'dual', accountModel: 'dual' },
  },
  {
    id: 'crossSpread',
    name: '跨所价差',
    shortName: '跨所价差',
    category: 'arbitrage',
    order: 20,
    platform: { enabled: true, analysis: true, execution: true },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'dual', accountModel: 'dual' },
  },
  {
    id: 'domesticOverseas',
    name: '海内外价差',
    shortName: '海内外价差',
    category: 'arbitrage',
    order: 30,
    platform: { enabled: true, analysis: true, execution: true },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'dual', accountModel: 'dual' },
  },
  {
    id: 'dip',
    name: '抄底',
    shortName: '抄底',
    category: 'directional',
    order: 40,
    platform: { enabled: false, analysis: false, execution: false },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'single', accountModel: 'single' },
  },
  {
    id: 'shortLineTraderL',
    name: '短线交易员 L',
    shortName: '短线 L',
    category: 'intraday',
    order: 50,
    platform: { enabled: false, analysis: false, execution: false },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'single', accountModel: 'single' },
  },
  {
    id: 'shortLineTraderW',
    name: '短线交易员 W',
    shortName: '短线 W',
    category: 'intraday',
    order: 60,
    platform: { enabled: false, analysis: false, execution: false },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'single', accountModel: 'single' },
  },
] as const;

export const platformStrategies = strategyRegistry
  .filter((strategy) => strategy.platform.enabled)
  .sort((left, right) => left.order - right.order);

export const managementStrategies = strategyRegistry
  .filter((strategy) => strategy.management.enabled)
  .sort((left, right) => left.order - right.order);

export const strategyRegistryMap = strategyRegistry.reduce(
  (map, strategy) => {
    map[strategy.id] = strategy;
    return map;
  },
  {} as Record<StrategyId, StrategyManifest>,
);

export function getStrategyManifest(id: StrategyId): StrategyManifest {
  return strategyRegistryMap[id];
}
