import type {
  CrossSpreadExecutionMode,
  CrossSpreadExitPlanResult,
  CrossSpreadLimitStrategy,
} from '@/api/platform/crossSpreadLifecycle';
import type {
  CrossSpreadObservabilityResult,
  CrossSpreadVenueObservability,
  NumericValue,
  VenuePositionSnapshot,
} from '@/api/platform/crossSpreadObservability';
import type { CrossSpreadSnapshotResult } from '@/api/platform/trading.types';
import {
  formatNullablePrice,
  formatNullableSigned,
  formatNumber,
  parseOptionalNumber,
} from './useCrossSpreadFormatting';

export interface QuantityRules {
  minOz: number;
  stepOz: number;
  mt5Multiplier: number;
}

export interface CloseOrder {
  id: string;
  direction: 'LONG_SPREAD' | 'SHORT_SPREAD';
  qtyOz: number;
  entrySpread: number;
  takeProfit: number | null;
  stopLoss: number | null;
  execution: string;
}

export interface OverviewRow {
  id: string;
  direction: string;
  qty: number;
  entrySpread: string;
  currentSpread: string;
  detail: string;
  accountStatus: string;
  accountRisk: string;
  pnl: string;
  legPnl: string;
  takeProfit: string;
  stopLoss: string;
  liquidation: string;
  margin: string;
  openTime: string;
  holdingTime: string;
  status: string;
}

interface MapOverviewRowsOptions {
  snapshot: CrossSpreadSnapshotResult | null;
  observability: CrossSpreadObservabilityResult | null;
  quantityRules: QuantityRules | null;
  longSpread: number | null;
  shortSpread: number | null;
  snapshotStatusText: string;
  exitPlans: CrossSpreadExitPlanResult[];
}

export function mapCloseOrders(exitPlans: CrossSpreadExitPlanResult[]) {
  return exitPlans
    .filter((plan) => plan.status === 'active' || plan.status === 'manual_intervention')
    .map<CloseOrder>((plan) => ({
      id: plan.planId,
      direction: plan.direction,
      qtyOz: Number(plan.quantityOz) || 0,
      entrySpread: Number(plan.entrySpread) || 0,
      takeProfit: parseOptionalNumber(plan.takeProfitSpread),
      stopLoss: parseOptionalNumber(plan.stopLossSpread),
      execution: `${
        plan.status === 'manual_intervention' ? '受控恢复 / ' : ''
      }${executionSelectionLabel(
        plan.takeProfitExecutionMode,
        plan.takeProfitLimitStrategy,
      )} / ${executionSelectionLabel(plan.stopLossExecutionMode, plan.stopLossLimitStrategy)}`,
    }));
}

