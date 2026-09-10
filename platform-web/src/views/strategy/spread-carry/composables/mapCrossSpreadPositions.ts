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
import type {
  CrossSpreadPositionOverviewResult,
  CrossSpreadPositionPnlResult,
  CrossSpreadSnapshotResult,
} from '@/api/platform/trading.types';
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
  originLabel?: string | null;
  mt5PositionId?: string;
  isAbnormal?: boolean;
  mt5Only?: boolean;
  remainingMt5Lots?: number;
  recoveryIdempotencyKey?: string | null;
}

export interface OverviewRow {
  id: string;
  exitPlanId: string | null;
  takeProfitExecutionMode: CrossSpreadExecutionMode | null;
  stopLossExecutionMode: CrossSpreadExecutionMode | null;
  takeProfitLimitStrategy: CrossSpreadLimitStrategy | null;
  stopLossLimitStrategy: CrossSpreadLimitStrategy | null;
  direction: string;
  qty: number;
  entrySpread: string;
  currentSpread: string;
  detail: string;
  accountStatus: string;
  accountRisk: string;
  pnl: string;
  pnlUsdt: NumericValue | null;
  pnlReason: string | null;
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

export function mapCloseOrders(
  exitPlans: CrossSpreadExitPlanResult[],
  abnormalOrders: CrossSpreadPositionOverviewResult['abnormalOrders'] = [],
) {
  return exitPlans
    .filter((plan) => plan.status === 'active' || plan.status === 'manual_intervention')
    .map<CloseOrder>((plan) => ({
      id: plan.planId,
      originLabel: plan.originLabel,
      mt5PositionId: plan.mt5PositionId,
      direction: plan.direction,
      qtyOz:
        Number(
          abnormalOrders.find((row) => row.planId === plan.planId)?.closeQuantityOz ??
            plan.quantityOz,
        ) || 0,
      isAbnormal: !!plan.originLabel || plan.status === 'manual_intervention',
      mt5Only: abnormalOrders.some(
        (row) => row.planId === plan.planId && row.action === 'finish_mt5',
      ),
      remainingMt5Lots: Number(
        abnormalOrders.find((row) => row.planId === plan.planId)?.mt5PendingCloseQuantity ?? 0,
      ),
      recoveryIdempotencyKey: abnormalOrders.find((row) => row.planId === plan.planId)
        ?.recoveryIdempotencyKey,
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
    (plan) => plan.status === 'active' && !plan.originLabel,
  );
  if (activePlans.length === 0) return [];
  const bybitPositions = options.snapshot?.bybit.positions || [];
  const mt5Positions = options.snapshot?.mt5.positions || [];
  const rowCount = Math.max(bybitPositions.length, mt5Positions.length);

  if (!options.snapshot && activePlans.length === 0) return [];
  const rows: OverviewRow[] = [];

  if (activePlans.length > 0) {
    return activePlans.map((plan) => {
      // A shared net position cannot supply each group's cost, margin or PnL.
      const candidateBybitLive =
        activePlans.length === 1
          ? matchObservedPlanPosition(options.observability?.bybit, plan.direction, 'bybit')
          : null;
      const bybitLive =
        candidateBybitLive &&
        Math.abs(Number(candidateBybitLive.netQuantity)) === Number(plan.quantityOz)
          ? candidateBybitLive
          : null;
      const valuation = matchingGroupValuation(plan, options.snapshot?.positionOverview);
      const mt5Live =
        options.observability?.mt5.positions.find(
          (position) => position.externalPositionId === plan.mt5PositionId,
        ) ?? null;
      const direction = plan.direction === 'LONG_SPREAD' ? '多头' : '空头';
      return {
        id: plan.planId,
        exitPlanId: plan.planId,
        takeProfitExecutionMode: plan.takeProfitExecutionMode,
        stopLossExecutionMode: plan.stopLossExecutionMode,
        takeProfitLimitStrategy: plan.takeProfitLimitStrategy,
        stopLossLimitStrategy: plan.stopLossLimitStrategy,
        direction,
        qty: Number(plan.quantityOz) || 0,
        entrySpread: formatPlanEntrySpread(plan.entrySpread, bybitLive, mt5Live),
        currentSpread: formatNullableSigned(
          direction === '多头' ? options.shortSpread : options.longSpread,
        ),
        detail: `BY: ${formatNullablePrice(
          valuation?.bybitEntryPrice,
        )} | MT5: ${formatNullablePrice(valuation?.mt5EntryPrice)} · Ticket ${plan.mt5PositionId}`,
        accountStatus: `BY: ${venueReadState(options.observability?.bybit)} | MT5: ${venueReadState(
          options.observability?.mt5,
        )}`,
        accountRisk: `BY: ${accountRiskText(options.observability?.bybit)} | MT5: ${accountRiskText(
          options.observability?.mt5,
        )}`,
        pnl: formatNullableSigned(parseOptionalNumber(valuation?.totalPnlUsdt)),
        pnlUsdt: valuation?.totalPnlUsdt ?? null,
        pnlReason: valuation?.reason ?? null,
        legPnl: `BY: ${formatNullableSigned(
          parseOptionalNumber(valuation?.bybitPnlUsdt),
        )} | MT5: ${formatNullableSigned(parseOptionalNumber(valuation?.mt5PnlUsdt))}`,
        takeProfit: formatNullableSigned(parseOptionalNumber(plan.takeProfitSpread)),
        stopLoss: formatNullableSigned(parseOptionalNumber(plan.stopLossSpread)),
        liquidation: `BY: ${formatObservedLiquidation(
          options.observability?.bybit,
          bybitLive,
        )} | MT5: ${formatObservedLiquidation(options.observability?.mt5, mt5Live)}`,
        margin: `BY: ${formatObservedMargin(bybitLive)} | MT5: ${formatObservedMargin(mt5Live)}`,
        openTime: formatOpenTime(valuation?.openTime ?? plan.createdAt, null),
        holdingTime: formatHoldingTime(
          valuation?.openTime ?? plan.createdAt,
          options.snapshot?.asOf,
        ),
        status: plan.originLabel || (plan.status === 'manual_intervention' ? '待复核' : '正常'),
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
    const matchedPlan = matchActivePlan(activePlans, direction, qty, mt5?.externalId);
    rows.push({
      id: `${bybit?.externalId || bybit?.symbol || 'bybit'}-${
        mt5?.externalId || mt5?.symbol || 'mt5'
      }-${index}`,
      exitPlanId: matchedPlan?.planId ?? null,
      takeProfitExecutionMode: matchedPlan?.takeProfitExecutionMode ?? null,
      stopLossExecutionMode: matchedPlan?.stopLossExecutionMode ?? null,
      takeProfitLimitStrategy: matchedPlan?.takeProfitLimitStrategy ?? null,
      stopLossLimitStrategy: matchedPlan?.stopLossLimitStrategy ?? null,
      direction,
      qty,
      entrySpread: matchedPlan
        ? formatPlanEntrySpread(matchedPlan.entrySpread, bybitLive, mt5Live)
        : formatEntrySpread(
            parseOptionalNumber(bybit?.averagePrice),
            parseOptionalNumber(mt5?.averagePrice),
          ),
      currentSpread: formatNullableSigned(
        direction === '多头' ? options.shortSpread : options.longSpread,
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
      pnl:
        bybit?.unrealizedPnl != null && mt5?.unrealizedPnl != null
          ? formatNullableSigned(Number(bybit.unrealizedPnl) + Number(mt5.unrealizedPnl))
          : '--',
      pnlUsdt: null,
      pnlReason: '成交尚未归属到完整组合',
      legPnl: `BY: ${formatNullableSigned(
        parseOptionalNumber(bybit?.unrealizedPnl),
      )} | MT5: ${formatNullableSigned(parseOptionalNumber(mt5?.unrealizedPnl))}`,
      takeProfit: formatNullableSigned(parseOptionalNumber(matchedPlan?.takeProfitSpread)),
      stopLoss: formatNullableSigned(parseOptionalNumber(matchedPlan?.stopLossSpread)),
      liquidation: `BY: ${formatObservedLiquidation(
        options.observability?.bybit,
        bybitLive,
      )} | MT5: ${formatObservedLiquidation(options.observability?.mt5, mt5Live)}`,
      margin: `BY: ${formatObservedMargin(bybitLive)} | MT5: ${formatObservedMargin(mt5Live)}`,
      openTime: formatOpenTime(bybitLive?.openTime, mt5Live?.openTime),
      holdingTime: '--',
      status:
        options.snapshot?.status !== 'available'
          ? options.snapshotStatusText
          : !matchedPlan || matchedPlan.status === 'manual_intervention'
          ? '待复核'
          : '正常',
    });
  }
  return rows;
}

function matchingGroupValuation(
  plan: CrossSpreadExitPlanResult,
  overview: CrossSpreadPositionOverviewResult | null | undefined,
): CrossSpreadPositionPnlResult | null {
  const rows = overview?.groups.filter((group) => group.planId === plan.planId) ?? [];
  const row = rows.length === 1 ? rows[0] : null;
  return row &&
    Number(row.quantityOz) === Number(plan.quantityOz) &&
    Date.parse(row.planUpdatedAt) === Date.parse(plan.updatedAt)
    ? row
    : null;
}

export function mapOverviewPnlSummary(
  plans: CrossSpreadExitPlanResult[],
  overview: CrossSpreadPositionOverviewResult | null | undefined,
): CrossSpreadPositionOverviewResult | null {
  const active = plans.filter((plan) => plan.status === 'active' && !plan.originLabel);
  if (!overview || !active.every((plan) => matchingGroupValuation(plan, overview))) return null;
  const groups = overview.groups.filter((group) =>
    active.some((plan) => plan.planId === group.planId),
  );
  return { ...overview, groups };
}

function formatHoldingTime(openTime: string, asOf: string | undefined) {
  const minutes = Math.floor((Date.parse(asOf ?? '') - Date.parse(openTime)) / 60000);
  if (!Number.isFinite(minutes) || minutes < 0) return '--';
  if (minutes < 60) return `${minutes} 分钟`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} 小时 ${minutes % 60} 分钟`;
  return `${Math.floor(minutes / 1440)} 天 ${Math.floor((minutes % 1440) / 60)} 小时`;
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
    }) || null
  );
}

function matchActivePlan(
  plans: CrossSpreadExitPlanResult[],
  direction: string,
  qty: number,
  mt5PositionId?: string | null,
) {
  const normalizedDirection =
    direction === '多头' ? 'LONG_SPREAD' : direction === '空头' ? 'SHORT_SPREAD' : null;
  if (!normalizedDirection) return null;
  const directionPlans = plans.filter((plan) => plan.direction === normalizedDirection);
  if (mt5PositionId) {
    const ticketMatch = directionPlans.find((plan) => plan.mt5PositionId === mt5PositionId);
    if (ticketMatch) return ticketMatch;
  }
  const quantityMatches = directionPlans.filter(
    (plan) => Math.abs((Number(plan.quantityOz) || 0) - qty) < 1e-8,
  );
  if (quantityMatches.length === 1) return quantityMatches[0];
  return directionPlans.length === 1 ? directionPlans[0] : null;
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
