import { managementStrategies, type StrategyId } from '@/views/strategy/shared/strategyRegistry';

export type StrategyDeskKey = StrategyId;

export type {
  StrategyAccountBreakdown,
  StrategyCapitalComparisonCard,
  StrategyCapitalCurveConfig,
  StrategyCapitalCurveOption,
  StrategyCapitalCurveSummary,
  StrategyCapitalProfile,
  StrategyCapitalRiskCard,
  StrategyCapitalRiskOverview,
  StrategyCapitalRuleAlert,
  StrategyCapitalRuleMetric,
  StrategyCapitalRulePanel,
  StrategyCurveCard,
  StrategyCurvePoint,
  StrategyKpiCard,
  StrategyTableColumn,
  StrategyTableRow,
  StrategyTableSection,
  StrategyTableTab,
} from './types';

export type StrategyKpiItem = import('./types').StrategyKpiCard;
export type StrategyCardItem = import('./types').StrategyKpiCard;

export {
  strategyPnlProfiles,
  type StrategyPnlAttributionItem,
  type StrategyPnlProfile,
} from './pnl';
export { strategyCapitalProfiles } from './capital';
export { strategyOrderProfiles, type StrategyOrderProfile } from './orders';

export const strategyDeskOrder = managementStrategies.map(
  (strategy) => strategy.id,
) as StrategyDeskKey[];

export const strategyDeskLabels = Object.fromEntries(
  managementStrategies.map((strategy) => [strategy.id, strategy.name]),
) as Record<StrategyDeskKey, string>;