export function mapOverviewRows(options: MapOverviewRowsOptions) {
  const activePlans = options.exitPlans.filter(
    (plan) => plan.status === 'active' || plan.status === 'manual_intervention',
  );
  const bybitPositions = options.snapshot?.bybit.positions || [];
  const mt5Positions = options.snapshot?.mt5.positions || [];
  const rowCount = Math.max(bybitPositions.length, mt5Positions.length);

  if (!options.snapshot && activePlans.length === 0) return [];
  const rows: OverviewRow[] = [];

  if (rowCount === 0 && activePlans.length > 0) {
    return activePlans.map((plan, index) => {
      const bybitLive = matchObservedPlanPosition(
        options.observability?.bybit,
        plan.direction,
        'bybit',
      );
      const mt5Live = matchObservedPlanPosition(options.observability?.mt5, plan.direction, 'mt5');
      const direction = plan.direction === 'LONG_SPREAD' ? '多头' : '空头';
      return {
        id: plan.planId,
        direction,
        qty: Number(plan.quantityOz) || 0,
        entrySpread: formatPlanEntrySpread(plan.entrySpread, bybitLive, mt5Live),
        currentSpread: formatNullableSigned(
          direction === '多头' ? options.longSpread : options.shortSpread,
        ),
        detail: `BY: ${formatObservedAveragePrice(bybitLive)} | MT5: ${formatObservedAveragePrice(
          mt5Live,
        )}`,
        accountStatus: `BY: ${venueReadState(options.observability?.bybit)} | MT5: ${venueReadState(
          options.observability?.mt5,
        )}`,
        accountRisk: `BY: ${accountRiskText(options.observability?.bybit)} | MT5: ${accountRiskText(
          options.observability?.mt5,
        )}`,
        pnl: formatNullableSigned(
          (parseOptionalNumber(bybitLive?.unrealizedPnl) || 0) +
            (parseOptionalNumber(mt5Live?.unrealizedPnl) || 0),
        ),
        legPnl: `BY: ${formatNullableSigned(
          parseOptionalNumber(bybitLive?.unrealizedPnl),
        )} | MT5: ${formatNullableSigned(parseOptionalNumber(mt5Live?.unrealizedPnl))}`,
        takeProfit: formatNullableSigned(parseOptionalNumber(plan.takeProfitSpread)),
        stopLoss: formatNullableSigned(parseOptionalNumber(plan.stopLossSpread)),
        liquidation: `BY: ${formatObservedLiquidation(
          options.observability?.bybit,
          bybitLive,
        )} | MT5: ${formatObservedLiquidation(options.observability?.mt5, mt5Live)}`,
        margin: `BY: ${formatObservedMargin(bybitLive)} | MT5: ${formatObservedMargin(mt5Live)}`,
        openTime: formatOpenTime(bybitLive?.openTime, mt5Live?.openTime, plan.createdAt),
        holdingTime: '--',
        status: plan.status === 'manual_intervention' ? '待复核' : '正常',
      };
    });
  }

  for (let index = 0; index < rowCount; index += 1) {
    const bybit = bybitPositions[index];
    const mt5 = mt5Positions[index];
    const bybitLive = matchObservedPosition(options.observability?.bybit, bybit?.symbol, index);
    const mt5Live = matchObservedPosition(options.observability?.mt5, mt5?.symbol, index);
    const bybitQtyValue = Math.abs(parseOptionalNumber(bybit?.quantity) || 0);
    const mt5QtyValue =
      Math.abs(parseOptionalNumber(mt5?.quantity) || 0) *
      (options.quantityRules?.mt5Multiplier || 0);
    const qty = bybitQtyValue || mt5QtyValue;
    const bybitQty = parseOptionalNumber(bybit?.quantity);
    const mt5Side = typeof mt5?.side === 'string' ? mt5.side.toLowerCase() : null;
    let direction: string;
    if (bybitQty !== null && bybitQty !== 0) {
      direction = bybitQty >= 0 ? '多头' : '空头';
    } else if (mt5Side === 'buy') {
      direction = '空头';
    } else if (mt5Side === 'sell') {
      direction = '多头';
    } else {
      direction = '--';
    }
    const matchedPlan = matchActivePlan(activePlans, direction, qty);
    rows.push({
      id: `${bybit?.externalId || bybit?.symbol || 'bybit'}-${
        mt5?.externalId || mt5?.symbol || 'mt5'
      }-${index}`,
      direction,
      qty,
      entrySpread: matchedPlan
        ? formatPlanEntrySpread(matchedPlan.entrySpread, bybitLive, mt5Live)
        : formatEntrySpread(
            parseOptionalNumber(bybit?.averagePrice),
            parseOptionalNumber(mt5?.averagePrice),
          ),
      currentSpread: formatNullableSigned(
        direction === '多头' ? options.longSpread : options.shortSpread,
      ),
      detail: `BY: ${
        formatObservedAveragePrice(bybitLive) || formatNullablePrice(bybit?.averagePrice)
      } | MT5: ${formatObservedAveragePrice(mt5Live) || formatNullablePrice(mt5?.averagePrice)}`,
      accountStatus: `BY: ${venueReadState(options.observability?.bybit)} | MT5: ${venueReadState(
        options.observability?.mt5,
      )}`,
      accountRisk: `BY: ${accountRiskText(options.observability?.bybit)} | MT5: ${accountRiskText(
        options.observability?.mt5,
      )}`,
      pnl: formatNullableSigned(
        (parseOptionalNumber(bybit?.unrealizedPnl) || 0) +
          (parseOptionalNumber(mt5?.unrealizedPnl) || 0),
      ),
      legPnl: `BY: ${formatNullableSigned(
        parseOptionalNumber(bybit?.unrealizedPnl),
      )} | MT5: ${formatNullableSigned(parseOptionalNumber(mt5?.unrealizedPnl))}`,
      takeProfit: formatExitSpread(options.exitPlans, 'takeProfit'),
      stopLoss: formatExitSpread(options.exitPlans, 'stopLoss'),
      liquidation: `BY: ${formatObservedLiquidation(
        options.observability?.bybit,
        bybitLive,
      )} | MT5: ${formatObservedLiquidation(options.observability?.mt5, mt5Live)}`,
      margin: `BY: ${formatObservedMargin(bybitLive)} | MT5: ${formatObservedMargin(mt5Live)}`,
      openTime: formatOpenTime(bybitLive?.openTime, mt5Live?.openTime),
      holdingTime: '--',
      status: options.snapshot?.status === 'available' ? '正常' : options.snapshotStatusText,
    });
  }
  return rows;
}

function matchObservedPosition(
  venue: CrossSpreadVenueObservability | null | undefined,
  symbol: string | undefined,
  index: number,
) {
  if (!venue) return null;
  return (
    venue.positions.find((position) => position.symbol === symbol) || venue.positions[index] || null
  );
}

function matchObservedPlanPosition(
  venue: CrossSpreadVenueObservability | null | undefined,
  direction: 'LONG_SPREAD' | 'SHORT_SPREAD',
  leg: 'bybit' | 'mt5',
) {
  if (!venue) return null;
  const expectedPositive =
    (direction === 'LONG_SPREAD' && leg === 'bybit') ||
    (direction === 'SHORT_SPREAD' && leg === 'mt5');
  return (
    venue.positions.find((position) => {
      const quantity = parseOptionalNumber(position.netQuantity);
      if (quantity === null || quantity === 0) return false;
      return expectedPositive ? quantity > 0 : quantity < 0;
    }) ||
    venue.positions.find((position) => position.symbol === venue.symbol) ||
    venue.positions[0] ||
    null
  );
}

function matchActivePlan(plans: CrossSpreadExitPlanResult[], direction: string, qty: number) {
  const normalizedDirection =
    direction === '多头' ? 'LONG_SPREAD' : direction === '空头' ? 'SHORT_SPREAD' : null;
  if (!normalizedDirection) return null;
  return (
    plans.find(
      (plan) =>
        plan.direction === normalizedDirection &&
        Math.abs((Number(plan.quantityOz) || 0) - qty) < 1e-8,
    ) ||
    plans.find((plan) => plan.direction === normalizedDirection) ||
    null
  );
}

function isSyntheticObservedPrice(position: VenuePositionSnapshot | null) {
  return Boolean(position && position.source === 'fake');
}

function venueReadState(venue: CrossSpreadVenueObservability | null | undefined) {
  if (!venue) return '不可用';
  if (venue.status === 'complete') return `${venue.accountId} / 完整`;
  if (venue.status === 'partial') return `${venue.accountId} / 部分`;
  return `${venue.accountId} / 不可用`;
}

function accountRiskText(venue: CrossSpreadVenueObservability | null | undefined) {
  const risk = venue?.accountRisk;
  if (!risk) return '--';
  return `${money(risk.equity, risk.currency)} / ${money(risk.availableBalance, risk.currency)}`;
}

function formatObservedLiquidation(
  venue: CrossSpreadVenueObservability | null | undefined,
  position: VenuePositionSnapshot | null,
) {
  if (position?.liquidationPrice != null) return formatNumeric(position.liquidationPrice);
  if (venue?.venue === 'MT5') {
    return `Stop Out ${thresholdValue(
      venue.accountRisk?.stopOutLevel,
      venue.accountRisk?.marginThresholdMode,
    )}`;
  }
  return '--';
}

function formatObservedMargin(position: VenuePositionSnapshot | null) {
  if (!position) return '--';
  const initial = formatNumeric(position.initialMargin);
  const maintenance = formatNumeric(position.maintenanceMargin);
  return initial === '--' && maintenance === '--' ? '--' : `${initial} / ${maintenance}`;
}

function formatEntrySpread(bybitAvg: number | null, mt5Avg: number | null): string {
  if (bybitAvg === null || mt5Avg === null) return '--';
  return formatNullableSigned(bybitAvg - mt5Avg);
}

function formatPlanEntrySpread(
  entrySpread: NumericValue | null | undefined,
  bybitPosition: VenuePositionSnapshot | null,
  mt5Position: VenuePositionSnapshot | null,
) {
  const parsed = parseOptionalNumber(entrySpread);
  if (
    parsed !== null &&
    !(
      parsed === 0 &&
      isSyntheticObservedPrice(bybitPosition) &&
      isSyntheticObservedPrice(mt5Position)
    )
  ) {
    return formatNullableSigned(parsed);
  }
  return '--';
}

function formatObservedAveragePrice(position: VenuePositionSnapshot | null) {
  if (!position || isSyntheticObservedPrice(position)) return '';
  return formatNullablePrice(position.averagePrice);
}

function formatExitSpread(
  exitPlans: CrossSpreadExitPlanResult[],
  kind: 'takeProfit' | 'stopLoss',
): string {
  const active = exitPlans.find((plan) => plan.status === 'active');
  if (!active) return '--';
  const value = kind === 'takeProfit' ? active.takeProfitSpread : active.stopLossSpread;
  return formatNullableSigned(parseOptionalNumber(value));
}

function formatOpenTime(
  bybitOpenTime: string | null | undefined,
  mt5OpenTime: string | null | undefined,
  fallbackOpenTime?: string | null | undefined,
): string {
  const candidate = bybitOpenTime || mt5OpenTime || fallbackOpenTime;
  if (!candidate) return '--';
  const parsed = new Date(candidate);
  if (Number.isNaN(parsed.getTime())) return '--';
  return parsed.toLocaleString('zh-CN', { hour12: false });
}

function formatNumeric(value: NumericValue | null | undefined, digits = 2) {
  const parsed = parseOptionalNumber(value);
  return parsed === null ? '--' : formatNumber(parsed, digits);
}

function money(value: NumericValue | null | undefined, currency: string) {
  const rendered = formatNumeric(value);
  return rendered === '--' ? rendered : `${rendered} ${currency}`;
}

function thresholdValue(value: NumericValue | null | undefined, mode?: string | null) {
  const parsed = parseOptionalNumber(value);
  if (parsed === null) return '--';
  return mode === '1' ? parsed.toFixed(2) : `${parsed.toFixed(2)}%`;
}

function limitStrategyLabel(strategy: CrossSpreadLimitStrategy) {
  return strategy === 'post_only_chase' ? 'PostOnly Chase' : 'FOK';
}

function executionSelectionLabel(
  mode: CrossSpreadExecutionMode,
  strategy: CrossSpreadLimitStrategy,
) {
  return mode === 'market' ? '市价' : limitStrategyLabel(strategy);
}
